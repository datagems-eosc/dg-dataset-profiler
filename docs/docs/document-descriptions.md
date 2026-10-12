# Document Keywords & Summaries

For every PDF and plain-text document in a dataset, the profiler extracts a short list of **keywords** and a **summary** of the document's content. Structural metadata — page count, author, title — says what a file *is*; keywords and a summary say what it is *about*, which is what dataset discovery searches on.

Both come from a single LLM call per document against the SCAYLE LLM service.

## How It Works

1. The document's text is extracted: PDFs with PyMuPDF (the same pass that produces the CDD `chunked_content`), text files as read for the text statistics.
2. Documents with fewer than **10 words** of extractable text are skipped. Scanned PDFs without a text layer fall here, as do placeholder files; given nothing to describe, the model invents keywords such as `placeholder` or `empty document` instead.
3. The text is sent to the model, capped at the first **24,000 characters**. Course sheets and teaching material fit whole; longer documents are described from their beginning, where the title, abstract and table of contents live.
4. The model returns up to **8 keywords** and a summary of at most **150 words**, both in the language of the document. Duplicate keywords (ignoring case) are dropped.

Extraction is **best-effort**. If the LLM is unreachable, the model id is not served, or the answer cannot be parsed, the failure is logged and the document gets empty `keywords` and an empty `summary` — profiling continues. Losing an enrichment must never fail a profile.

### Which documents are described

A document gets a record set — and therefore keywords and a summary — only when it sits **inside a folder** of the dataset, so that the folder is listed as a `cr:FileSet`:

```
<dataset>/
└── course_sheets/              ← cr:FileSet
    └── IPB_Offering_example.pdf  ← cr:FileObject + cr:RecordSet (keywords, summary)
```

A PDF or text file placed directly at the dataset root is listed in the `distribution`, but has no record set and is not described.

## Profile Output

### MoMa profile

Keywords and summary appear on the document's `cr:RecordSet` in the heavy profile:

```json
{
  "@type": "cr:RecordSet",
  "name": "IPB_Offering_example.pdf",
  "source": { "@type": "cr:FileObject", "@id": "55038d8b-2743-42d4-8311-5de74c285bdc" },
  "title": "ECTS Guide Artificial Intelligence",
  "author": "Instituto Politécnico de Bragança, School of Technology and Management",
  "pagesCount": 2,
  "keywords": [
    "Artificial Intelligence",
    "Machine Learning",
    "Python",
    "Scikit-learn",
    "Supervised Learning",
    "Unsupervised Learning",
    "Clustering",
    "Dimensionality Reduction"
  ],
  "summary": "This document describes the Artificial Intelligence course unit for the Bachelor in Informatics Engineering at the School of Technology and Management, academic year 2024/2025. …",
  "field": []
}
```

In the JSON-LD `@context`, `summary` resolves to `dg:summary`; `keywords` is `schema:keywords`.

!!! note "Not the dataset's keywords"
    The top-level `keywords` of the profile are the ones submitted in the profiling request and are
    never changed. The extracted keywords live on each document's record set.

### CDD profile

The same values appear on the document's entry in `files`, with the summary under `description`:

```json
{
  "file_object_id": "55038d8b-2743-42d4-8311-5de74c285bdc",
  "original_format": "application/pdf",
  "name": "IPB_Offering_example.pdf",
  "description": "This document describes the Artificial Intelligence course unit for the Bachelor in Informatics Engineering at the School of Technology and Management, academic year 2024/2025. …",
  "keywords": ["Artificial Intelligence", "Machine Learning", "Python", "…"],
  "chunked_content": [ { "section": "", "subsection": "", "chunks": ["…"] } ]
}
```

## Configuration

Extraction is **on by default** and uses the SCAYLE credentials shared with the other LLM features:

```bash
SCAYLE_BASE_URL=https://<scayle-host>/api
SCAYLE_USERNAME=<username>
SCAYLE_PASSWORD=<password>
SCAYLE_VERIFY_SSL=false   # self-signed certificate

ENABLE_DOCUMENT_LLM=true                 # set to false to skip keywords and summaries
DOCUMENT_LLM_MODEL=qwen3.8-flash-next    # default; any id the endpoint serves
DOCUMENT_LLM_TIMEOUT=120                 # seconds per request
```

Unlike semantic type annotation, this feature does not read `llm_config.yaml`: that file pins a 30-second SCAYLE timeout, too short for long documents.

!!! warning "Model identifiers are case-sensitive and drift"
    SCAYLE model ids change over time and are matched exactly. A retired id makes every document come
    back with empty `keywords` and `summary` while the job still succeeds. List the models the endpoint
    serves before changing `DOCUMENT_LLM_MODEL`, and check the logs for
    `Document keyword and summary extraction failed`, logged once per failed document with the error.

## Limitations & Notes

- **One LLM call per document**, a few seconds each with the default model. A folder of several hundred PDFs adds tens of minutes to the heavy profile; set `ENABLE_DOCUMENT_LLM=false` when that is not worth it.
- **Scanned PDFs** have no text layer and are skipped: no OCR is run.
- **Long documents** are described from their first 24,000 characters only.
- Output is free text, not a controlled vocabulary, and wording varies slightly between runs.
