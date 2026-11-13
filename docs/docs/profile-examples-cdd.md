# CDD Profile

## `original_format` values

Every entry in `files` carries an `original_format`, taken from the file's extension (case-insensitive). A file gets the same value whether or not the profiler could read it, so a PDF is always `application/pdf`, even at the dataset root or when it fails to parse.

| Extension | `original_format` |
|---|---|
| `.csv` | `csv` |
| `.xlsx`, `.xls` | `xlsx` |
| `.pdf` | `application/pdf` |
| `.txt` | `text` |
| `.json`, `.geojson` | `json` (`jsonl` when the file holds JSON Lines) |
| `.jsonl`, `.ndjson` | `jsonl` |
| database connection | `sql-db` |
| anything else | the lowercased extension without the dot, e.g. `docx`, `m4a` |

## Document content

The profiler does not chunk documents: it hands CDD the text whole, and CDD chunks it.

| File type | Where the text is |
|---|---|
| `.pdf` | `raw_content`: the full text as one string, pages separated by a blank line |
| `.txt` | not in the profile: CDD reads the file at `content.file_path` |
| `.json`, `.jsonl` | `text_content`: one `{section, subsection, text}` entry per long text value (see the [JSON example](#example-json-file)) |

`raw_content` comes from the PDF's text layer. No OCR is run, so a scanned PDF has an empty `raw_content`. A PDF the profiler cannot open at all gets a bare entry with no `content` and no `raw_content`.

## Example: mixed file types

Below you can find a CDD profile example covering different file types:

```json
{
  "@id": "7c4d20a0-33e8-471e-8a3f-a7a54aa09f68",
  "content_url": "7c4d20a0-33e8-471e-8a3f-a7a54aa09f68",
  "name": "Dummy data.",
  "headline": "Dummy data.",
  "description": "Dummy data.",
  "keywords": [
    "weather",
    "weather prediction"
  ],
  "field_of_science": [
    "EARTH AND RELATED ENVIRONMENTAL SCIENCES"
  ],
  "files": [
    {
      "file_object_id": "ebd4e170-ff69-4517-8e03-eb733c5d7b82",
      "original_format": "csv",
      "source_file": "tests/assets/dummy_data/data/csv_1.csv",
      "name": "csv_1",
      "description": "",
      "keywords": [],
      "columns": [
        {
          "name": "dv_agency",
          "primitive_type": "sc:Integer",
          "semantic_types": [],
          "description": "",
          "statistics": {
            "rowCount": 20357,
            "mean": 2.1724713857641107,
            "median": 2.0,
            "standardDeviation": 0.41898436210185863,
            "min": 1.0,
            "max": 4.0,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": "[{\"binRange\": [0.997, 1.3], \"count\": 193}, {\"binRange\": [1.3, 1.6], \"count\": 0}, {\"binRange\": [1.6, 1.9], \"count\": 0}, {\"binRange\": [1.9, 2.2], \"count\": 16601}, {\"binRange\": [2.2, 2.5], \"count\": 0}, {\"binRange\": [2.5, 2.8], \"count\": 0}, {\"binRange\": [2.8, 3.1], \"count\": 3422}, {\"binRange\": [3.1, 3.4], \"count\": 0}, {\"binRange\": [3.4, 3.7], \"count\": 0}, {\"binRange\": [3.7, 4.0], \"count\": 141}]",
            "uniqueCount": 4,
            "variance": 0.1755478956859014,
            "range": 3.0,
            "percentile05": 1.9149060297572436,
            "percentile95": 3.0231282875511396,
            "generatedAt": "2026-06-12T00:00:00+00:00"
          }
        },
        {
          "name": "dv_platenum_station",
          "primitive_type": "sc:Text",
          "semantic_types": [],
          "description": "",
          "statistics": {
            "rowCount": 20357,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": null,
            "uniqueCount": 83,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null
          }
        },
        {
          "name": "dv_validations",
          "primitive_type": "sc:Integer",
          "semantic_types": [],
          "description": "",
          "statistics": {
            "rowCount": 20357,
            "mean": 351.1354325293511,
            "median": 192.0,
            "standardDeviation": 700.3838578383433,
            "min": 1.0,
            "max": 17606.0,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": "[{\"binRange\": [-16.605, 1761.5], \"count\": 19931}, {\"binRange\": [1761.5, 3522.0], \"count\": 336}, {\"binRange\": [3522.0, 5282.5], \"count\": 39}, {\"binRange\": [5282.5, 7043.0], \"count\": 7}, {\"binRange\": [7043.0, 8803.5], \"count\": 10}, {\"binRange\": [8803.5, 10564.0], \"count\": 10}, {\"binRange\": [10564.0, 12324.5], \"count\": 13}, {\"binRange\": [12324.5, 14085.0], \"count\": 4}, {\"binRange\": [14085.0, 15845.5], \"count\": 1}, {\"binRange\": [15845.5, 17606.0], \"count\": 6}]",
            "uniqueCount": 1673,
            "variance": 490537.5483205206,
            "range": 17605.0,
            "percentile05": 74.20048764487481,
            "percentile95": 1708.6992652526214,
            "generatedAt": "2026-06-12T00:00:00+00:00"
          }
        },
        {
          "name": "dv_route",
          "primitive_type": "sc:Float",
          "semantic_types": [],
          "description": "",
          "statistics": {
            "rowCount": 0,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 20357,
            "missingPercentage": 100.0,
            "histogram": "[]",
            "uniqueCount": 0,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null
          }
        },
        {
          "name": "routes_per_hour",
          "primitive_type": "sc:Float",
          "semantic_types": [],
          "description": "",
          "statistics": {
            "rowCount": 0,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 20357,
            "missingPercentage": 100.0,
            "histogram": "[]",
            "uniqueCount": 0,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null
          }
        },
        {
          "name": "load_dt",
          "primitive_type": "sc:Text",
          "semantic_types": [],
          "description": "",
          "statistics": {
            "rowCount": 20357,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": null,
            "uniqueCount": 20,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null
          }
        },
        {
          "name": "date_hour",
          "primitive_type": "sc:Text",
          "semantic_types": [],
          "description": "",
          "statistics": {
            "rowCount": 20357,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": null,
            "uniqueCount": 96,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null
          }
        },
        {
          "name": "etl_extraction_dt",
          "primitive_type": "sc:Date",
          "semantic_types": [],
          "description": "",
          "statistics": {
            "rowCount": 20357,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": null,
            "uniqueCount": 5,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null
          }
        },
        {
          "name": "etl_load_dt",
          "primitive_type": "sc:Date",
          "semantic_types": [],
          "description": "",
          "statistics": {
            "rowCount": 20357,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": null,
            "uniqueCount": 5,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null
          }
        },
        {
          "name": "dv_agency_desc",
          "primitive_type": "sc:Text",
          "semantic_types": [],
          "description": "",
          "statistics": {
            "rowCount": 20357,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": null,
            "uniqueCount": 6,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null
          }
        },
        {
          "name": "boarding_disembark_desc",
          "primitive_type": "sc:Text",
          "semantic_types": [],
          "description": "",
          "statistics": {
            "rowCount": 20357,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": null,
            "uniqueCount": 2,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null
          }
        }
      ]
    },
    {
      "file_object_id": "4c3bc073-e519-4eb3-bcf4-637a36d03bc9",
      "original_format": "xlsx",
      "source_file": "tests/assets/dummy_data/data/ISCO-08 EN Structure and definitions.xlsx",
      "name": "ISCO-08 EN Structure and definitions.xlsx",
      "description": "",
      "keywords": [],
      "tables": [
        {
          "name": "Sheet3",
          "description": "",
          "columns": [
            {
              "name": "Level",
              "primitive_type": "sc:Integer",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 9,
                "mean": 3.2222222222222223,
                "median": 4.0,
                "standardDeviation": 1.092906420717,
                "min": 1.0,
                "max": 4.0,
                "missingCount": 0,
                "missingPercentage": 0.0,
                "histogram": "[{\"binRange\": [0.997, 1.3], \"count\": 1}, {\"binRange\": [1.3, 1.6], \"count\": 0}, {\"binRange\": [1.6, 1.9], \"count\": 0}, {\"binRange\": [1.9, 2.2], \"count\": 1}, {\"binRange\": [2.2, 2.5], \"count\": 0}, {\"binRange\": [2.5, 2.8], \"count\": 0}, {\"binRange\": [2.8, 3.1], \"count\": 2}, {\"binRange\": [3.1, 3.4], \"count\": 0}, {\"binRange\": [3.4, 3.7], \"count\": 0}, {\"binRange\": [3.7, 4.0], \"count\": 5}]",
                "uniqueCount": 4,
                "variance": 1.1944444444444444,
                "range": 3.0,
                "percentile05": 1.13335,
                "percentile95": 3.973,
                "generatedAt": "2026-06-12T00:00:00+00:00"
              }
            },
            {
              "name": "ISCO 08 Code",
              "primitive_type": "sc:Integer",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 9,
                "mean": 645.0,
                "median": 1111.0,
                "standardDeviation": 557.4262283029029,
                "min": 1.0,
                "max": 1120.0,
                "missingCount": 0,
                "missingPercentage": 0.0,
                "histogram": "[{\"binRange\": [-0.119, 112.9], \"count\": 4}, {\"binRange\": [112.9, 224.8], \"count\": 0}, {\"binRange\": [224.8, 336.7], \"count\": 0}, {\"binRange\": [336.7, 448.6], \"count\": 0}, {\"binRange\": [448.6, 560.5], \"count\": 0}, {\"binRange\": [560.5, 672.4], \"count\": 0}, {\"binRange\": [672.4, 784.3], \"count\": 0}, {\"binRange\": [784.3, 896.2], \"count\": 0}, {\"binRange\": [896.2, 1008.1], \"count\": 0}, {\"binRange\": [1008.1, 1120.0], \"count\": 5}]",
                "uniqueCount": 9,
                "variance": 310724.00000000006,
                "range": 1119.0,
                "percentile05": 12.5956375,
                "percentile95": 1109.929,
                "generatedAt": "2026-06-12T00:00:00+00:00"
              }
            },
            {
              "name": "Title EN",
              "primitive_type": "sc:Text",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 9,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": 0,
                "missingPercentage": 0.0,
                "histogram": null,
                "uniqueCount": 8,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "Definition",
              "primitive_type": "sc:Text",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 9,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": 0,
                "missingPercentage": 0.0,
                "histogram": null,
                "uniqueCount": 8,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "Tasks include",
              "primitive_type": "sc:Text",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 9,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": 0,
                "missingPercentage": 0.0,
                "histogram": null,
                "uniqueCount": 9,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "Included occupations",
              "primitive_type": "sc:Text",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 9,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": 0,
                "missingPercentage": 0.0,
                "histogram": null,
                "uniqueCount": 9,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "ISCO-08 EN Struct and defin",
          "description": "",
          "columns": [
            {
              "name": "Level",
              "primitive_type": "sc:Integer",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 619,
                "mean": 3.602584814216478,
                "median": 4.0,
                "standardDeviation": 0.6900071106725839,
                "min": 1.0,
                "max": 4.0,
                "missingCount": 0,
                "missingPercentage": 0.0,
                "histogram": "[{\"binRange\": [0.997, 1.3], \"count\": 10}, {\"binRange\": [1.3, 1.6], \"count\": 0}, {\"binRange\": [1.6, 1.9], \"count\": 0}, {\"binRange\": [1.9, 2.2], \"count\": 43}, {\"binRange\": [2.2, 2.5], \"count\": 0}, {\"binRange\": [2.5, 2.8], \"count\": 0}, {\"binRange\": [2.8, 3.1], \"count\": 130}, {\"binRange\": [3.1, 3.4], \"count\": 0}, {\"binRange\": [3.4, 3.7], \"count\": 0}, {\"binRange\": [3.7, 4.0], \"count\": 436}]",
                "uniqueCount": 4,
                "variance": 0.47610981277872744,
                "range": 3.0,
                "percentile05": 2.0461627906976743,
                "percentile95": 3.978704128440367,
                "generatedAt": "2026-06-12T00:00:00+00:00"
              }
            },
            {
              "name": "ISCO 08 Code",
              "primitive_type": "sc:Integer",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 619,
                "mean": 3493.928917609047,
                "median": 3111.0,
                "standardDeviation": 2954.134840377685,
                "min": 0.0,
                "max": 9629.0,
                "missingCount": 0,
                "missingPercentage": 0.0,
                "histogram": "[{\"binRange\": [-9.629, 962.9], \"count\": 186}, {\"binRange\": [962.9, 1925.8], \"count\": 31}, {\"binRange\": [1925.8, 2888.7], \"count\": 92}, {\"binRange\": [2888.7, 3851.6], \"count\": 84}, {\"binRange\": [3851.6, 4814.5], \"count\": 29}, {\"binRange\": [4814.5, 5777.4], \"count\": 40}, {\"binRange\": [5777.4, 6740.3], \"count\": 18}, {\"binRange\": [6740.3, 7703.2], \"count\": 66}, {\"binRange\": [7703.2, 8666.1], \"count\": 40}, {\"binRange\": [8666.1, 9629.0], \"count\": 33}]",
                "uniqueCount": 613,
                "variance": 8726912.655133292,
                "range": 9629.0,
                "percentile05": 152.19773413978496,
                "percentile95": 8725.916515151514,
                "generatedAt": "2026-06-12T00:00:00+00:00"
              }
            },
            {
              "name": "Title EN",
              "primitive_type": "sc:Text",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 619,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": 0,
                "missingPercentage": 0.0,
                "histogram": null,
                "uniqueCount": 585,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "Definition",
              "primitive_type": "sc:Text",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 619,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": 0,
                "missingPercentage": 0.0,
                "histogram": null,
                "uniqueCount": 602,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "Tasks include",
              "primitive_type": "sc:Text",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 603,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": 16,
                "missingPercentage": 2.5848142164781907,
                "histogram": null,
                "uniqueCount": 603,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "Included occupations",
              "primitive_type": "sc:Text",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 619,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": 0,
                "missingPercentage": 0.0,
                "histogram": null,
                "uniqueCount": 619,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "Excluded occupations",
              "primitive_type": "sc:Text",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 311,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": 308,
                "missingPercentage": 49.75767366720517,
                "histogram": null,
                "uniqueCount": 302,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "Notes",
              "primitive_type": "sc:Text",
              "semantic_types": [],
              "description": "",
              "statistics": {
                "rowCount": 92,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": 527,
                "missingPercentage": 85.1373182552504,
                "histogram": null,
                "uniqueCount": 87,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        }
      ]
    },
    {
      "file_object_id": "165cb283-002e-4edc-85c5-82624c3826e9",
      "original_format": "sql-db",
      "source_file": "",
      "name": "ds_mathe",
      "description": "",
      "keywords": [],
      "tables": [
        {
          "name": "user_final",
          "description": "",
          "columns": [
            {
              "name": "years_of_experience",
              "primitive_type": "sc:Integer",
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "field_research",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "university",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "student_work",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "teaching",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "uni_degree",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "uni_courses",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "subject_taught",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "position",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "work",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "degree_percentage",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "learning",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "gender",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "study_country",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "enjoy_math",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "typology",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "birth_year",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "hobbies",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "learning_style",
          "description": "",
          "columns": [
            {
              "name": "label",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "platform_materials",
          "description": "",
          "columns": [
            {
              "name": "clicks",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "title",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "date",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "description",
              "primitive_type": "sc:Text",
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "link",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "file_name",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "author",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "languages",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "file_ext",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "type",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "platform__degree",
          "description": "",
          "columns": [
            {
              "name": "label",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "teaching_style",
          "description": "",
          "columns": [
            {
              "name": "label",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "platform__sna__questions",
          "description": "",
          "columns": [
            {
              "name": "date",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "algorithmlevel",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "subtopic",
              "primitive_type": "sc:Integer",
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "level",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "file_name",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "topic",
              "primitive_type": "sc:Integer",
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "file_ext",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "platform__university",
          "description": "",
          "columns": [
            {
              "name": "name",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "vis",
              "primitive_type": "sc:Integer",
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "latitude",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "validated",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "country",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "suggested_by",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "longitude",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "timezone",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "platform_material_keyword",
          "description": "",
          "columns": [
            {
              "name": "platformkeywordid",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "platformmaterialid",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "hobbies",
          "description": "",
          "columns": [
            {
              "name": "label",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "assessment",
          "description": "",
          "columns": [
            {
              "name": "subtopic",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "student_id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "option_selected",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "answer",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "duration",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "question_id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "topic",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "question_level",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "date",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "countries",
          "description": "",
          "columns": [
            {
              "name": "name",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "alpha_3",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "alpha_2",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "roles",
          "description": "",
          "columns": [
            {
              "name": "description",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "work_preference",
          "description": "",
          "columns": [
            {
              "name": "label",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "platform__keywords",
          "description": "",
          "columns": [
            {
              "name": "hidden",
              "primitive_type": "sc:Integer",
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id_top",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id_sub",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "name",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "platform__percentage_degree",
          "description": "",
          "columns": [
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "label",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "platform__topic",
          "description": "",
          "columns": [
            {
              "name": "hidden",
              "primitive_type": "sc:Integer",
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "name",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "material_top_sub",
          "description": "",
          "columns": [
            {
              "name": "platformtopicid",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "platformsubtopicid",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "platformmaterialid",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "material_type",
          "description": "",
          "columns": [
            {
              "name": "description",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "user_gender",
          "description": "",
          "columns": [
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "label",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "platform__subtopic",
          "description": "",
          "columns": [
            {
              "name": "name",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "hidden",
              "primitive_type": "sc:Integer",
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id_top",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "teacher_position",
          "description": "",
          "columns": [
            {
              "name": "label",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "studentwork_preference",
          "description": "",
          "columns": [
            {
              "name": "label",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "teacher_experience",
          "description": "",
          "columns": [
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "label",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "platform__course",
          "description": "",
          "columns": [
            {
              "name": "id",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "label",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        },
        {
          "name": "platform_keyword_snaquestion",
          "description": "",
          "columns": [
            {
              "name": "platformsnaquestionid",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            },
            {
              "name": "platformkeywordid",
              "primitive_type": null,
              "semantic_type": [],
              "description": "",
              "statistics": {
                "rowCount": null,
                "mean": null,
                "median": null,
                "standardDeviation": null,
                "min": null,
                "max": null,
                "missingCount": null,
                "missingPercentage": null,
                "histogram": null,
                "uniqueCount": null,
                "variance": null,
                "range": null,
                "percentile05": null,
                "percentile95": null,
                "generatedAt": null
              }
            }
          ]
        }
      ]
    },
    {
      "file_object_id": "6c0e19d5-9f45-4e8c-92d0-2c51438f3681",
      "original_format": "text",
      "source_file": "tests/assets/dummy_data/data/txt_files/text1.txt",
      "name": "text1",
      "description": "",
      "keywords": [],
      "content": {
        "type": "text",
        "file_path": "tests/assets/dummy_data/data/txt_files/text1.txt"
      }
    },
    {
      "file_object_id": "5d207c9f-5f6e-4952-8f54-c70a71078b2e",
      "original_format": "text",
      "source_file": "tests/assets/dummy_data/data/txt_files/text2.txt",
      "name": "text2",
      "description": "",
      "keywords": [],
      "content": {
        "type": "text",
        "file_path": "tests/assets/dummy_data/data/txt_files/text2.txt"
      }
    },
    {
      "file_object_id": "7559a6df-50ea-4422-beb6-ae1cc07d72f7",
      "original_format": "application/pdf",
      "source_file": "tests/assets/dummy_data/data/pdfs/960.pdf",
      "name": "960.pdf",
      "description": "",
      "keywords": [],
      "content": {
        "type": "application/pdf",
        "file_path": "tests/assets/dummy_data/data/pdfs/960.pdf"
      },
      "raw_content": "By: Ana J\u00falia B. Bezerra\n\u2022 Spectrum\nThe spectrum of a matrix A, denoted by S(A), is the set of all eigenvalues of A.\nIn other words, it consists of all scalar values \u03bb such that there exists a non-zero\nvector v (an eigenvector) for which:\nAv = \u03bbv\nThe spectrum gives a complete picture of the behavior of the matrix\u2019s action in\nterms of scaling along the directions of its eigenvectors.\n\u2022 Spectral Radius\nThe spectral radius of a matrix A, denoted \u03c1(A), is the largest absolute value of\nits eigenvalues. If S(A) is the set of eigenvalues of A, then the spectral radius is:\n\u03c1(A) = max{|\u03bb| : \u03bb \u2208S(A)}\nIn other words, it gives the magnitude of the \"dominant\" eigenvalue, which has\nthe greatest influence on the long-term behavior of the matrix\u2019s powers.\n\u2022 Spectral Shift\nA spectral shift refers to modifying the eigenvalues of a matrix by adding a scalar\nmultiple of the identity matrix I to the original matrix A. If A has eigenvalues\n\u03bb1, \u03bb2, . . . , \u03bbn, then adding cI to A results in a new matrix A + cI, whose\neigenvalues are shifted by c:\nEigenvaluesofA + cI = {\u03bb1 + c, \u03bb2 + c, . . . , \u03bbn + c}\nThis spectral shift preserves the relative spacing between the eigenvalues but\ntranslates them by a fixed amount.\n1\n\nProblems\na) The set of eigenvalues of the matrix A =\n\u0014\u22123\n1\n1\n\u22123\n\u0015\nis?\nIs necessary find the eigenvalues, solving the characteristic equation:\ndet(A \u2212\u03bbI) = 0\nWhere I is the identity matrix, and \u03bb represents the eigenvalues. The characteristic\nequation becomes:\ndet\n\u0014\u22123 \u2212\u03bb\n1\n1\n\u22123 \u2212\u03bb\n\u0015\n= 0\nThe determinant is:\n(\u22123 \u2212\u03bb)(\u22123 \u2212\u03bb) \u2212(1)(1) = \u03bb2 + 6\u03bb + 9 \u22121 = \u03bb2 + 6\u03bb + 8 = 0\nSolve the quadratic equation:\n\u03bb2 + 6\u03bb + 8 = 0\nThus, the eigenvalues are:\n\u03bb1 = \u22122,\n\u03bb2 = \u22124\nThe set of eigenvalues is {\u22122, \u22124}.\nb) The spectral radius of the matrix A =\n\u0014\u22123\n1\n1\n\u22123\n\u0015\nis?\nThe absolute values of the eigenvalues are, according to a):\n|\u03bb1| = 2,\n|\u03bb2| = 4\nThe spectral radius is the largest of these values:\n\u03c1(A) = 4\n2\n\nc) Consider the set {\u22122, 2, 5} of eigenvalues of the real 3 \u00d7 3 matrix A + 3I, where I\ndenotes the identity matrix. Find the eigenvalues of A.\nThe eigenvalues of A + 3I are related to the eigenvalues of A by a shift of +3. In other\nwords:\nEigenvalues of A + 3I = {\u03bb1 + 3, \u03bb2 + 3, \u03bb3 + 3}\nAre given that the eigenvalues of A + 3I are {\u22122, 2, 5}. Therefore, to find the\neigenvalues of A, it is necessary to subtract 3 from each of these values:\nEigenvalues of A = {\u22122 \u22123, 2 \u22123, 5 \u22123} = {\u22125, \u22121, 2}\nEigenvalues of A = {\u22125, \u22121, 2}\nThus, the eigenvalues of A are {\u22125, \u22121, 2}.\nReference: Nicholson, W. K. (2006). Elementary Linear Algebra. ISBN 85-86804-92-4.\n3"
    }
  ]
}
```

## Example: JSON file

The CDD profile of the same `tests/assets/json_stations` dataset shown on the [MoMa profile page](profile-examples-moma.md#example-json-file). A JSON file has the same `columns` layout as a CSV file, plus:

- a `json_profile` block: layout, record path and count, nesting, structure consistency, parse errors, the values found outside the records (`document_metadata`) and a few sample records;
- `json_path` and `repeated` on each column, and `array_length` for fields under an array;
- `jsonTypes` and `topValues` in the statistics, as JSON objects rather than strings;
- `text_content` holding the long text values (`notes`) whole, one entry per station that has them, for CDD to chunk so semantic search reaches inside them.

```json
{
  "@id": "5f3c1e2a-7b4d-4c8e-9a1f-2d6b8e0c4a71",
  "content_url": "/home/mikexydas/PycharmProjects/dataset-profiler/5f3c1e2a-7b4d-4c8e-9a1f-2d6b8e0c4a71",
  "name": "Greek Weather Stations (JSON example)",
  "headline": "Weather station readings in JSON.",
  "description": "Hourly temperature and humidity readings from Greek weather stations, exported as one JSON document with station metadata and nested readings.",
  "keywords": [
    "weather stations",
    "temperature",
    "humidity"
  ],
  "field_of_science": [
    "EARTH AND RELATED ENVIRONMENTAL SCIENCES"
  ],
  "files": [
    {
      "file_object_id": "d86b919a-8913-4179-b690-e438c7a791b6",
      "original_format": "json",
      "source_file": "/home/mikexydas/PycharmProjects/dataset-profiler/tests/assets/json_stations/data/stations.json",
      "name": "stations",
      "description": "This dataset describes meteorological stations and their observations, primarily in Greece. Each record identifies a station by name, operator, location coordinates, elevation, and installed sensors, such as temperature, humidity, and wind. It also includes site-specific notes about station placement and environmental conditions that may affect measurements. Time-stamped readings provide temperature in degrees Celsius and relative humidity, with some stations indicating additional sensor types. The data is sourced from the National Observatory of Athens and is licensed under CC BY 4.0.",
      "keywords": [
        "weather stations",
        "meteorological observations",
        "Greece",
        "temperature",
        "humidity",
        "wind",
        "station metadata",
        "National Observatory of Athens"
      ],
      "json_profile": {
        "shape": "wrapped_records",
        "dialect": null,
        "record_path": "$.stations[*]",
        "record_count": 5,
        "max_depth": 3,
        "path_count": 11,
        "paths_truncated": false,
        "schema_consistency_percentage": 60.0,
        "parse_errors": 0,
        "summary": "This dataset describes meteorological stations and their observations, primarily in Greece. Each record identifies a station by name, operator, location coordinates, elevation, and installed sensors, such as temperature, humidity, and wind. It also includes site-specific notes about station placement and environmental conditions that may affect measurements. Time-stamped readings provide temperature in degrees Celsius and relative humidity, with some stations indicating additional sensor types. The data is sourced from the National Observatory of Athens and is licensed under CC BY 4.0.",
        "document_metadata": {
          "$.meta.source": "National Observatory of Athens",
          "$.meta.generated": "2026-09-30T00:00:00Z",
          "$.meta.license": "CC BY 4.0"
        },
        "sample_records": "[{\"id\": \"NOA-0142\", \"name\": \"Athens - Thiseio\", \"operator\": \"NOA\", \"location\": {\"lat\": 37.9715, \"lon\": 23.7181}, \"elevation_m\": 107, \"sensors\": [\"temperature\", \"humidity\", \"wind\"], \"notes\": \"Rooftop station in the historic centre, next to the observatory dome. Shaded after 16:00 in winter, so afternoon readings run cooler than at nearby street-level stations.\", \"readings\": [{\"ts\": \"2026-09-29T12:00:00Z\", \"temp_c\": 27.4, \"rh\": 41}, {\"ts\": \"2026-09-29T13:00:00Z\", \"temp_c\": 28.1, \"rh\": 38}, {\"ts\": \"2026-09-29T14:00:00Z\", \"temp_c\": 28.6, \"rh\": 36}]}, {\"id\": \"NOA-0207\", \"name\": \"Ioannina - Airport\", \"operator\": null, \"location\": {\"lat\": 39.6964, \"lon\": 20.8222}, \"elevation_m\": 484, \"sensors\": [\"temperature\", \"humidity\"], \"readings\": [{\"ts\": \"2026-09-29T12:00:00Z\", \"temp_c\": 22.0, \"rh\": 55}, {\"ts\": \"2026-09-29T13:00:00Z\", \"temp_c\": 22.7, \"rh\": 51}]}, {\"id\": \"HNMS-16716\", \"name\": \"Heraklion\", \"operator\": \"HNMS\", \"location\": {\"lat\": 35.3387, \"lon\": 25.1806}, \"elevation_m\": 39, \"sensors\": [\"temperature\", \"humidity\", \"wind\", \"… 1 more\"], \"readings\": [{\"ts\": \"2026-09-29T12:00:00Z\", \"temp_c\": 29.3, \"rh\": 47}, {\"ts\": \"2026-09-29T13:00:00Z\", \"temp_c\": 29.5, \"rh\": 45}, {\"ts\": \"2026-09-29T14:00:00Z\", \"temp_c\": 29.1, \"rh\": 46}, \"… 1 more\"]}]"
      },
      "columns": [
        {
          "name": "id",
          "json_path": "$.stations[*].id",
          "primitive_type": "sc:Text",
          "semantic_type": "identifier",
          "description": "",
          "repeated": false,
          "statistics": {
            "rowCount": 5,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": null,
            "uniqueCount": 5,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null,
            "jsonTypes": {
              "string": 5
            },
            "topValues": null
          }
        },
        {
          "name": "name",
          "json_path": "$.stations[*].name",
          "primitive_type": "sc:Text",
          "semantic_type": "location name",
          "description": "",
          "repeated": false,
          "statistics": {
            "rowCount": 5,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": null,
            "uniqueCount": 5,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null,
            "jsonTypes": {
              "string": 5
            },
            "topValues": null
          }
        },
        {
          "name": "operator",
          "json_path": "$.stations[*].operator",
          "primitive_type": "sc:Text",
          "semantic_type": "organization",
          "description": "",
          "repeated": false,
          "statistics": {
            "rowCount": 3,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 2,
            "missingPercentage": 40.0,
            "histogram": null,
            "uniqueCount": 3,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null,
            "jsonTypes": {
              "string": 3
            },
            "topValues": null
          }
        },
        {
          "name": "location.lat",
          "json_path": "$.stations[*].location.lat",
          "primitive_type": "sc:Float",
          "semantic_type": "latitude",
          "description": "",
          "repeated": false,
          "statistics": {
            "rowCount": 5,
            "mean": 37.963300000000004,
            "median": 37.776465,
            "standardDeviation": 1.871798777913833,
            "min": 35.3387,
            "max": 39.771,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": "[{\"binRange\": [35.334267700000005, 35.78193], \"count\": 1}, {\"binRange\": [35.78193, 36.22516], \"count\": 0}, {\"binRange\": [36.22516, 36.66839], \"count\": 0}, {\"binRange\": [36.66839, 37.11162], \"count\": 1}, {\"binRange\": [37.11162, 37.55485], \"count\": 0}, {\"binRange\": [37.55485, 37.99808], \"count\": 1}, {\"binRange\": [37.99808, 38.44131], \"count\": 0}, {\"binRange\": [38.44131, 38.88454], \"count\": 0}, {\"binRange\": [38.88454, 39.32777], \"count\": 0}, {\"binRange\": [39.32777, 39.771], \"count\": 2}]",
            "uniqueCount": 5,
            "variance": 3.5036306649997186,
            "range": 4.432299999999998,
            "percentile05": 35.446183275,
            "percentile95": 39.715596250000004,
            "generatedAt": "2026-10-30T10:56:09.855877+00:00",
            "jsonTypes": {
              "number": 5
            },
            "topValues": null
          }
        },
        {
          "name": "location.lon",
          "json_path": "$.stations[*].location.lon",
          "primitive_type": "sc:Float",
          "semantic_type": "longitude",
          "description": "",
          "repeated": false,
          "statistics": {
            "rowCount": 5,
            "mean": 22.60362,
            "median": 21.9118,
            "standardDeviation": 1.824420588022388,
            "min": 20.8222,
            "max": 25.1806,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": "[{\"binRange\": [20.817841599999998, 21.258039999999998], \"count\": 2}, {\"binRange\": [21.258039999999998, 21.69388], \"count\": 0}, {\"binRange\": [21.69388, 22.12972], \"count\": 1}, {\"binRange\": [22.12972, 22.565559999999998], \"count\": 0}, {\"binRange\": [22.565559999999998, 23.001399999999997], \"count\": 0}, {\"binRange\": [23.001399999999997, 23.43724], \"count\": 0}, {\"binRange\": [23.43724, 23.873079999999998], \"count\": 1}, {\"binRange\": [23.873079999999998, 24.308919999999997], \"count\": 0}, {\"binRange\": [24.308919999999997, 24.74476], \"count\": 0}, {\"binRange\": [24.74476, 25.1806], \"count\": 1}]",
            "uniqueCount": 5,
            "variance": 3.328510481999956,
            "range": 4.3584,
            "percentile05": 20.8728664,
            "percentile95": 25.07164,
            "generatedAt": "2026-10-30T10:56:09.855961+00:00",
            "jsonTypes": {
              "number": 5
            },
            "topValues": null
          }
        },
        {
          "name": "elevation_m",
          "json_path": "$.stations[*].elevation_m",
          "primitive_type": "sc:Integer",
          "semantic_type": null,
          "description": "",
          "repeated": false,
          "statistics": {
            "rowCount": 5,
            "mean": 447.5,
            "median": 151.1,
            "standardDeviation": 513.7447485538579,
            "min": 39.0,
            "max": 1160.0,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": "[{\"binRange\": [37.879, 151.1], \"count\": 2}, {\"binRange\": [151.1, 263.2], \"count\": 0}, {\"binRange\": [263.2, 375.29999999999995], \"count\": 0}, {\"binRange\": [375.29999999999995, 487.4], \"count\": 1}, {\"binRange\": [487.4, 599.5], \"count\": 0}, {\"binRange\": [599.5, 711.5999999999999], \"count\": 0}, {\"binRange\": [711.5999999999999, 823.6999999999999], \"count\": 0}, {\"binRange\": [823.6999999999999, 935.8], \"count\": 0}, {\"binRange\": [935.8, 1047.9], \"count\": 0}, {\"binRange\": [1047.9, 1160.0], \"count\": 1}]",
            "uniqueCount": 4,
            "variance": 263933.6666666667,
            "range": 1121.0,
            "percentile05": 49.2011,
            "percentile95": 1137.58,
            "generatedAt": "2026-10-30T10:56:09.856035+00:00",
            "jsonTypes": {
              "integer": 4,
              "string": 1
            },
            "topValues": null
          }
        },
        {
          "name": "sensors[*]",
          "json_path": "$.stations[*].sensors[*]",
          "primitive_type": "sc:Text",
          "semantic_type": "sensor type",
          "description": "",
          "repeated": true,
          "statistics": {
            "rowCount": 14,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": null,
            "uniqueCount": 5,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null,
            "jsonTypes": {
              "string": 14
            },
            "topValues": [
              {
                "value": "temperature",
                "count": 5
              },
              {
                "value": "humidity",
                "count": 4
              },
              {
                "value": "wind",
                "count": 3
              },
              {
                "value": "pressure",
                "count": 1
              },
              {
                "value": "rainfall",
                "count": 1
              }
            ]
          },
          "array_length": {
            "min": 1,
            "avg": 2.8,
            "max": 4
          }
        },
        {
          "name": "notes",
          "json_path": "$.stations[*].notes",
          "primitive_type": "sc:Text",
          "semantic_type": "description",
          "description": "",
          "repeated": false,
          "statistics": {
            "rowCount": 2,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 3,
            "missingPercentage": 60.0,
            "histogram": null,
            "uniqueCount": 2,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null,
            "jsonTypes": {
              "string": 2
            },
            "topValues": null
          }
        },
        {
          "name": "readings[*].ts",
          "json_path": "$.stations[*].readings[*].ts",
          "primitive_type": "sc:DateTime",
          "semantic_type": "timestamp",
          "description": "",
          "repeated": true,
          "statistics": {
            "rowCount": 13,
            "mean": null,
            "median": null,
            "standardDeviation": null,
            "min": null,
            "max": null,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": null,
            "uniqueCount": 4,
            "variance": null,
            "range": null,
            "percentile05": null,
            "percentile95": null,
            "generatedAt": null,
            "jsonTypes": {
              "string": 13
            },
            "topValues": [
              {
                "value": "2026-09-29T12:00:00Z",
                "count": 5
              },
              {
                "value": "2026-09-29T13:00:00Z",
                "count": 5
              },
              {
                "value": "2026-09-29T14:00:00Z",
                "count": 2
              },
              {
                "value": "2026-09-29T15:00:00Z",
                "count": 1
              }
            ]
          },
          "array_length": {
            "min": 2,
            "avg": 2.6,
            "max": 4
          }
        },
        {
          "name": "readings[*].temp_c",
          "json_path": "$.stations[*].readings[*].temp_c",
          "primitive_type": "sc:Float",
          "semantic_type": "temperature",
          "description": "",
          "repeated": true,
          "statistics": {
            "rowCount": 13,
            "mean": 26.015384615384615,
            "median": 28.357857142857142,
            "standardDeviation": 4.489403478163185,
            "min": 17.2,
            "max": 29.5,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": "[{\"binRange\": [17.1877, 18.43], \"count\": 2}, {\"binRange\": [18.43, 19.66], \"count\": 0}, {\"binRange\": [19.66, 20.89], \"count\": 0}, {\"binRange\": [20.89, 22.119999999999997], \"count\": 1}, {\"binRange\": [22.119999999999997, 23.35], \"count\": 1}, {\"binRange\": [23.35, 24.58], \"count\": 0}, {\"binRange\": [24.58, 25.81], \"count\": 0}, {\"binRange\": [25.81, 27.04], \"count\": 0}, {\"binRange\": [27.04, 28.27], \"count\": 2}, {\"binRange\": [28.27, 29.5], \"count\": 7}]",
            "uniqueCount": 13,
            "variance": 20.154743589743703,
            "range": 12.3,
            "percentile05": 17.5914475,
            "percentile95": 29.385785714285714,
            "generatedAt": "2026-10-30T10:56:09.856224+00:00",
            "jsonTypes": {
              "number": 13
            },
            "topValues": null
          },
          "array_length": {
            "min": 2,
            "avg": 2.6,
            "max": 4
          }
        },
        {
          "name": "readings[*].rh",
          "json_path": "$.stations[*].readings[*].rh",
          "primitive_type": "sc:Integer",
          "semantic_type": "relative humidity",
          "description": "",
          "repeated": true,
          "statistics": {
            "rowCount": 13,
            "mean": 48.69230769230769,
            "median": 45.916666666666664,
            "standardDeviation": 10.570277632624851,
            "min": 36.0,
            "max": 71.0,
            "missingCount": 0,
            "missingPercentage": 0.0,
            "histogram": "[{\"binRange\": [35.965, 39.5], \"count\": 2}, {\"binRange\": [39.5, 43.0], \"count\": 2}, {\"binRange\": [43.0, 46.5], \"count\": 3}, {\"binRange\": [46.5, 50.0], \"count\": 2}, {\"binRange\": [50.0, 53.5], \"count\": 1}, {\"binRange\": [53.5, 57.0], \"count\": 1}, {\"binRange\": [57.0, 60.5], \"count\": 0}, {\"binRange\": [60.5, 64.0], \"count\": 0}, {\"binRange\": [64.0, 67.5], \"count\": 0}, {\"binRange\": [67.5, 71.0], \"count\": 2}]",
            "uniqueCount": 13,
            "variance": 111.73076923076921,
            "range": 35.0,
            "percentile05": 37.113875,
            "percentile95": 69.8625,
            "generatedAt": "2026-10-30T10:56:09.856296+00:00",
            "jsonTypes": {
              "integer": 13
            },
            "topValues": null
          },
          "array_length": {
            "min": 2,
            "avg": 2.6,
            "max": 4
          }
        }
      ],
      "text_content": [
        {
          "section": "notes",
          "subsection": "NOA-0142",
          "text": "Rooftop station in the historic centre, next to the observatory dome. Shaded after 16:00 in winter, so afternoon readings run cooler than at nearby street-level stations."
        },
        {
          "section": "notes",
          "subsection": "NOA-0420",
          "text": "High-altitude site in the Pindus mountains. Snow cover affects the readings from December to March, and the station runs on battery during storms."
        }
      ]
    }
  ]
}
```
