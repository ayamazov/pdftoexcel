---
name: estratto-conto-extract
description: "Deprecated alias. Use the italian-bank-statement-extractor skill instead — it holds the working pipeline, the scripts and the references."
---

# Deprecated — use `italian-bank-statement-extractor`

This skill is kept only so the old name still resolves. Do not follow it.

Everything it described lives in `.claude/skills/italian-bank-statement-extractor/`,
with the scripts it referenced actually present. The paths in the old version were
broken: it called `scripts/*.py` that did not exist in its own directory and
`/home/claude/estratto_toolkit.py`, which does not exist at all.

**Load `italian-bank-statement-extractor` and follow that.**
