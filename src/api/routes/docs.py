import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()

RAW_DIR = Path("data/raw")

ENTITY_RE = re.compile(r"\{\{[^:}]+:([^}]+)\}\}")
XREF_RE = re.compile(r"\[(?:REQUIRES_SAFETY|VALIDATES_WITH|REFERENCES):[^\]]+\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
TABLE_ROW_RE = re.compile(r"^\|")

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, sans-serif; line-height: 1.6; color: #1f2937;
       max-width: 800px; margin: 0 auto; padding: 2rem 1.5rem; }
.meta { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px;
        padding: 1rem 1.25rem; margin-bottom: 2rem; font-size: 0.875rem; color: #6b7280; }
.meta strong { color: #111827; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;
         font-weight: 600; background: #dbeafe; color: #1d4ed8; margin-left: 6px; }
.badge.official { background: #dcfce7; color: #15803d; }
.badge.ai { background: #fef9c3; color: #854d0e; }
h1 { font-size: 1.5rem; font-weight: 700; margin: 2rem 0 0.5rem;
     padding-top: 1rem; border-top: 2px solid #e5e7eb; color: #111827; }
h1:first-of-type { border-top: none; margin-top: 0; }
h2 { font-size: 1.15rem; font-weight: 600; margin: 1.5rem 0 0.5rem; color: #374151; }
p { margin: 0.5rem 0; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.9rem; }
th, td { border: 1px solid #d1d5db; padding: 0.5rem 0.75rem; text-align: left; }
th { background: #f3f4f6; font-weight: 600; }
.toc { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px;
       padding: 1rem 1.25rem; margin-bottom: 2rem; }
.toc h3 { font-size: 0.875rem; font-weight: 600; color: #6b7280;
           text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
.toc a { display: block; color: #2563eb; text-decoration: none;
          font-size: 0.9rem; padding: 2px 0; }
.toc a:hover { text-decoration: underline; }
.toc a.sub { padding-left: 1rem; color: #6b7280; }
"""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _inline(text: str) -> str:
    text = ENTITY_RE.sub(r"\1", text)
    text = XREF_RE.sub("", text)
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    return text.strip()


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    return fm, text[m.end():]


def _render_table(rows: list[str]) -> str:
    parts = ["<table>"]
    for i, row in enumerate(rows):
        if re.match(r"^\|[-| ]+\|$", row.strip()):
            continue
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        tag = "th" if i == 0 else "td"
        parts.append("<tr>" + "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells) + "</tr>")
    parts.append("</table>")
    return "\n".join(parts)


def _doc_path(doc_id: str) -> Path:
    for path in RAW_DIR.glob("*.md"):
        text = path.read_text()
        m = re.search(r'doc_id:\s*"([^"]+)"', text)
        if m and m.group(1) == doc_id:
            return path
    raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")


def _render(doc_id: str) -> str:
    path = _doc_path(doc_id)
    text = path.read_text()
    fm, body = _parse_frontmatter(text)

    title = fm.get("title", doc_id)
    origin = fm.get("origin", "")
    domain = fm.get("domain", "")
    revision = fm.get("revision", "")
    badge_cls = "official" if origin == "official" else "ai"
    badge_label = "Official Standard" if origin == "official" else "AI Paraphrase"

    # Collect headings for TOC
    headings: list[tuple[int, str]] = []
    for line in body.splitlines():
        if line.startswith("## "):
            headings.append((2, line[3:].strip()))
        elif line.startswith("# "):
            headings.append((1, line[2:].strip()))

    toc_items = "".join(
        f'<a href="#{_slug(h)}" class="{"sub" if level == 2 else ""}">{h}</a>'
        for level, h in headings
    )

    html_parts: list[str] = [
        f"<div class='meta'><strong>{domain}</strong> &nbsp;·&nbsp; Rev {revision}"
        f"<span class='badge {badge_cls}'>{badge_label}</span></div>",
        f"<div class='toc'><h3>Sections</h3>{toc_items}</div>",
    ]

    lines = body.splitlines()
    para: list[str] = []
    table_rows: list[str] = []
    in_table = False

    def flush_para() -> None:
        joined = " ".join(para).strip()
        para.clear()
        if joined:
            html_parts.append(f"<p>{_inline(joined)}</p>")

    def flush_table() -> None:
        if table_rows:
            html_parts.append(_render_table(table_rows))
            table_rows.clear()

    for line in lines:
        if TABLE_ROW_RE.match(line):
            if not in_table:
                flush_para()
            in_table = True
            table_rows.append(line)
            continue
        elif in_table:
            flush_table()
            in_table = False

        if line.startswith("## "):
            flush_para()
            h = line[3:].strip()
            html_parts.append(f'<h2 id="{_slug(h)}">{h}</h2>')
        elif line.startswith("# "):
            flush_para()
            h = line[2:].strip()
            html_parts.append(f'<h1 id="{_slug(h)}">{h}</h1>')
        elif line.strip() == "":
            flush_para()
        else:
            stripped = XREF_RE.sub("", line).strip()
            if stripped:
                para.append(stripped)

    flush_para()
    flush_table()

    body_html = "\n".join(html_parts)
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{title}</title>
<style>{CSS}</style></head>
<body>
<h1 style="font-size:1.75rem;border-top:none;margin-bottom:0.25rem">{title}</h1>
{body_html}
</body></html>"""


@router.get("/docs/{doc_id}", response_class=HTMLResponse)
def view_doc(doc_id: str) -> HTMLResponse:
    return HTMLResponse(_render(doc_id))
