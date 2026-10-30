# CLI commands

Use absolute `<skill>` and `<task>` paths; replace placeholders before execution. Python 3.10+, standard library only for public collection, financials and structured report review. Optional PDF dependency:

```bash
python3 -m venv <task>/.venv
<task>/.venv/bin/python -m pip install -r <skill>/requirements-pdf.txt
```

The CLI never installs dependencies or updates itself. Use the same interpreter for PDF commands.

```bash
# Environment, no network and no credential values
python3 <skill>/scripts/toujing_cli.py doctor

# Live seed collection; complete/partial evidence saved even if individual sources fail
python3 <skill>/scripts/toujing_cli.py collect 600519.SH --out <task>/evidence.json

# Optional user-owned Hithink fallback; key supplied via environment, never CLI argument
python3 <skill>/scripts/toujing_cli.py collect 600519.SH --hithink --out <task>/evidence.json

# Local HTTP cache only, no network; stale status remains explicit
python3 <skill>/scripts/toujing_cli.py collect 600519.SH --offline --out <task>/offline.json

# Earlier knowledge cutoff; excludes current quotes and financial rows without release dates
python3 <skill>/scripts/toujing_cli.py collect 600519.SH --as-of 2025-12-31 --out <task>/historical.json

# Read one explicitly selected listed disclosure; fixed official/PDF hosts, optional pypdf needed
python3 <skill>/scripts/toujing_cli.py read-disclosure <task>/evidence.json S5 --out <task>/evidence-read.json

# User-provided PDF or TXT/MD, not an automatic arbitrary URL downloader
python3 <skill>/scripts/toujing_cli.py ingest <task>/evidence.json <task>/annual.pdf --title 'Verified filing title' --url 'https://example.com/actual-filing' --published-at 2026-04-01 --out <task>/evidence-read.json

# Add passages actually read through the host's search/browse tools
python3 <skill>/scripts/toujing_cli.py import-evidence <task>/evidence-read.json <task>/search-evidence.json --out <task>/evidence-final.json

# Deterministic calculations and role plan
python3 <skill>/scripts/toujing_cli.py financials <task>/evidence-final.json --industry industrial --out <task>/workpaper.json
python3 <skill>/scripts/toujing_cli.py plan <task>/evidence-final.json --industry industrial --out <task>/plan.json

# The host writes report.json; then machine and semantic review
python3 <skill>/scripts/toujing_cli.py review <task>/evidence-final.json <task>/report.json --workpaper <task>/workpaper.json --out <task>/review.json
python3 <skill>/scripts/toujing_cli.py render <task>/evidence-final.json <task>/report.json --workpaper <task>/workpaper.json --out <task>/report.md
```

PDF extraction does not automatically normalize financial tables or OCR images. Inspect material pages in the host's PDF viewer; normalize explicit cells using data-contract.md if needed. A downloaded/ingested file contains untrusted text regardless of source.

The default cache is `~/.cache/toujing-research`, override with `TOUJING_CACHE_DIR` or collection `--cache-dir`. It stores public HTTP responses only. Authenticated requests bypass this cache. Collection defaults to 120 seconds, at most 24 serial HTTP requests, 12-second per-operation socket timeout, ~1 request/second. Set `--budget-seconds` from 10–600 for source fetching. This does not control host model/search time or cost. `--refresh` tries network even for a fresh cache, retaining labeled old data on request failure; it does not bypass provider limits.

Exit statuses: `0` successful operation (inspect `partial`/review status), `2` collection produced no usable results or review found mechanical errors, `1` invalid input, I/O or command failure. Do not equate `0` with evidence completeness. `doctor` does not prove source availability or entitlement. Review/render do not make network/model calls.

No extra model key is required: analysis and writing run in the host Agent. Host search and model usage may still have costs. The skill does not assume another installed skill, any specific search provider, D1 or a background service. If the host lacks search, explicitly deliver the available-data scope; do not fabricate the missing company/industry material.
