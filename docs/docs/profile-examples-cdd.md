# CDD Profile

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
            "uniqueCount": 4
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
            "uniqueCount": 83
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
            "uniqueCount": 1673
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
            "uniqueCount": 0
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
            "uniqueCount": 0
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
            "uniqueCount": 20
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
            "uniqueCount": 96
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
            "uniqueCount": 5
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
            "uniqueCount": 5
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
            "uniqueCount": 6
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
            "uniqueCount": 2
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
                "uniqueCount": 4
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
                "uniqueCount": 9
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
                "uniqueCount": 8
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
                "uniqueCount": 8
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
                "uniqueCount": 9
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
                "uniqueCount": 9
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
                "uniqueCount": 4
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
                "uniqueCount": 613
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
                "uniqueCount": 585
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
                "uniqueCount": 602
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
                "uniqueCount": 603
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
                "uniqueCount": 619
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
                "uniqueCount": 302
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
                "uniqueCount": 87
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
                "uniqueCount": null
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
      "chunked_content": [
        {
          "section": "",
          "subsection": "",
          "chunks": [
            "A text file (sometimes spelled textfile; an old alternative name is flat file) is a kind of computer file that is structured as a sequence of lines of electronic text. A text file exists stored as data within a computer file system.",
            "In operating systems such as CP/M, where the operating system does not keep track of the file size in bytes, the end of a text file is denoted by placing one or more special characters, known as an end-of-file (EOF) marker, as padding after the last line in a text file.[1] In modern operating systems such as DOS, Microsoft Windows and Unix-like systems, text files do not contain any special EOF character, because file systems on those operating systems keep track of the file size in bytes.[2]",
            "Some operating systems, such as Multics, Unix-like systems, CP/M, DOS, the classic Mac OS, and Windows, store text files as a sequence of bytes, with an end-of-line delimiter at the end of each line",
            "Other operating systems, such as OpenVMS and OS/360 and its successors, have record-oriented filesystems, in which text files are stored as a sequence either of fixed-length records or of variable-length records with a record-length value in the record header.",
            "\"Text file\" refers to a type of container, while plain text refers to a type of content.\n\nAt a generic level of description, there are two kinds of computer files: text files and binary files.[3]",
            "Data storage\nicon\nThis section does not cite any sources. Please help improve this section by adding citations to reliable sources. Unsourced material may be challenged and removed. (September 2024) (Learn how and when to remove this message)",
            "A stylized iconic depiction of a CSV-formatted text file",
            "Because of their simplicity, text files are commonly used for storage of information. They avoid some of the problems encountered with other file formats, such as endianness, padding bytes, or differences in the number of bytes in a machine word",
            "Further, when data corruption occurs in a text file, it is often easier to recover and continue processing the remaining contents. A disadvantage of text files is that they usually have a low entropy, meaning that the information occupies more storage than is strictly necessary.",
            "A simple text file may need no additional metadata (other than knowledge of its character set) to assist the reader in interpretation. A text file may contain no data at all, which is a case of zero-byte file.",
            "Encoding\nicon\nThis section does not cite any sources. Please help improve this section by adding citations to reliable sources. Unsourced material may be challenged and removed. (September 2024) (Learn how and when to remove this message)",
            "The ASCII character set is the most common compatible subset of character sets for English-language text files, and is generally assumed to be the default file format in many situations",
            "It covers American English, but for the British pound sign, the euro sign, or characters used outside English, a richer character set must be used. In many systems, this is chosen based on the default locale setting on the computer it is read on",
            "Prior to UTF-8, this was traditionally single-byte encodings (such as ISO-8859-1 through ISO-8859-16) for European languages and wide character encodings for Asian languages.",
            "Because encodings necessarily have only a limited repertoire of characters, often very small, many are only usable to represent text in a limited subset of human languages",
            "Unicode is an attempt to create a common standard for representing all known languages, and most known character sets are subsets of the very large Unicode character set",
            "Although there are multiple character encodings available for Unicode, the most common is UTF-8, which has the advantage of being backwards-compatible with ASCII; that is, every ASCII text file is also a UTF-8 text file with identical meaning",
            "UTF-8 also has the advantage that it is easily auto-detectable. Thus, a common operating mode of UTF-8 capable software, when opening files of unknown encoding, is to try UTF-8 first and fall back to a locale dependent legacy encoding when it definitely is not UTF-8.",
            "Formats",
            "On most operating systems, the name text file refers to a file format that allows only plain text content with very little formatting (e.g., no bold or italic types). Such files can be viewed and edited on text terminals or in simple text editors",
            "Text files usually have the MIME type text/plain, usually with additional information indicating an encoding.",
            "Microsoft Windows text files",
            "Windows 11's Notepad opening an example text file",
            "DOS and Microsoft Windows use a common text file format, with each line of text separated by a two-character combination: carriage return (CR) and line feed (LF)",
            "It is common for the last line of text not to be terminated with a CR-LF marker, and many text editors (including Notepad) do not automatically insert one on the last line.",
            "On Microsoft Windows operating systems, a file is regarded as a text file if the suffix of the name of the file (the \"filename extension\") is .txt. However, many other suffixes are used for text files with specific purposes",
            "For example, source code for computer programs is usually kept in text files that have file name suffixes indicating the programming language in which the source is written.",
            "Most Microsoft Windows text files use ANSI, OEM, Unicode or UTF-8 encoding. What Microsoft Windows terminology calls \"ANSI encodings\" are usually single-byte ISO/IEC 8859 encodings (i.e",
            "ANSI in the Microsoft Notepad menus is really \"System Code Page\", non-Unicode, legacy encoding), except for in locales such as Chinese, Japanese and Korean that require double-byte character sets",
            "ANSI encodings were traditionally used as default system locales within Microsoft Windows, before the transition to Unicode. By contrast, OEM encodings, also known as DOS code pages, were defined by IBM for use in the original IBM PC text mode display system",
            "They typically include graphical and line-drawing characters common in DOS applications. \"Unicode\"-encoded Microsoft Windows text files contain text in UTF-16 Unicode Transformation Format. Such files normally begin with byte order mark (BOM), which communicates the endianness of the file content",
            "Although UTF-8 does not suffer from endianness problems, many Microsoft Windows programs (i.e. Notepad) prepend the contents of UTF-8-encoded files with BOM,[4] to differentiate UTF-8 encoding from other 8-bit encodings.[5]",
            "Unix text files",
            "On Unix-like operating systems, text files format is precisely described: POSIX defines a text file as a file that contains characters organized into zero or more lines,[6] where lines are sequences of zero or more non-newline characters plus a terminating newline character,[7] normally LF.",
            "Additionally, POSIX defines a printable file as a text file whose characters are printable or space or backspace according to regional rules. This excludes most control characters, which are not printable.[8]",
            "Apple Macintosh text files\nPrior to the advent of macOS, the classic Mac OS system regarded the content of a file (the data fork) to be a text file when its resource fork indicated that the type of the file was \"TEXT\".[9] Lines of classic Mac OS text files are terminated with CR characters.[10]",
            "Being a Unix-like system, macOS uses Unix format for text files.[10] Uniform Type Identifier (UTI) used for text files in macOS is \"public.plain-text\"; additional, more specific UTIs are: \"public.utf8-plain-text\" for utf-8-encoded text, \"public.utf16-external-plain-text\" and \"public.utf16-plain-text\" for utf-16-encoded text and \"com.apple.traditional-mac-plain-text\" for classic Mac OS text files.[9]",
            "Rendering",
            "When opened by a text editor, human-readable content is presented to the user. This often consists of the file's plain text visible to the user",
            "Depending on the application, control codes may be rendered either as literal instructions acted upon by the editor, or as visible escape characters that can be edited as plain text",
            "Though there may be plain text in a text file, control characters within the file (especially the end-of-file character) can render the plain text unseen by a particular method.",
            "Related concepts",
            "The use of lightweight markup languages such as TeX, markdown and wikitext can be regarded as an extension of plain text files, as marked-up text is still wholly or partially human-readable in spite of containing machine-interpretable annotations",
            "Early uses of HTML could also be regarded in this way, although the HTML of modern websites is largely unreadable by humans. Other file formats such as enriched text and CSV can also be regarded as human-interpretable to some degree."
          ]
        }
      ],
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
      "chunked_content": [
        {
          "section": "",
          "subsection": "",
          "chunks": [
            "A text file (sometimes spelled textfile; an old alternative name is flat file) is a kind of computer file that is structured as a sequence of lines of electronic text. A text file exists stored as data within a computer file system.",
            "In operating systems such as CP/M, where the operating system does not keep track of the file size in bytes, the end of a text file is denoted by placing one or more special characters, known as an end-of-file (EOF) marker, as padding after the last line in a text file.[1] In modern operating systems such as DOS, Microsoft Windows and Unix-like systems, text files do not contain any special EOF character, because file systems on those operating systems keep track of the file size in bytes.[2]",
            "Some operating systems, such as Multics, Unix-like systems, CP/M, DOS, the classic Mac OS, and Windows, store text files as a sequence of bytes, with an end-of-line delimiter at the end of each line",
            "Other operating systems, such as OpenVMS and OS/360 and its successors, have record-oriented filesystems, in which text files are stored as a sequence either of fixed-length records or of variable-length records with a record-length value in the record header.",
            "\"Text file\" refers to a type of container, while plain text refers to a type of content.\n\nAt a generic level of description, there are two kinds of computer files: text files and binary files.[3]",
            "Data storage\nicon\nThis section does not cite any sources. Please help improve this section by adding citations to reliable sources. Unsourced material may be challenged and removed. (September 2024) (Learn how and when to remove this message)",
            "A stylized iconic depiction of a CSV-formatted text file",
            "Because of their simplicity, text files are commonly used for storage of information. They avoid some of the problems encountered with other file formats, such as endianness, padding bytes, or differences in the number of bytes in a machine word",
            "Further, when data corruption occurs in a text file, it is often easier to recover and continue processing the remaining contents. A disadvantage of text files is that they usually have a low entropy, meaning that the information occupies more storage than is strictly necessary.",
            "A simple text file may need no additional metadata (other than knowledge of its character set) to assist the reader in interpretation. A text file may contain no data at all, which is a case of zero-byte file.",
            "Encoding\nicon\nThis section does not cite any sources. Please help improve this section by adding citations to reliable sources. Unsourced material may be challenged and removed. (September 2024) (Learn how and when to remove this message)",
            "The ASCII character set is the most common compatible subset of character sets for English-language text files, and is generally assumed to be the default file format in many situations",
            "It covers American English, but for the British pound sign, the euro sign, or characters used outside English, a richer character set must be used. In many systems, this is chosen based on the default locale setting on the computer it is read on",
            "Prior to UTF-8, this was traditionally single-byte encodings (such as ISO-8859-1 through ISO-8859-16) for European languages and wide character encodings for Asian languages.",
            "Because encodings necessarily have only a limited repertoire of characters, often very small, many are only usable to represent text in a limited subset of human languages",
            "Unicode is an attempt to create a common standard for representing all known languages, and most known character sets are subsets of the very large Unicode character set",
            "Although there are multiple character encodings available for Unicode, the most common is UTF-8, which has the advantage of being backwards-compatible with ASCII; that is, every ASCII text file is also a UTF-8 text file with identical meaning",
            "UTF-8 also has the advantage that it is easily auto-detectable. Thus, a common operating mode of UTF-8 capable software, when opening files of unknown encoding, is to try UTF-8 first and fall back to a locale dependent legacy encoding when it definitely is not UTF-8.",
            "Formats",
            "On most operating systems, the name text file refers to a file format that allows only plain text content with very little formatting (e.g., no bold or italic types). Such files can be viewed and edited on text terminals or in simple text editors",
            "Text files usually have the MIME type text/plain, usually with additional information indicating an encoding.",
            "Microsoft Windows text files",
            "Windows 11's Notepad opening an example text file",
            "DOS and Microsoft Windows use a common text file format, with each line of text separated by a two-character combination: carriage return (CR) and line feed (LF)",
            "It is common for the last line of text not to be terminated with a CR-LF marker, and many text editors (including Notepad) do not automatically insert one on the last line.",
            "On Microsoft Windows operating systems, a file is regarded as a text file if the suffix of the name of the file (the \"filename extension\") is .txt. However, many other suffixes are used for text files with specific purposes",
            "For example, source code for computer programs is usually kept in text files that have file name suffixes indicating the programming language in which the source is written.",
            "Most Microsoft Windows text files use ANSI, OEM, Unicode or UTF-8 encoding. What Microsoft Windows terminology calls \"ANSI encodings\" are usually single-byte ISO/IEC 8859 encodings (i.e",
            "ANSI in the Microsoft Notepad menus is really \"System Code Page\", non-Unicode, legacy encoding), except for in locales such as Chinese, Japanese and Korean that require double-byte character sets",
            "ANSI encodings were traditionally used as default system locales within Microsoft Windows, before the transition to Unicode. By contrast, OEM encodings, also known as DOS code pages, were defined by IBM for use in the original IBM PC text mode display system",
            "They typically include graphical and line-drawing characters common in DOS applications. \"Unicode\"-encoded Microsoft Windows text files contain text in UTF-16 Unicode Transformation Format. Such files normally begin with byte order mark (BOM), which communicates the endianness of the file content",
            "Although UTF-8 does not suffer from endianness problems, many Microsoft Windows programs (i.e. Notepad) prepend the contents of UTF-8-encoded files with BOM,[4] to differentiate UTF-8 encoding from other 8-bit encodings.[5]",
            "Unix text files",
            "On Unix-like operating systems, text files format is precisely described: POSIX defines a text file as a file that contains characters organized into zero or more lines,[6] where lines are sequences of zero or more non-newline characters plus a terminating newline character,[7] normally LF.",
            "Additionally, POSIX defines a printable file as a text file whose characters are printable or space or backspace according to regional rules. This excludes most control characters, which are not printable.[8]",
            "Apple Macintosh text files\nPrior to the advent of macOS, the classic Mac OS system regarded the content of a file (the data fork) to be a text file when its resource fork indicated that the type of the file was \"TEXT\".[9] Lines of classic Mac OS text files are terminated with CR characters.[10]",
            "Being a Unix-like system, macOS uses Unix format for text files.[10] Uniform Type Identifier (UTI) used for text files in macOS is \"public.plain-text\"; additional, more specific UTIs are: \"public.utf8-plain-text\" for utf-8-encoded text, \"public.utf16-external-plain-text\" and \"public.utf16-plain-text\" for utf-16-encoded text and \"com.apple.traditional-mac-plain-text\" for classic Mac OS text files.[9]",
            "Rendering",
            "When opened by a text editor, human-readable content is presented to the user. This often consists of the file's plain text visible to the user",
            "Depending on the application, control codes may be rendered either as literal instructions acted upon by the editor, or as visible escape characters that can be edited as plain text",
            "Though there may be plain text in a text file, control characters within the file (especially the end-of-file character) can render the plain text unseen by a particular method.",
            "Related concepts",
            "The use of lightweight markup languages such as TeX, markdown and wikitext can be regarded as an extension of plain text files, as marked-up text is still wholly or partially human-readable in spite of containing machine-interpretable annotations",
            "Early uses of HTML could also be regarded in this way, although the HTML of modern websites is largely unreadable by humans. Other file formats such as enriched text and CSV can also be regarded as human-interpretable to some degree."
          ]
        }
      ],
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
      "chunked_content": [
        {
          "section": "",
          "subsection": "",
          "chunks": [
            "By: Ana J\u00falia B. Bezerra\n\u2022 Spectrum\nThe spectrum of a matrix A, denoted by S(A), is the set of all eigenvalues of A.\nIn other words, it consists of all scalar values \u03bb such that there exists a non-zero\nvector v (an eigenvector) for which:\nAv = \u03bbv\nThe spectrum gives a complete picture of the behavior of the matrix\u2019s action in\nterms of scaling along the directions of its eigenvectors.\n\u2022 Spectral Radius\nThe spectral radius of a matrix A, denoted \u03c1(A), is the largest absolute value of\nits eigenvalues. If S(A) is the set of eigenvalues of A, then the spectral radius is:\n\u03c1(A) = max{|\u03bb| : \u03bb \u2208S(A)}\nIn other words, it gives the magnitude of the \"dominant\" eigenvalue, which has\nthe greatest influence on the long-term behavior of the matrix\u2019s powers.\n\u2022 Spectral Shift\nA spectral shift refers to modifying the eigenvalues of a matrix by adding a scalar\nmultiple of the identity matrix I to the original matrix A. If A has eigenvalues",
            "\u2022 Spectral Shift\nA spectral shift refers to modifying the eigenvalues of a matrix by adding a scalar\nmultiple of the identity matrix I to the original matrix A. If A has eigenvalues\n\u03bb1, \u03bb2, . . . , \u03bbn, then adding cI to A results in a new matrix A + cI, whose\neigenvalues are shifted by c:\nEigenvaluesofA + cI = {\u03bb1 + c, \u03bb2 + c, . . . , \u03bbn + c}\nThis spectral shift preserves the relative spacing between the eigenvalues but\ntranslates them by a fixed amount.\n1",
            "Problems\na) The set of eigenvalues of the matrix A =\n\u0014\u22123\n1\n1\n\u22123\n\u0015\nis?\nIs necessary find the eigenvalues, solving the characteristic equation:\ndet(A \u2212\u03bbI) = 0\nWhere I is the identity matrix, and \u03bb represents the eigenvalues. The characteristic\nequation becomes:\ndet\n\u0014\u22123 \u2212\u03bb\n1\n1\n\u22123 \u2212\u03bb\n\u0015\n= 0\nThe determinant is:\n(\u22123 \u2212\u03bb)(\u22123 \u2212\u03bb) \u2212(1)(1) = \u03bb2 + 6\u03bb + 9 \u22121 = \u03bb2 + 6\u03bb + 8 = 0\nSolve the quadratic equation:\n\u03bb2 + 6\u03bb + 8 = 0\nThus, the eigenvalues are:\n\u03bb1 = \u22122,\n\u03bb2 = \u22124\nThe set of eigenvalues is {\u22122, \u22124}.\nb) The spectral radius of the matrix A =\n\u0014\u22123\n1\n1\n\u22123\n\u0015\nis?\nThe absolute values of the eigenvalues are, according to a):\n|\u03bb1| = 2,\n|\u03bb2| = 4\nThe spectral radius is the largest of these values:\n\u03c1(A) = 4\n2",
            "c) Consider the set {\u22122, 2, 5} of eigenvalues of the real 3 \u00d7 3 matrix A + 3I, where I\ndenotes the identity matrix. Find the eigenvalues of A.\nThe eigenvalues of A + 3I are related to the eigenvalues of A by a shift of +3. In other\nwords:\nEigenvalues of A + 3I = {\u03bb1 + 3, \u03bb2 + 3, \u03bb3 + 3}\nAre given that the eigenvalues of A + 3I are {\u22122, 2, 5}. Therefore, to find the\neigenvalues of A, it is necessary to subtract 3 from each of these values:\nEigenvalues of A = {\u22122 \u22123, 2 \u22123, 5 \u22123} = {\u22125, \u22121, 2}\nEigenvalues of A = {\u22125, \u22121, 2}\nThus, the eigenvalues of A are {\u22125, \u22121, 2}.\nReference: Nicholson, W. K. (2006). Elementary Linear Algebra. ISBN 85-86804-92-4.\n3"
          ]
        }
      ],
      "content": {
        "type": "application/pdf",
        "file_path": "tests/assets/dummy_data/data/pdfs/960.pdf"
      }
    }
  ]
}

```
