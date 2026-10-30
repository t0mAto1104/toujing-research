<p align="center"><a href="README.md">简体中文</a> | <b>English</b></p>

# Toujing Research Skill

An Agent skill for **A-share company research, financial analysis and verification, report review, and disclosure evidence extraction**.

Version **0.1.0**, extracted independently from [Toujing V3.12.2](https://github.com/t0mAto1104/toujing-fundamental-copilot). Includes selected public-data adapters; requires no Toujing account, website, database or separate a-stock-data installation. The host Agent performs reasoning, searches and writing using its own authorized capabilities.

This repository is **private**. Other users need repository access before installing. This is a portable first release, not the website's complete execution engine.

## Capabilities

- Four research perspectives: business/competition, financial quality, industry/policy, valuation/risk; shared evidence, merged supplementation, review and synthesis.
- Deterministic financial workpapers: exact field aliases, monetary units, same-period growth, TTM, balance reconciliation and selected cash-quality metrics. Each result preserves inputs, formula, periods, units and sources.
- Structured report checks: issuer identity, evidence revision, citations and linked calculation values/units/periods. Separate Agent review for semantic support, reasoning and omissions.
- Disclosure lists, explicitly selected PDF extraction, PDF/TXT/Markdown ingestion and imported excerpts actually read through host search tools.
- Selected Tencent quotes/daily K-lines, Sina financial statements, CNInfo disclosures and bounded fallback endpoints. Optional caller-owned Hithink financial fallback.

Default report modules: synthesis, business, financial quality, industry/policy, peers, valuation/scenarios and risk/tracking. Respect user-defined scope/templates.

## Install

Clone using your already authenticated GitHub client. Never place tokens in URLs or chat:

```bash
git clone https://github.com/t0mAto1104/toujing-research.git
```

Place the complete folder in your Agent's skill directory, such as `~/.codex/skills/toujing-research/` or `~/.claude/skills/toujing-research/`. Do not copy only `SKILL.md`. Inspect existing versions before overwriting user changes. Start a new session and confirm discovery. Alternatively, ask the Agent to use the repository's `SKILL.md` directly.

Other clients must support the relevant script execution, network and search permissions; loading Markdown alone does not provide these capabilities. Parallel execution is optional and requires host support and authorization.

Core tools require **Python 3.10+ and its standard library only**:

```bash
python3 scripts/toujing_cli.py doctor
```

If `trusted_ca_certificates_available` is false or a request reports `tls_certificate_error`, repair the Python runtime's trusted CA configuration or use an existing correctly configured runtime. Never disable TLS verification. This environment failure does not mean every upstream provider is unavailable.

PDF text extraction alone needs the optional dependency:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-pdf.txt
```

On Windows use the virtual environment's `Scripts/python.exe`. Tools do not install dependencies or update themselves. Text/financial workflows work without PDF support.

## Use

Ask your Agent:

> Use $toujing-research to research an A-share company. Verify its identity, explain its business and history, analyze financials and competition, and deliver clear conditional conclusions with sources. Put acquisition gaps in the final appendix.

Or:

> Use $toujing-research to review this report. Locate unsupported facts, calculation or accounting errors, and weak conclusions before rewriting anything.

Standalone data tools:

```bash
python3 scripts/toujing_cli.py collect 600519.SH --out /path/to/task/evidence.json
python3 scripts/toujing_cli.py financials /path/to/task/evidence.json --industry industrial --out /path/to/task/workpaper.json
python3 scripts/toujing_cli.py plan /path/to/task/evidence.json --industry industrial --out /path/to/task/plan.json
```

Replace paths; keep task evidence/reports outside the skill checkout and out of Git. Collection and planning do not invoke a model or automatically produce a researched report. The host follows the skill to read sources, analyze, review, supplement and synthesize.

See [SKILL.md](SKILL.md), [commands](references/commands.md), [data contracts](references/data-contract.md), [financial methods](references/financial-methods.md), and [review guidance](references/report-review.md).

## Data, costs and limitations

Bundled public endpoints need no data-service account/key, but can fail, be rate-limited or change. Optional Hithink fallback requires explicit `--hithink` and the caller's own `HITHINK_FINANCE_API_KEY` environment variable. No website credentials are included or reused. The host model/search may incur charges under the user's plan; no additional model API or paid retry loop is built in.

The seed collector provides one company quote, up to 28 recent statement periods per statement, about 550 calendar days of daily K-lines and up to 40 recent disclosure-list items. It is not the full upstream 87-capability package, a five-year valuation database, OCR engine, brokerage client, background scheduler or point-in-time backtest dataset. Beijing historical K-lines are unsupported by the bundled Tencent adapter; old Beijing codes are rejected to avoid frozen quotes.

Offline mode supports explicit local materials and labeled old public cache. A missing search capability narrows the report scope; it never authorizes fabricated evidence. Current quotes cannot stand in for past-cutoff data. Unknown release dates exclude financial API rows from historical-cutoff calculations; known dates still do not prove unrevised historical vintages.

Missing values, zero, negative values, not-applicable metrics and conflicting sources remain distinct. Consolidated/parent, YTD/quarter, total/attributable profit and TTM/static/forecast valuation are not interchangeable. Simplified CFO minus long-term asset cash payments is not FCFF/FCFE. Bank/broker/insurance and unknown profiles skip manufacturing-only cash/margin metrics.

The report starts with an AI/non-investment-advice disclaimer and direct supported judgments. Detailed data gaps go in the final appendix while decision-changing conditions stay with conclusions. A link, excerpt or PDF text extraction is not full-document reading, visual table verification or an audit opinion. Mechanical validation does not prove semantic support or completeness.

## Safety and validation

Fixed HTTPS destinations, no redirects, credential-origin restrictions, serial pacing, bounded requests, no authenticated public HTTP cache, restrictive local files and untrusted-document handling are included. Prompt injection defenses also depend on the host's tool permissions; a skill cannot guarantee immunity. PDF parsing uses a separate bounded process, not a hardened malware sandbox. No telemetry, secret provisioning, trading, publication or production writes are implied. Read [safety boundaries](references/safety-and-boundaries.md).

```bash
python3 -m unittest discover -s tests -v
```

Offline tests use synthetic fixtures, no real keys/model calls. Optional PDF tests require pypdf. Actual validation and live public-endpoint results are recorded in [VALIDATION.md](VALIDATION.md). Do not infer accuracy or cost improvements from offline tests alone.

## Attribution and license

**Apache-2.0**. Thanks to [Simon Lin's a-stock-data](https://github.com/simonlin1212/a-stock-data) and [Toujing](https://github.com/t0mAto1104/toujing-fundamental-copilot). Original upstream instructions/license are archived under `vendor/a-stock-data/`; [UPSTREAM.json](vendor/a-stock-data/UPSTREAM.json) pins the revision/hash. Adapters are a reviewed subset, not runtime execution of downloaded Markdown or automatic tracking of upstream main.

See [NOTICE](NOTICE) and [third-party notices](THIRD_PARTY_NOTICES.md). Code licensing does not grant redistribution rights to third-party market data, news, research PDFs or licensed API services.
