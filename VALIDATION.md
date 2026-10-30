# Validation · 0.1.0 · 2026-10-31

## Offline checks

- 55 unittest checks passed with Python 3.13 and optional pypdf 6.10.0; includes three PDF parsing checks (blank/needs OCR, encrypted input, text/page location).
- Core tests use synthetic financial data and no network, actual keys, model API or private user documents.
- Checks cover issuer/market mismatch, legacy Beijing code rejection, malformed/nonfinite/bool numbers, missing vs zero, units, parent vs consolidated scope, YTD/TTM formulas, source conflicts, ambiguous duplicate source labels, banking applicability, cash-surplus labeling, financial reconciliation, changed evidence, modified workpapers, unknown references, linked calculation period/unit/value mismatch, inert prompt-injection text, disabled HTML/images in rendered output, cross-security imports, fixed HTTP destinations, no redirects, request budget, stale/expired cache, credential destination/cache/log boundaries, output permissions, partial-failure saving and doctor secret redaction.
- Official skill-creator `quick_validate.py`: passed using PyYAML in a temporary validation environment. PyYAML is not a runtime dependency of this skill.

## Live public-source smoke test

One company (`600519.SH`) was used only as an adapter smoke test, without a model call or any data-service credential:

- Tencent quote and daily K-line: successful; 365 daily bars returned for the requested ~550-calendar-day window.
- Sina statements: 28 periods per statement, 84 rows total, latest observed period 2026-09-30.
- CNInfo issuer mapping and disclosure list: successful, 30 recent identity-filtered documents.
- A selected publicly listed third-quarter filing was downloaded and text extracted from 12 of 12 pages. This tests transport/page extraction, not all financial-table coordinates or all facts in the filing.
- Financial workpaper generated from the saved public packet: 239 calculated rows. Duplicate source labels in some income-statement periods were isolated and retained as explicit field conflicts, without discarding unrelated valid numbers.
- Offline replay of the acquired public HTTP cache succeeded. Stale metadata and acquisition/source dates are preserved.

The initial system Python lacked trusted CA certificates and failed TLS verification for public endpoints. This was diagnosed without weakening TLS; live verification used an existing bundled Python with a valid CA store. `doctor` and transport errors now distinguish this condition. Smoke-test data, cache, downloaded filing and workpapers remain outside this repository.

## Limits of this validation

- No Hithink credential was used; the optional adapter was checked against the existing project's fixed REST contract, not a real account's entitlement. Its availability and response schema still require the caller's authorized request.
- No paid model report was generated, no report accuracy/cost benchmark was performed, and no all-provider/global availability or guaranteed financial correctness is claimed.
- Host-agent behavior, semantic citation support, prompt-injection resistance and judgment quality cannot be certified by unit tests. There is no independent multi-agent end-to-end evaluation in this release.
- PDF extraction is not visual verification or OCR. Real critical financial tables still require source-page inspection.
- Only Python 3.13 was executed locally. Code targets Python 3.10+; cross-version CI can be added when the owner wants ongoing automation.
- Existing Toujing website code, production configuration, user data and deployment were not changed for this extraction.
