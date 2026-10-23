"""Build the files served at https://datagems.eu/ns/ from the vocabulary TTL.

Writes three files into ``vocabulary/ns/``:

* ``datagems.ttl``   -- a copy of ``datagems-croissant-extension.ttl``
* ``context.jsonld`` -- the JSON-LD context the profiler emits, plus the JSON
                        profiling terms declared in the TTL
* ``index.html``     -- human-readable documentation generated from the TTL

Re-run after every change to the TTL. rdflib is not a project dependency, so run
it with::

    uv run --no-project --with rdflib python scripts/build_vocabulary_site.py
"""
import html
import json
import runpy
import shutil
from pathlib import Path

import rdflib
from rdflib.namespace import OWL, RDF, RDFS, XSD

REPO = Path(__file__).resolve().parent.parent
TTL = REPO / "datagems-croissant-extension.ttl"
OUT = REPO / "vocabulary" / "ns"
NS = "https://datagems.eu/ns/"

# Terms the profiler does not emit yet (JSON profiling), but which the published
# context should already resolve. Keep in step with REFERENCES_TEMPLATE once the
# profiler emits them.
JSON_TERMS = {
    "recordPath": "dg:recordPath",
    "jsonShape": "dg:jsonShape",
    "recordCount": "dg:recordCount",
    "maxDepth": "dg:maxDepth",
    "schemaConsistencyPercentage": "dg:schemaConsistencyPercentage",
    "jsonTypes": "dg:jsonTypes",
    "topValues": "dg:topValues",
}

PREFIXES = {
    "https://datagems.eu/ns/": "dg:",
    "http://mlcommons.org/croissant/": "cr:",
    "https://schema.org/": "sc:",
    "http://www.w3.org/2001/XMLSchema#": "xsd:",
    "http://www.w3.org/ns/dqv#": "dqv:",
    "http://www.w3.org/ns/shacl#": "sh:",
    "http://www.w3.org/ns/csvw#": "csvw:",
}


def curie(term) -> str:
    s = str(term)
    for base, prefix in PREFIXES.items():
        if s.startswith(base):
            return prefix + s[len(base):]
    return s


def build_context() -> dict:
    consts = runpy.run_path(str(REPO / "dataset_profiler/profile_components/constants.py"))
    context = {**consts["CONTEXT_TEMPLATE"], **consts["REFERENCES_TEMPLATE"], **JSON_TERMS}
    assert context["dg"] == NS, f"profiler context declares dg = {context['dg']}"
    return {"@context": context}


def describe_domain(g: rdflib.Graph, term) -> str:
    domain = g.value(term, RDFS.domain)
    if domain is None:
        return ""
    union = g.value(domain, OWL.unionOf)
    if union is not None:
        return " or ".join(curie(d) for d in rdflib.collection.Collection(g, union))
    return curie(domain)


def comments(g: rdflib.Graph, term) -> list[str]:
    # Deprecated terms carry two comments: the original and the deprecation note.
    # Show the deprecation note first.
    texts = [str(c) for c in g.objects(term, RDFS.comment)]
    return sorted(texts, key=lambda t: not t.startswith("DEPRECATED"))


def paragraphs(text: str) -> str:
    blocks = [" ".join(b.split()) for b in text.strip().split("\n\n")]
    return "".join(f"<p>{html.escape(b)}</p>" for b in blocks if b)


def term_card(g: rdflib.Graph, term, kind: str) -> str:
    local = str(term)[len(NS):]
    label = g.value(term, RDFS.label)
    deprecated = (term, OWL.deprecated, rdflib.Literal(True)) in g
    rows = [("IRI", f'<code>{html.escape(str(term))}</code>')]
    if kind == "class":
        parent = g.value(term, RDFS.subClassOf)
        if parent is not None:
            rows.append(("Subclass of", f"<code>{curie(parent)}</code>"))
    else:
        dom = describe_domain(g, term)
        if dom:
            rows.append(("Domain", f"<code>{html.escape(dom)}</code>"))
        rng = g.value(term, RDFS.range)
        if rng is not None:
            rows.append(("Range", f"<code>{curie(rng)}</code>"))
    see = sorted(curie(s) for s in g.objects(term, RDFS.seeAlso))
    if see:
        rows.append(("See also", ", ".join(f"<code>{html.escape(s)}</code>" for s in see)))
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    badge = '<span class="dep">deprecated</span>' if deprecated else ""
    body = "".join(paragraphs(c) for c in comments(g, term))
    return (
        f'<article id="{local}" class="term{" is-dep" if deprecated else ""}">'
        f'<h3><a href="#{local}">dg:{local}</a>{badge}</h3>'
        f'<p class="label">{html.escape(str(label or local))}</p>'
        f"<dl>{dl}</dl>{body}</article>"
    )


def build_html(g: rdflib.Graph) -> str:
    onto = rdflib.URIRef(NS)
    title = str(g.value(onto, rdflib.URIRef("http://purl.org/dc/terms/title")))
    version = str(g.value(onto, OWL.versionInfo))
    intro = paragraphs(str(g.value(onto, RDFS.comment)))

    def ours(t):
        return isinstance(t, rdflib.URIRef) and str(t).startswith(NS) and str(t) != NS

    classes = sorted({s for s in g.subjects(RDF.type, RDFS.Class) if ours(s)}, key=str)
    props = sorted({s for s in g.subjects(RDF.type, RDF.Property) if ours(s)}, key=str)

    groups: dict[str, list] = {}
    for p in props:
        groups.setdefault(describe_domain(g, p) or "Other", []).append(p)
    order = sorted(groups, key=lambda d: (d != "sc:Dataset", d != "cr:Field", d))

    toc = "".join(
        f'<li><a href="#{str(c)[len(NS):]}">dg:{str(c)[len(NS):]}</a></li>' for c in classes
    )
    sections = [f'<section><h2 id="classes">Classes</h2>{"".join(term_card(g, c, "class") for c in classes)}</section>']
    for dom in order:
        anchor = "props-" + dom.replace(":", "-").replace(" ", "-")
        cards = "".join(term_card(g, p, "property") for p in groups[dom])
        sections.append(f'<section><h2 id="{anchor}">Properties of <code>{html.escape(dom)}</code></h2>{cards}</section>')
        toc += f'<li><a href="#{anchor}">Properties of {html.escape(dom)}</a></li>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="alternate" type="text/turtle" href="datagems.ttl">
<link rel="alternate" type="application/ld+json" href="context.jsonld">
<style>
:root {{ --bg:#fbfbfd; --fg:#1b2230; --muted:#5c6779; --line:#dfe3ea; --accent:#2f4fb5; --code:#eef1f6; --dep:#9a3412; color-scheme: light; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#11151c; --fg:#e4e8ef; --muted:#9aa4b5; --line:#2a3240; --accent:#94a8ff; --code:#1c2330; --dep:#f0a36c; color-scheme: dark; }} }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width: 860px; margin: 0 auto; padding: 40px 16px 80px; }}
h1 {{ font-size: 2rem; line-height:1.2; margin: 0 0 8px; }}
h2 {{ font-size: 1.35rem; margin: 48px 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--line); }}
h3 {{ font-size: 1.05rem; margin: 0; display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; }}
a {{ color: var(--accent); }}
code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .88em; }}
code {{ background: var(--code); padding: 0 .3em; border-radius: 4px; overflow-wrap:anywhere; }}
pre {{ background: var(--code); padding: 12px 14px; border-radius: 8px; overflow-x: auto; }}
.meta {{ color: var(--muted); }}
.files {{ display:flex; flex-wrap:wrap; gap: 8px 20px; margin: 16px 0; }}
nav ul {{ columns: 2 240px; padding-left: 18px; }}
.term {{ padding: 18px 0; border-bottom: 1px solid var(--line); scroll-margin-top: 12px; }}
.term .label {{ color: var(--muted); margin: 2px 0 8px; }}
.term dl {{ display:grid; grid-template-columns: max-content minmax(0,1fr); gap: 2px 14px; margin: 0 0 8px; font-size: .92rem; }}
.term dt {{ color: var(--muted); }}
.term dd {{ margin: 0; min-width: 0; }}
.term p {{ margin: 6px 0; max-width: 72ch; }}
.is-dep h3 a {{ text-decoration: line-through; }}
.dep {{ font-size: .75rem; font-weight: 600; color: var(--dep); border: 1px solid currentColor; border-radius: 4px; padding: 0 6px; }}
:target {{ background: color-mix(in srgb, var(--accent) 8%, transparent); }}
</style>
</head>
<body>
<main>
<h1>{html.escape(title)}</h1>
<p class="meta">Namespace <code>{NS}</code> · prefix <code>dg:</code> · version {html.escape(version)}</p>
{intro}
<div class="files">
  <a href="datagems.ttl">Vocabulary (Turtle)</a>
  <a href="context.jsonld">JSON-LD context</a>
</div>
<p>Use the published context in a Croissant / JSON-LD document:</p>
<pre>"@context": "{NS}context.jsonld"</pre>
<p>or declare the prefix yourself, exactly as below, including the trailing slash:</p>
<pre>"dg": "{NS}"</pre>
<nav><h2>Contents</h2><ul>{toc}</ul></nav>
{"".join(sections)}
</main>
</body>
</html>
"""


def main() -> None:
    g = rdflib.Graph()
    g.parse(TTL, format="turtle")
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TTL, OUT / "datagems.ttl")
    (OUT / "context.jsonld").write_text(json.dumps(build_context(), indent=2, sort_keys=True) + "\n")
    (OUT / "index.html").write_text(build_html(g))
    print(f"Wrote {', '.join(p.name for p in sorted(OUT.iterdir()))} to {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
