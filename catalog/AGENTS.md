# AGENTS.md: FieldMaps International Administrative Boundaries

Guidance for AI agents and LLMs working with this catalog. This file supplements the README with practical, agent-oriented notes.

## Overview

Admin level 0 boundaries built from the U.S. Department of State's LSIB boundary lines, organized as `{license}/{view}/adm0-{polygons,lines,points}/`.

## Collections

- `cc0/` uses State Department World Polygons coastlines and is public domain (CC0-1.0). `odbl/` uses OpenStreetMap coastlines (ODbL-1.0).
- `humanitarian/` groups disputed and autonomous areas with a neighbouring area. `disaggregated/` keeps them as separate features. Pick one view per analysis.
- `adm0-polygons`: areas. `adm0-lines`: land boundary lines, no coastlines. `adm0-points`: one label point per area.

## Data access patterns

- Never combine files from `cc0/` and `odbl/` in one query or output; the result falls under ODbL.
- `adm0_id` is `{adm0_src}-{source date YYYYMMDD}`. Join across releases on `adm0_src`.
- Polygons have one row per row group. Filter on `iso_3` or `adm0_id` to read single areas.

## License

CC0-1.0 under `cc0/`, ODbL-1.0 under `odbl/`. See each collection's `license` and attribution.
