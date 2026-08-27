# Message — data quality edge rename (for the MoMa/Neo4j integration)

*Draft to send. What changed, and the exact edits needed on the MoMa side.*

---

Hi,

Following the schema review, two object properties in the data quality schema were renamed. **The profile JSON payload does not change at all** — what changes is two edge labels on your side.

## What changed

The review point was that predicates should read as verbs, not as the nouns they point at. Two of our terms link nodes, and both were named after their target:

| Vocabulary term | Neo4j edge label |
|---|---|
| ~~`dg:dataQuality`~~ → **`dg:hasDataQuality`** | ~~`dataQuality`~~ → **`HAS_DATA_QUALITY`** |
| ~~`dg:error`~~ → **`dg:hasError`** | ~~`error`~~ → **`HAS_ERROR`** |

`HAS_*` matches the convention MoMa already uses for its newest edges — `HAS_COMPARISON`, `HAS_EVIDENCE`, `HAS_TARGET` — rather than introducing a third style.

The resulting shape:

```
(cr:RecordSet)-[:HAS_DATA_QUALITY]->(DataQuality)-[:HAS_ERROR]->(DataQualityError)
```

## What this means for you

- Profile payload — **byte-identical**, no reprofiling needed
- Node labels — **unchanged** (`DataQuality`, `DataQualityError`)
- Property names — **unchanged** (`summary`, `column`, `errorType`, `description`, `totalAffectedRows`, `errorExamples`)
- JSON Schemas — **no edits**

Two files, four lines.

## 1. `domain/mapping.yml`

Only the two `label:` values under `edges:` change:

```yaml
DataQuality:
  id: "@id"
  labels: [ "DataQuality", "@type" ]
  map:
    type: "@type"
    summary: summary
  edges:
    - from: parent
      to: self
      label: HAS_DATA_QUALITY     # <-- was: dataQuality
  children:
    errors: DataQualityError

DataQualityError:
  id: "@id"
  labels: [ "DataQualityError", "@type" ]
  map:
    type: "@type"
    column: column
    errorType: errorType
    description: description
    totalAffectedRows: totalAffectedRows
    errorExamples: examples
  edges:
    - from: parent
      to: self
      label: HAS_ERROR            # <-- was: error
```

**One line that looks like it should change and must not.** In the `RecordSet` spec, the child key stays `dataQuality`:

```yaml
  children:
    field: Field
    dataQuality: DataQuality      # JSON key in the profile, NOT an edge label
```

That key names the property in the Croissant payload. Renaming it to `HAS_DATA_QUALITY` would stop the block from being found at all.

## 2. `domain/schema/edges/edge_constraints.json`

```json
{
    "fromLabel": "cr:RecordSet",
    "label": "HAS_DATA_QUALITY",
    "toLabel": "DataQuality",
    "description": "RecordSet → its data quality detection result"
},
{
    "fromLabel": "DataQuality",
    "label": "HAS_ERROR",
    "toLabel": "DataQualityError",
    "description": "Data quality result → one detected error pattern"
}
```

## Verified

Re-ran through `croissant_to_pgjson` on `assets/profiles/heavy/mathe_heavy.json` to confirm nothing else shifted:

```
DataQuality        labels=['DataQuality', 'dg:DataQuality']
                   props=['summary', 'type']

DataQualityError   labels=['DataQualityError', 'dg:DataQualityError']
                   props=['column', 'description', 'errorExamples', 'errorType',
                          'totalAffectedRows', 'type']

edges: ['HAS_DATA_QUALITY', 'HAS_ERROR']
```

Same nodes, same properties. Only the two relationship types differ.

Cheers,
Mike
