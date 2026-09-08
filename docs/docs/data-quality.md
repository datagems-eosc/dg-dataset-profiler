# Data Quality

The profiler can optionally detect data quality errors in tabular record sets (CSV files and Excel sheets; relational databases are planned). Detection is LLM-assisted and **detection-only**: the profiler reports errors, it never corrects the data.

## How It Works

For each tabular record set, the profiler:

1. Reads the table with all values as strings, preserving the original formatting
2. Builds a compact profile: per-column statistics plus a random sample of up to 100 rows
3. Sends the profile to the configured LLM, which generates a Python detection script
4. Executes the generated script against the full file (in a subprocess, with a 120s timeout)
5. Validates the script's findings and asks the LLM for a one-sentence factual summary
6. Embeds the result in the generated profile

Any failure in this pipeline is logged and swallowed — data quality detection can never break profile generation.

## Detected Error Types

| Error type | Description | Example |
|------------|-------------|---------|
| `format_inconsistency` | Mixed representations of the same format | Dates as `1990-05-12` and `15/03/1985` in one column |
| `value_error` | Impossible or out-of-range values | Negative ages, humidity > 100% |
| `consistency_error` | Same concept written multiple ways | `US`, `USA`, `United States`, `united states` |

The set is closed. The detection script is LLM-written and will occasionally invent a category — a
real run produced `missing_value` — so any entry whose `error_type` is not one of the three is logged
and discarded rather than published. Consumers can rely on the enum.

Plainly missing values are deliberately **not** reported: `missingCount` and `missingPercentage` on
the column statistics already carry that, and duplicating it adds nothing. Conditional emptiness — a
column empty only when another is filled — is a real finding and is reported as a
`consistency_error`.

## Profile Output

Data quality is reported in the **heavy MoMa profile only**. Each tabular `recordSet` gains a `dataQuality` section:

```json
{
  "@type": "cr:RecordSet",
  "@id": "20d566dd-1ff7-4496-94bd-8e12673206f6",
  "name": "patients",
  "field": ["..."],
  "dataQuality": {
    "@type": "dg:DataQuality",
    "@id": "3f2a1c88-1111-4aaa-9999-0123456789ab",
    "summary": "Detected out-of-range ages in the age column, where negative values (\"-5\", \"-2\") appear alongside valid ones, and mixed date formats in admission date (\"1990-05-12\" vs \"15/03/1985\").",
    "errors": [
      {
        "@type": "dg:DataQualityError",
        "@id": "7c4b2d99-2222-4bbb-8888-0123456789cd",
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

Each error entry describes an error **pattern**, not a single bad cell: `totalAffectedRows`
counts every row exhibiting the pattern across the table, while `examples` carries at most five
illustrative occurrences.

The `@id`/`@type` pair on the block and on each error exists so that downstream consumers can
address them as first-class entities — the MoMa knowledge graph turns each into its own node and
discards anything without an identifier.

The **CDD profile does not carry data quality information** — it is intentionally omitted there. The light MoMa profile contains no record sets at all, so it is unaffected as well.

### In the MoMa knowledge graph

The block is materialised as nodes rather than stored as a blob, so individual errors are
queryable:

```
(cr:RecordSet)-[:HAS_DATA_QUALITY]->(DataQuality)-[:HAS_ERROR]->(DataQualityError)
```

`DataQuality` carries the `summary`; each `DataQualityError` carries `column`, `errorType`,
`description`, `totalAffectedRows` and `examples`.

!!! warning "Absence is not a clean bill of health"
    A record set with no `dataQuality` block was **not analysed** — detection is opt-in, tabular-only,
    skips files over 100 MB, and swallows every failure by design. It does not mean the table is clean.
    Anything rendering this to users should distinguish "no errors detected" (a `dataQuality` block whose
    `errors` array is empty) from "not analysed" (no block at all).

### Vocabulary

The terms are defined in `datagems-croissant-extension.ttl`: the classes `dg:DataQuality` and
`dg:DataQualityError`, and the properties `dg:hasDataQuality`, `dg:hasError`, `dg:errorType`,
`dg:totalAffectedRows` and `dg:examples`. In the JSON-LD `@context`, `dataQuality` is declared
as an `@json` literal, because the block nests its own `summary`, `column` and `examples` keys which
would otherwise collide with the identically named record-set and Croissant terms.

The two properties that link nodes are named as verb phrases (`hasDataQuality`, `hasError`) rather
than as the nouns they point at; the attributes on those nodes stay nouns, which is the usual split.

### Why not DQV or SHACL?

The obvious existing vocabularies were considered and are recorded as `rdfs:seeAlso` rather than
reused outright:

- **[DQV](https://www.w3.org/TR/vocab-dqv/)** models quality as a `dqv:QualityMeasurement` — a
  resource scored against a `dqv:Metric` within a `dqv:Dimension`. Detection produces no metric, no
  dimension and no score, so instances would satisfy almost none of it.
- **[SHACL](https://www.w3.org/TR/shacl/)** is the closest structural fit: `sh:ValidationReport`
  holding `sh:ValidationResult`s mirrors this shape almost exactly. But `sh:focusNode` and
  `sh:resultPath` address nodes in an RDF graph, whereas these findings address a column of a CSV.

Declaring `rdfs:subClassOf` against either would entail properties these instances do not have, so
the link is advisory. If detection later produces real metrics — a completeness score, an error rate
per dimension — DQV becomes the right home and this should be revisited.

## Configuration

Data quality detection is **opt-in** and configured entirely through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_DATA_QUALITY` | Enable LLM-based error detection for tabular record sets | `false` |
| `DATA_QUALITY_LLM_PROVIDER` | LLM provider: `scayle` or `bedrock` | `scayle` |
| `DATA_QUALITY_LLM_MODEL` | Model override | `qwen3.6` (scayle), `us.anthropic.claude-sonnet-4-6` (bedrock) |
| `DATA_QUALITY_LLM_TIMEOUT` | LLM request timeout in seconds | `300` |
| `DATA_QUALITY_LLM_MAX_ATTEMPTS` | Attempts per LLM call (initial try + retries) on transient failures | `3` |
| `DATA_QUALITY_LLM_COOLDOWN` | Seconds to skip detection after retries are exhausted (`0` disables) | `300` |

### Retries

Connector setup and both chat calls are retried on transient faults — dropped
connections, request timeouts, rate limits and 5xx responses — with exponential
backoff (2s, then 4s) plus jitter. Authentication errors are **not** retried,
since bad credentials never recover.

SCAYLE authenticates during connector construction, so a network fault surfaces
there rather than on the first completion; the retry wraps construction for that
reason. The connect phase is capped at 10s independently of
`DATA_QUALITY_LLM_TIMEOUT`, so an unreachable host fails in seconds instead of
hanging for the full read timeout.

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
- The generated script is told the same encoding the profiler resolved for the file (see [Architecture → Character Encoding](architecture.md#character-encoding)), so it reads the table exactly as the statistics pass did.
- Relational-database record sets are not yet analysed — detection currently covers CSV files and Excel sheets only.
- The LLM-generated detection script runs in a subprocess on the profiling worker with a hard timeout. The LLM providers used are trusted internal/enterprise services; still, only enable the feature in environments where executing generated analysis code is acceptable.
