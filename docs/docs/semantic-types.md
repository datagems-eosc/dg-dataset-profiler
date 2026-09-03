# Semantic Types

Alongside the structural type of each column (`sc:Text`, `sc:Integer`, …), the profiler infers a **semantic type** — a short phrase describing what the values actually *mean*. A column typed `sc:Text` might be a `country name`, an `email address` or a `product category`; the structural type cannot tell them apart, and dataset discovery needs the difference.

This is done by the **Column Type Annotator** (CTA), an LLM-backed component that runs over every tabular column: CSV files, Excel sheets, and relational-database tables alike.

## How It Works

For each column, the annotator sends the LLM:

1. The **target column header**
2. The **other headers** in the table, as context — `id` means something different next to `patient name` than next to `invoice date`
3. A **sample of up to 10 non-null values** from the column
4. The **annotations already produced** for earlier columns in the same table, so that related columns are labelled consistently

The model answers in one to three words. Structural types are explicitly ruled out by the prompt, so `string` or `float` is never a valid answer.

Values are sampled rather than read in full: CSV columns are annotated from the first 100 rows, and database tables from a `LIMIT 100` sample. Annotation therefore costs the same on a 10 MB table as on a 10 GB one.

### Reserved values

| Value | Meaning |
|-------|---------|
| `unknown` | The model could not infer a type from the header and sample |
| `identifier` | The column holds mostly unique identifiers |
| `error` | The LLM call or response parsing failed for this column |
| `""` (empty) | Annotation did not run for this record set at all |

Annotation is **best-effort**. If the LLM is unreachable or misconfigured, the failure is logged and swallowed — the column gets `error` or `""` and profiling continues. A semantic type is an enrichment; losing it must never fail a profile.

## Profile Output

Semantic types appear on every `cr:Field` of a tabular record set, in both the light and heavy MoMa profiles:

```json
{
  "@type": "cr:Field",
  "@id": "a2c99e5f-d314-4b6e-a93a-aa91d2afd9b8",
  "name": "dv_agency",
  "description": "",
  "dataType": "sc:Integer",
  "semanticType": "transit agency identifier",
  "source": {
    "fileObject": { "@id": "7f5e489d-f2e4-475f-a942-71d6b0aed1ee" },
    "extract": { "column": "dv_agency" }
  },
  "sample": [3, 2, 3],
  "statistics": { "...": "..." }
}
```

!!! note "Key naming differs between profiles"
    The MoMa profile uses **`semanticType`** (camelCase), consistent with `dataType`, `encodingFormat`
    and every other key in that profile. The **CDD profile uses `semantic_type`** (snake_case) — that is
    a separate contract with its own conventions and is not affected.

In the JSON-LD `@context` the term resolves to `dg:semanticType`, defined in `datagems-croissant-extension.ttl` with domain `cr:Field`.

### Relationship to `cr:dataType`

`dg:semanticType` overlaps with a mechanism Croissant already has, and this is worth being explicit
about. The Croissant specification allows a field to carry **several** `dataType` values, provided at
least one is atomic — the rest supply semantic meaning. Its own example pairs a structural type with
a Wikidata entity:

```json
"dataType": ["https://schema.org/URL", "https://www.wikidata.org/wiki/Q515"]
```

That is where a semantic type belongs. The profiler does not use it because `cr:dataType` is declared
`"@type": "@vocab"` and therefore needs an IRI, while the annotator produces unconstrained English
phrases — `geographic coordinate`, `alternative label` — which have no IRI to point at. (The `wd:`
prefix already sitting unused in the profile `@context` suggests this was anticipated.)

So `dg:semanticType` is a stopgap for free-text values, not a competing design. If annotation moves to
a controlled vocabulary with IRIs, those values belong in `cr:dataType` and this property should be
deprecated rather than kept alongside it.

## Configuration

CTA uses the shared `CommonLLMConnector` against the SCAYLE LLM service, on the `Qwen3` model group, configured through `dataset_profiler/common_llm/configs/llm_config.yaml` and the usual SCAYLE environment variables:

```bash
SCAYLE_BASE_URL=https://<scayle-host>/api
SCAYLE_USERNAME=<username>
SCAYLE_PASSWORD=<password>
SCAYLE_VERIFY_SSL=false   # self-signed certificate
```

Unlike data quality detection, annotation is **not** behind a feature flag — it runs whenever a tabular record set is profiled.

!!! warning "Model identifiers are case-sensitive and drift"
    SCAYLE model group names change over time and are matched exactly. A retired or misspelled name
    fails with `HTTP 400 … No fallback model group found for original model_group=<name>`, and **every
    column in the profile comes back as `error`** — profiling still succeeds, so the failure is easy to
    miss. List the available model groups on the endpoint before deploying a model change, and check a
    sample profile for a run of `"semanticType": "error"` afterwards.

## Limitations & Notes

- Annotation is **per column, in sequence** — a wide table costs one LLM call per column. This dominates profiling time for tables with many columns.
- The sample is drawn from the first 100 rows, so a column whose meaning is only apparent later in the file may be mislabelled.
- Output is free text, not a controlled vocabulary. `country`, `country name` and `nation` are all plausible answers for the same column. The annotator accepts an optional set of candidate labels to classify into, which is the route to a controlled vocabulary, but the profiling pipeline does not currently pass one.
- Semantic types are **not** validated against the column's structural type or its statistics.
