# {{name}}

**Purpose:** what this model is for (coordination, PCO backup, resident notice, bid).

## Sources
Inventory in `sources/manifest.json` (sheet, detail, revision, scale, photo IDs). Files are not committed.

## Specs
`specs/*.yaml` — one per area or detail. Every element is `confirmed` (with `source`), `provisional`
(with `source` + reference/tolerance) or `assumed` (with `basis`). Build and verify:

```bash
uv run bm check
uv run bm build {{site}}            # all specs; or {{site}}/<spec>
```

## Products
`products/<name>/product.yaml` declares bespoke pipelines (film, viewer, report) and their steps:
`uv run bm run {{site}}/<name> <step>`.

## Releases
Outputs over 1 MB go to GitHub Releases, not git: `uv run bm publish {{site}}/<product> <files…>` uploads them, records checksums in the product's `release-assets.json`, keeps the local copies out of git, and prints links for the deliverable README. `uv run bm assets pull <manifest>` restores them.
