import re
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from src.models.nodes import DomainName, OriginKind, EntityKind

CROSS_REF_RE = re.compile(r"\[(REQUIRES_SAFETY|VALIDATES_WITH|REFERENCES):\s*(DOC-\d+)\s*§(.+?)\]")
ENTITY_RE = re.compile(r"\{\{(Machine|Part|Hazard|Term):(.+?)\}\}")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class CrossRef:
    type: str
    target_doc_id: str
    target_section: str


@dataclass
class EntityMention:
    kind: EntityKind
    name: str


@dataclass
class ParsedStep:
    content: str
    cross_refs: list[CrossRef] = field(default_factory=list)
    entity_mentions: list[EntityMention] = field(default_factory=list)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()

    def clean_content(self) -> str:
        text = CROSS_REF_RE.sub("", self.content)
        text = ENTITY_RE.sub(r"\2", text)
        return text.strip()


@dataclass
class ParsedSection:
    heading: str
    level: int
    steps: list[ParsedStep] = field(default_factory=list)
    children: list["ParsedSection"] = field(default_factory=list)


@dataclass
class ParsedDocument:
    title: str
    domain: DomainName
    doc_id: str
    revision: str
    origin: OriginKind
    sections: list[ParsedSection] = field(default_factory=list)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("Missing or malformed frontmatter")
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    return fm, text[m.end():]


def _parse_step(paragraph: str) -> ParsedStep:
    cross_refs = [
        CrossRef(type=m.group(1), target_doc_id=m.group(2), target_section=m.group(3).strip())
        for m in CROSS_REF_RE.finditer(paragraph)
    ]
    entity_mentions = [
        EntityMention(kind=m.group(1), name=m.group(2).strip())  # type: ignore[arg-type]
        for m in ENTITY_RE.finditer(paragraph)
    ]
    return ParsedStep(content=paragraph.strip(), cross_refs=cross_refs, entity_mentions=entity_mentions)


def parse_document(path: Path) -> ParsedDocument:
    text = path.read_text()
    fm, body = _parse_frontmatter(text)

    doc = ParsedDocument(
        title=fm["title"],
        domain=fm["domain"],  # type: ignore[arg-type]
        doc_id=fm["doc_id"],
        revision=fm["revision"],
        origin=fm["origin"],  # type: ignore[arg-type]
    )

    current_section: ParsedSection | None = None
    current_subsection: ParsedSection | None = None
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        text = "\n".join(paragraph_lines).strip()
        paragraph_lines.clear()
        if not text:
            return
        step = _parse_step(text)
        target = current_subsection or current_section
        if target:
            target.steps.append(step)

    for line in body.splitlines():
        if line.startswith("## "):
            flush_paragraph()
            current_subsection = ParsedSection(heading=line[3:].strip(), level=2)
            if current_section:
                current_section.children.append(current_subsection)
        elif line.startswith("# "):
            flush_paragraph()
            current_subsection = None
            current_section = ParsedSection(heading=line[2:].strip(), level=1)
            doc.sections.append(current_section)
        elif line.strip() == "":
            flush_paragraph()
        else:
            paragraph_lines.append(line)

    flush_paragraph()
    return doc
