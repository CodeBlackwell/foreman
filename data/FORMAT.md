# Synthetic Document Format

Each document is a markdown file in data/raw/.

## File naming

`<domain>_<slug>.md`  (e.g. safety_loto.md, maintenance_press.md, quality_inspection.md)

## Required frontmatter (YAML block at top of file)

```
---
title: "Full Document Title"
domain: Safety | Maintenance | QualityControl
doc_id: "DOC-001"  # unique across all docs
revision: "1.0"
origin: official | ai_paraphrase
---
```

## Heading structure

`# Section heading`  (level 1 = top-level section)
`## Subsection`      (level 2 = subsection, parsed as child Section)

## Step content

Steps are paragraphs under a heading. Each paragraph becomes one Step node.
A paragraph that begins with a number followed by a period (e.g. "1. ") is a procedure step.

## Cross references

To link a Step to another document use the tag on its own line:

```
[REQUIRES_SAFETY: DOC-001 §Section heading]
[VALIDATES_WITH: DOC-003 §Section heading]
[REFERENCES: DOC-002 §Section heading]
```

## Entity mentions

Wrap entity mentions in double braces to extract them as Entity nodes:

```
{{Machine:X200 Press}}
{{Part:Drive Bearing}}
{{Hazard:Stored Energy}}
{{Term:LOTO}}
```
