# Informal heads-up — 8 dataset properties dropped at ingestion

*Short message, not an issue. Send and see what they want to do with it.*

---

Hi,

Not urgent, and unrelated to the data quality work — but I hit this while converting a profile to
Turtle to check our prefixes, and it looks like it affects data already in Neo4j.

The `Dataset` block in `domain/mapping.yml` looks up **prefixed** keys:

```yaml
    headline: dg:headline
    keywords: dg:keywords
    fieldOfScience: dg:fieldOfScience
    status: dg:status
    access: dg:access
    doi: dg:doi
    uploadedBy: dg:uploadedBy
    archivedAt: sc:archivedAt
```

But the prefix only exists in the JSON-LD *context* — the actual JSON key in the profile is bare:

```json
{ "doi": "10.0000/example", "status": "loaded", "keywords": ["weather"], "headline": "..." }
```

`get_path` does a plain dict lookup, so `dg:doi` never matches and the value is dropped without a
warning. I ran the real profile through `croissant_to_pgjson` to check:

```
name       -> 'Dummy data.'
country    -> 'GR'
headline   -> *** DROPPED ***
keywords   -> *** DROPPED ***
doi        -> *** DROPPED ***
status     -> *** DROPPED ***
```

The unprefixed lookups (`name`, `country`, `description`, …) all work. It is only the eight prefixed
ones that fail, so my guess is they were written from the vocabulary rather than from a sample
payload — an easy thing to get wrong, since in the vocabulary they genuinely are `dg:doi` and
`dg:status`.

Fix is one word per line — `doi: doi`, `status: status`, and so on. `archivedAt: sc:archivedAt`
likewise becomes `archivedAt: archivedAt`.

Two things worth deciding on your side:

- whether already-ingested datasets get re-ingested to pick the values up
- whether it is worth failing loudly, or at least logging, when a `map:` key resolves to nothing —
  this is the third silent-drop we have found in the same engine, and every one of them cost more
  time to find than to fix

Happy to open a proper issue with the reproduction if you'd rather track it.

Cheers,
Mike
