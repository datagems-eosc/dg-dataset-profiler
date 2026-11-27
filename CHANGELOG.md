# Changelog

## Unreleased

### Added: MathE document conversion operator

`POST /documents/convert4ap` is the document conversion operator of the MathE keywords Analytical Pattern, called by DMM. It reads the FileObject ids the `Document_Convert_Operator` takes as input, converts their PDFs to Markdown and fills the Markdown `ResultType` node of each file (`value`, `pages`, `model`, `fallbackPages`, `sha256`, or `error`). Every other part of the AP is returned unchanged. `POST /documents/convert` does the same without an AP. One request, one response: each file is converted in its own Ray task, and the request waits at most 240 s (`DOCUMENT_REQUEST_TIMEOUT_SECONDS`).

- **Quality mode** (default) transcribes every page with SCAYLE's `glm-5.3-flash` vision model, formulas as LaTeX; `fast` uses the CPU extraction below.
- **Files are found through MoMa with the caller's token**, so MoMa checks the caller's grant. Only PDFs are converted, and only from the dataset storage (`DATA_ROOT_PATH`), in the AP's dataset when it names one.
- **Conversions are cached** in Redis for 30 days by content hash, mode and model. Degraded and failed conversions are not.
- **Tokens are verified** against Keycloak (signature, issuer, audience `dataset-profiler-api`, role), behind their own switch, `DOCUMENTS_AUTH_ENABLED`, on by default. The `/profiler` endpoints' authentication is unchanged.

Keywords are not generated here: in-dataset-discovery ranks them against the Markdown. New settings: `MOMA_API_URL`, `DOCUMENT_MAX_FILES`, `DOCUMENT_REQUEST_TIMEOUT_SECONDS`, `DOCUMENT_CACHE_TTL_SECONDS`. See [MathE Document Endpoints](docs/docs/mathe-documents.md).

### Added: tests and release notes on every release

Pushing a `v*` tag now runs the test suite first (`.github/workflows/tests.yml`). The API and Ray images are built and pushed only if it passes. A GitHub Release is then created for the tag. Its notes list the commits and merged pull requests since the previous tag (`scripts/release_notes.sh`), and the JUnit test report is attached. The same tests run on pull requests and pushes to `main`.

The runners reach neither SCAYLE nor the dev VPN. Tests marked `live_llm` or `live_data_quality` are left out. So are tests marked `local_dataset`, which profile full datasets kept only under the git-ignored `tests/assets`. The ERA5-Land database tests skip themselves. Seven small fixtures the suite needs are now tracked.

### Changed: PDF text, OCR and document keywords in profiles

- **Scanned PDF pages are OCRed** with Tesseract (English by default, `DOCUMENT_OCR_LANGUAGE`). Their keywords, summary and CDD `raw_content` used to be empty. Handwriting is still beyond reach.
- **PDF text is read in reading order** with PyMuPDF4LLM, also across columns. Pages whose formulas the layout model drops keep their text layer. `raw_content` stays plain text.
- **Documents get at most 5 keywords** (was 8). This applies to PDF, text and JSON files.
- **Document keywords and summaries share a time budget per profiling job**, 10 minutes by default (`DOCUMENT_LLM_TIME_BUDGET_SECONDS`). Documents past it get empty keywords and summary.

New dependencies: `pymupdf4llm` (`>=1.28.2,<2`), `pymupdf` raised to `>=1.28.2,<2`, `pyjwt[crypto]`. The Ray image installs `tesseract-ocr` and `tesseract-ocr-eng`.

### Fixed: column statistics, types, samples and checksums

The structure of the profile is unchanged: the same keys, nesting, `@type`s and `@context`. Only values change. The rules are shared with croissant-laminate; see [Column Statistics](docs/docs/column-statistics.md).

- **Median and the 5th/95th percentiles are exact.** They were interpolated from the 10-bin histogram, which was far off on skewed data (a column of 990 × `1` and 10 × `1,000,000` reported a median of 50,011). Above 20 million numeric values per file they come from a t-digest.
- **Variance and standard deviation are exact** for columns whose mean is large compared with their spread. They used to come out as `0`.
- **`uniqueCount` is exact**, or `null` when a column has too many distinct values to count within the budget. It used to stop counting silently near 100,000, and could report up to 500,000.
- **Column types are decided from every value**, not from 3 random rows. `true`/`false` columns are `sc:Boolean` (they were `sc:Float`). Columns with a leading zero (`01234`) or a few non-numeric values are `sc:Text`, with null numeric statistics, as for any text column. Integer columns with missing values are `sc:Integer` (they were `sc:Float`).
- **Samples are deterministic and hold no missing values.** They are seeded from the file's content and the column's name. Leading-zero columns sample strings (`"01234"`).
- **`sha256` of a file is the hash of its content.** It was the hash of its path.
- **`includes` of a nested file set holds its whole path** (`a/b/*`, not `b/*`).
- **Excel sheet FileObjects carry the right sheet name.** A skipped empty or unreadable sheet used to shift the names of every later sheet.
- **Database samples of `jsonb` and array columns are JSON** (`{"k": 702}`). They were Python reprs (`{'k': 702}`).
- **Non-ASCII text in `examples`, `jsonTypes` and `topValues` is written as it is.** These properties are JSON strings inside the profile, and Greek came out as `\u039c` escapes, readable only after a second `json.loads`. They now hold `Μ`. The value is the same JSON once parsed.
- Malformed CSV rows (skipped or padded by pandas) are counted and logged with their line numbers.
- A warning is logged when a request's database host and port differ from the ones the profiler connects with. The profile still records the request's values.

New dependency: `fastdigest` (`>=0.14,<0.15`). Python 3.10 or later is required (the code already used 3.10 syntax).

### Existing profiles

Profiles created before this release have approximate (histogram-interpolated) medians and percentiles, possibly zero variance for large-valued columns, capped unique counts, `sc:Float` booleans and path-based checksums. They are not regenerated automatically. Editing a dataset re-profiles it with the fixed code. The structure of the profile is unchanged.
