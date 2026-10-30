# Financial methods

## Contract before formulas

Use exact financial synonyms. Attributable profit is not total net profit. Operating revenue and total operating revenue are different fields; do not substitute automatically. Total liabilities are not interest-bearing debt; total equity is not attributable equity. A cash-flow change is not the cash balance. Preserve raw field labels and IDs alongside normalized values.

Normalize yuan/ten-thousand yuan/hundred-million yuan before comparisons. Keep per-share units distinct. Confirm consolidated vs parent-only, balance vs YTD vs standalone quarter, and fiscal periods. Statements from different currencies or scopes are not combinable. Conflicting normalized values remain separate evidence and are excluded from affected calculations; materiality/reconciliation needs review, not arbitrary last-wins selection.

## Implemented deterministic calculations

`financials` calculates only when required matching inputs exist:

- Same-period revenue and attributable-profit growth; prior nonpositive values are not conventional growth rates.
- Liability/assets, and assets = liabilities + total-equity reconciliation.
- TTM = previous FY + current YTD − previous same-period YTD.
- For an explicitly nonfinancial `industrial` profile: gross margin, R&D/revenue, approximate CFO/attributable profit, CFO − disclosed cash paid for long-term assets, approximate AR days based on elapsed YTD days, goodwill/attributable equity.

Every calculation retains original source IDs, values, fields, periods, units, formula and limitations. The workpaper is bound to the exact packet. It never calculates from prose, rounds missing data to zero, annualizes one quarter times four or produces a target price.

The simplified cash surplus is not standard FCFF/FCFE; it omits some capital investment and does not establish financing cash flow. CFO/attributable profit mixes consolidated CFO and attributable earnings and is labeled approximate. AR days uses average opening/closing AR and operating revenue, not a disclosed credit-sales denominator. A reconciliation tolerance is a mechanical rounding check, not a clean audit opinion.

## Industry adaptation

- **Banks:** explain interest-earning assets/yields, deposit structure/cost, NIM, fees, credit cost, NPL, provisions, ROE and capital adequacy. Distinguish parent regulatory capital and consolidated accounting. Do not grade cash conversion, inventory or manufacturing gross margin.
- **Brokers:** separate brokerage/wealth, investment banking, asset management, investment/trading and international operations. Use net capital, risk coverage, liquidity and leverage. Market turnover is not company revenue. Fair-value gains need cycle/repeatability analysis.
- **Insurance:** distinguish life NBV, P&C combined ratio, investment return and solvency; accounting standard changes can break comparisons.
- **Industrial/general nonfinancial:** volumes × realized prices, unit costs, utilization, mix and working capital explain profitability. Market quotes are not company settlement prices. Planned capacity, built capacity, trial production and utilization are different.
- **Unknown:** resolve the business before applying nonfinancial checks. Missing NIM does not prove manufacturing; missing inventory does not prove poor disclosure.

Specialized operating/regulatory metrics are not auto-collected by this seed tool. Obtain them from actually read reports and cite pages. Null or not-applicable stays distinct from missing.

## Additional valuation/growth analysis

Use snapshot PE TTM as a dated source value; static PE, forecast PE and MRQ cannot be relabeled TTM/dynamic PE. Negative/zero profit does not imply cheapness. Historical percentiles need a real date-aligned series, a stated window, coverage, and a consistent valuation definition; the bundled 550-calendar-day K-line is not five-year valuation history. Price series is additive source-qfq, not a total-return index. Do not fabricate PEG, EV/EBITDA, FCFF, capacity utilization or five-year charts when inputs are absent.

Any additional formula must be computed in a saved script/workpaper with exact sourced inputs and assumptions. Choose comparable peers by business, accounting and period; a failure to retrieve peers restricts relative valuation, not all company analysis. Financial APIs may be restated and often lack release dates: historical-cutoff studies must exclude unknown-availability inputs and cannot claim point-in-time backtest quality.
