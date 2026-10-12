# dataset-profiler

Repository of the dataset-profiler DataGEMS service
https://datagems-eosc.github.io/dataset-profiler/

## Getting started with your project

### 1. Clone the repository

```bash
git clone git@github.com:datagems-eosc/dataset-profiler.git
```

### 2. Set Up Your Development Environment

If you do not have `uv` installed, you can install it with

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
After executing the command above, you will need to restart your shell.

`uv` is a python package similar to `poetry`.

Then, install the environment and the pre-commit hooks with

```bash
make install
```

This will also generate your `uv.lock` file

## Document Keywords & Summaries

Every PDF and text document inside a folder of the dataset gets LLM-extracted keywords and a short summary, one SCAYLE call per document. It is on by default:

```bash
ENABLE_DOCUMENT_LLM=true                 # false to skip
DOCUMENT_LLM_MODEL=qwen3.8-flash-next    # default
```

They appear on the document's record set as `keywords` / `summary` (MoMa) and on its `files` entry as `keywords` / `description` (CDD). See the [Document Keywords & Summaries docs](https://datagems-eosc.github.io/dataset-profiler/document-descriptions/) for details.

## Data Quality Detection (opt-in)

The profiler can detect data quality errors in tabular record sets (CSVs, Excel sheets) using an LLM: format inconsistencies (mixed date formats), value errors (negative ages), and consistency errors (`US` vs `USA` vs `United States`). Detection only — the data is never modified.

Enable it and pick a provider via environment variables (see `.env.example`):

```bash
ENABLE_DATA_QUALITY=true
DATA_QUALITY_LLM_PROVIDER=scayle   # or bedrock
```

Detected errors are embedded per record set in the generated profiles under `dataQuality` (Croissant) / `data_quality` (CDD). See the [Data Quality docs](https://datagems-eosc.github.io/dataset-profiler/data-quality/) for details.
