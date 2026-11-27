"""The Analytical Pattern (AP) of the document conversion operator.

DMM, the Task Orchestrator, posts the AP as PG-JSON under ``ap``. The profiler
reads its ``Document_Convert_Operator`` node and the FileObjects that node takes
as ``input``, and fills one Markdown ``ResultType`` node per file, which the
Gateway created and the operator points to with ``output``. Every other node
and edge is returned unchanged: DMM passes the AP on to in-dataset-discovery.

```
Analytical_Pattern --consist_of--> Document_Convert_Operator {mode}
Document_Convert_Operator --input-->  cr:FileObject (id only)
Document_Convert_Operator --output--> ResultType {name: "markdown", fileObjectId}
optional: sc:Dataset --distribution--> cr:FileObject
```

Property names are camelCase, as ap-schemas' ``ap-common.schema.json`` requires.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dataset_profiler.document_processing.service import ConversionMode, ConvertResult

OPERATOR_LABEL = "Document_Convert_Operator"
FILE_OBJECT_LABEL = "cr:FileObject"
RESULT_LABEL = "ResultType"
DATASET_LABEL = "sc:Dataset"
MARKDOWN_RESULT_NAME = "markdown"


class APError(ValueError):
    """The AP lacks what the operator needs (answered with 422)."""


@dataclass
class ConvertAP:
    """What the operator reads from the AP, and the nodes it fills."""
    mode: ConversionMode
    file_object_ids: List[str]
    # The Markdown ResultType node of each file: the payload's own dicts, filled in place.
    outputs: Dict[str, dict]
    dataset_id: Optional[str]


def _labels(item: dict) -> list:
    labels = item.get("labels")
    return labels if isinstance(labels, list) else []


def _properties(item: dict) -> dict:
    properties = item.get("properties")
    return properties if isinstance(properties, dict) else {}


def parse_convert_ap(payload: Any) -> ConvertAP:
    ap = payload.get("ap") if isinstance(payload, dict) else None
    if not isinstance(ap, dict) or not isinstance(ap.get("nodes"), list):
        raise APError("The request must hold the Analytical Pattern under 'ap', with 'nodes'")
    nodes = [n for n in ap["nodes"] if isinstance(n, dict) and "id" in n]
    edges = [e for e in (ap.get("edges") or []) if isinstance(e, dict)]
    by_id = {str(n["id"]): n for n in nodes}

    operators = [n for n in nodes if OPERATOR_LABEL in _labels(n)]
    if len(operators) != 1:
        raise APError(f"The AP must have exactly one {OPERATOR_LABEL} node, it has {len(operators)}")
    operator = operators[0]
    operator_id = str(operator["id"])

    mode_value = _properties(operator).get("mode") or ConversionMode.QUALITY.value
    try:
        mode = ConversionMode(mode_value)
    except ValueError:
        raise APError(f"Unknown mode {mode_value!r}; use one of "
                      f"{', '.join(m.value for m in ConversionMode)}")

    def targets(label: str) -> List[dict]:
        found = []
        for edge in edges:
            if str(edge.get("from")) == operator_id and label in _labels(edge):
                node = by_id.get(str(edge.get("to")))
                if node is not None and node not in found:
                    found.append(node)
        return found

    file_object_ids = [str(n["id"]) for n in targets("input") if FILE_OBJECT_LABEL in _labels(n)]
    if not file_object_ids:
        raise APError(f"The {OPERATOR_LABEL} has no input {FILE_OBJECT_LABEL}")

    outputs: Dict[str, dict] = {}
    for node in targets("output"):
        properties = _properties(node)
        file_object_id = properties.get("fileObjectId")
        if (RESULT_LABEL in _labels(node) and file_object_id is not None
                and properties.get("name", MARKDOWN_RESULT_NAME) == MARKDOWN_RESULT_NAME):
            outputs.setdefault(str(file_object_id), node)
    missing = [i for i in file_object_ids if i not in outputs]
    if missing:
        raise APError(f"No Markdown {RESULT_LABEL} output node for FileObject(s) "
                      f"{', '.join(missing)}: the operator needs one per input file, "
                      f"with properties name 'markdown' and fileObjectId")

    return ConvertAP(mode=mode, file_object_ids=file_object_ids, outputs=outputs,
                     dataset_id=_dataset_id(nodes, edges, set(file_object_ids)))


def _dataset_id(nodes: List[dict], edges: List[dict], files: set) -> Optional[str]:
    """The dataset the files belong to: the sc:Dataset distributing them, or the AP's only one."""
    datasets = {str(n["id"]) for n in nodes if DATASET_LABEL in _labels(n)}
    distributing = {str(e.get("from")) for e in edges
                    if "distribution" in _labels(e) and str(e.get("to")) in files} & datasets
    candidates = distributing or datasets
    if len(candidates) > 1:
        raise APError(f"The AP names several datasets ({', '.join(sorted(candidates))}); "
                      f"the files must belong to one")
    return next(iter(candidates), None)


def write_result(node: dict, result: ConvertResult, sha256: str) -> None:
    properties = node.get("properties")
    if not isinstance(properties, dict):
        properties = node["properties"] = {}
    properties.pop("error", None)
    properties.update({
        "value": result.markdown,
        "pages": result.pages,
        "model": result.model,
        "fallbackPages": list(result.fallback_pages),
        "sha256": sha256,
    })


def write_error(node: dict, error: str, sha256: str) -> None:
    properties = node.get("properties")
    if not isinstance(properties, dict):
        properties = node["properties"] = {}
    properties.update({"error": error, "sha256": sha256})
