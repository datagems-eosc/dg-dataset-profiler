# JSON Profiling

JSON (`.json`, `.geojson`) and JSON Lines (`.jsonl`, `.ndjson`) files are profiled as **record sets whose columns are JSONPaths**. Each leaf value in a record becomes a field such as `location.lat` or `readings[*].temp_c`, and every field gets the same statistics as a CSV column. Long text values are also reported whole, for CDD to chunk so that semantic search reaches inside them.

## Finding the records

The profiler first works out where the records are and reports it as the **record path**:

| `jsonShape` | Example | Record path |
|---|---|---|
| `array_of_records` | `[{"id": 1}, {"id": 2}]` | `$[*]` |
| `json_lines` | one object per line | `$` (per line) |
| `wrapped_records` | `{"meta": {…}, "stations": [{…}, {…}]}` | `$.stations[*]` |
| `single_document` | an object with no array of objects in it | `$` |

For `wrapped_records`, the outermost array of objects wins, even when a nested array holds more objects: the stations are the records, not their readings. Scalars outside every array (`$.meta.source`, `$.meta.license`) are kept as `document_metadata`.

A `.json` file that actually holds one document per line is read as JSON Lines. Known dialects are recorded as `dialect`: `geojson`, `json-ld`, `json-schema` and `openapi`.

## Statistics

Statistics mean the same as for CSV columns, so search can compare fields across formats:

- A record where the key is **absent** counts as missing, exactly like one where it is `null`.
- `rowCount` is the number of non-null values.
- `missingPercentage` is the share missing out of all records.
- For a field under an array (`repeated: true`), the counts are over array elements rather than records.

Two statistics exist only for JSON fields:

- **`jsonTypes`** counts the non-null values of each JSON type, for example `{"integer": 400, "string": 12}`. The counts add up to `rowCount`. When a field mixes types, the statistics come from the majority type, and the other values are left out of the mean and the histogram.
- **`topValues`** lists the most frequent values of a text or boolean field with at most 50 distinct values. It is omitted when every value is unique (ids, names) and for long text.

Data types follow the values: `sc:Integer`, `sc:Float`, `sc:Boolean`, `sc:Date` or `sc:Text`. JSON strings stay `sc:Text` even when they look like numbers.

## Guardrails

| Situation | Rule |
|---|---|
| Objects used as maps, e.g. `{"2026-09-01": 21.3, "2026-09-02": 22.0}` | Collapsed to one repeated field, `daily_max.*`. A nested object counts as a map when at least 10 of its keys look like data (dates, numbers, ids), or when it has over 50 keys that each appear in under 10% of the objects. |
| Very wide or deep records | At most 300 fields (`paths_truncated: true` beyond that). Containers nested deeper than 8 levels become one text field. |
| Large files | Files are streamed (`ijson`, or line by line), never loaded whole. Memory stays flat; a 54 MB file takes about 12 s. |
| Invalid JSON | The file keeps a record set with no fields and `parse_errors: 1`. A file that breaks off part-way is profiled up to the break. Broken JSON Lines lines are skipped and counted. |
| Encoding | UTF-8 with or without a BOM, plus other encodings detected the same way as for CSV. |

## LLM enrichments

Each JSON file gets two enrichments:

- **Semantic types** for its fields, from the first 100 records, exactly as for CSV columns (see [Semantic Types](semantic-types.md)).
- **Keywords and a summary**, from one call with the same model and settings as [Document Keywords & Summaries](document-descriptions.md) (`ENABLE_DOCUMENT_LLM`, `DOCUMENT_LLM_MODEL`). The model is given the record count, the values outside the records, the fields with a few sample values, and three sample records, and is asked what the data is about rather than how the file is laid out.

Both are best-effort: a failure is logged and the profile continues. In a folder of many JSON files, only the first `JSON_LLM_MAX_FILES_PER_FOLDER` files (default 20) get them. The other files are profiled in full, apart from these two enrichments.

## Profile output

The fragments below show the shape of the output. Full profiles of a real example (`tests/assets/json_stations`) are on the [MoMa profile](profile-examples-moma.md#example-json-file) and [CDD profile](profile-examples-cdd.md#example-json-file) pages.

### CDD profile

One entry in `files[]` per JSON file. `columns` has the same layout as for CSV, plus `json_path`, `repeated` and, for repeated fields, `array_length`:

```json
{
  "file_object_id": "2f0c7a1e-5d1b-4f62-9a57-6e1d3c0b8a41",
  "original_format": "json",
  "name": "stations",
  "json_profile": {
    "shape": "wrapped_records",
    "dialect": null,
    "record_path": "$.stations[*]",
    "record_count": 412,
    "max_depth": 3,
    "path_count": 11,
    "paths_truncated": false,
    "schema_consistency_percentage": 93.0,
    "parse_errors": 0,
    "summary": "…",
    "document_metadata": {"$.meta.source": "National Observatory of Athens"},
    "sample_records": "[…]"
  },
  "columns": [
    {
      "name": "operator",
      "json_path": "$.stations[*].operator",
      "primitive_type": "sc:Text",
      "repeated": false,
      "statistics": {
        "rowCount": 239, "missingCount": 173, "missingPercentage": 41.99,
        "jsonTypes": {"string": 239},
        "topValues": [{"value": "NOA", "count": 182}, {"value": "HNMS", "count": 54}]
      }
    }
  ],
  "text_content": [
    {"section": "notes", "subsection": "NOA-0142", "text": "Rooftop station in the historic centre, …"}
  ]
}
```

### MoMa profile

A `cr:RecordSet` whose fields use Croissant's `source.extract.jsonPath` and `repeated`. `jsonTypes` and `topValues` sit on the field statistics as JSON strings, like `histogram`. All terms are declared in the DataGEMS vocabulary under `https://datagems.eu/ns/`.

```json
{
  "@type": "cr:RecordSet",
  "name": "stations",
  "recordPath": "$.stations[*]",
  "jsonShape": "wrapped_records",
  "recordCount": 412,
  "maxDepth": 3,
  "schemaConsistencyPercentage": 93.0,
  "field": [
    {
      "@type": "cr:Field",
      "name": "location.lat",
      "dataType": "sc:Float",
      "source": {
        "fileObject": {"@id": "2f0c7a1e-5d1b-4f62-9a57-6e1d3c0b8a41"},
        "extract": {"jsonPath": "$.stations[*].location.lat"}
      },
      "repeated": false,
      "statistics": {"@type": "dg:ColumnStatistics", "rowCount": 412, "jsonTypes": "{\"number\": 412}", "topValues": null}
    }
  ]
}
```

Set `ENABLE_JSON_RECORD_SETS=false` to leave JSON record sets out of the MoMa profile; the CDD profile keeps them either way.
