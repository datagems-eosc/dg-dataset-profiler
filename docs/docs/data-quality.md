# Data Quality

The profiler can optionally detect data quality errors in tabular record sets (CSV files and Excel sheets; relational databases are planned). Detection is LLM-assisted and **detection-only**: the profiler reports errors, it never corrects the data.

## How It Works

For each tabular record set, the profiler:

1. Reads the table with all values as strings, preserving the original formatting
2. Builds a compact profile: per-column statistics plus a random sample of up to 100 rows
3. Sends the profile to the configured LLM, which generates a Python detection script
4. Executes the generated script against the full file (in a subprocess, with a 120s timeout)
5. Validates the script's findings and asks the LLM for a 2-sentence summary
6. Embeds the result in the generated profile

Any failure in this pipeline is logged and swallowed — data quality detection can never break profile generation.

## Detected Error Types

| Error type | Description | Example |
|------------|-------------|---------|
| `format_inconsistency` | Mixed representations of the same format | Dates as `1990-05-12` and `15/03/1985` in one column |
| `value_error` | Impossible or out-of-range values | Negative ages, humidity > 100% |
| `consistency_error` | Same concept written multiple ways | `US`, `USA`, `United States`, `united states` |

## Profile Output

In the Croissant (MoMa) profile each tabular `recordSet` gains a `dataQuality` section:

```json
{
  "@type": "cr:RecordSet",
  "name": "patients",
  "field": ["..."],
  "dataQuality": {
    "summary": "The dataset has moderate data quality issues [...]",
    "errors": [
      {
        "column": "age",
        "errorType": "value_error",
        "description": "Negative or invalid age values detected in age column.",
        "examples": [
          {"value": "-5", "row": 4},
          {"value": "-2", "row": 9}
        ],
        "totalAffectedRows": 3
      }
    ]
  }
}
```

The CDD profile carries the same information as a `data_quality` key (snake_case fields) on each file/table entry.

## Configuration

Data quality detection is **opt-in** and configured entirely through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_DATA_QUALITY` | Enable LLM-based error detection for tabular record sets | `false` |
| `DATA_QUALITY_LLM_PROVIDER` | LLM provider: `scayle` or `bedrock` | `scayle` |
| `DATA_QUALITY_LLM_MODEL` | Model override | `qwen3` (scayle), `us.anthropic.claude-sonnet-4-6` (bedrock) |
| `DATA_QUALITY_LLM_TIMEOUT` | LLM request timeout in seconds | `300` |

### SCAYLE provider

Uses the SCAYLE LLM service through the shared `CommonLLMConnector` (`dataset_profiler/common_llm/`). Requires:

```bash
SCAYLE_BASE_URL=https://<scayle-host>/api
SCAYLE_USERNAME=<username>
SCAYLE_PASSWORD=<password>
SCAYLE_VERIFY_SSL=false   # self-signed certificate
```

### Bedrock provider

Uses AWS Bedrock via the same connector. Requires:

```bash
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_REGION=us-east-1
```

## Limitations & Notes

- **Detection only** — the profiler never modifies or suggests corrections for the data.
- Files larger than **100 MB** are skipped to keep profiling memory bounded (detection loads the full table in memory, unlike the streamed column statistics).
- Row numbers in examples are 1-indexed relative to the first data row and are produced by the generated script, so treat them as indicative.
- The LLM-generated detection script runs in a subprocess on the profiling worker with a hard timeout. The LLM providers used are trusted internal/enterprise services; still, only enable the feature in environments where executing generated analysis code is acceptable.
