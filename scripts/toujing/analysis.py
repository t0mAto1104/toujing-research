"""Deterministic financial workpapers; results bind inputs, periods and sources."""
from datetime import date

from .core import amount, digest, number, validate_packet
from .providers import ALIASES

PARENT_PROFIT = "归属于母公司所有者的净利润"
CFO = "经营活动产生的现金流量净额"
CAPEX = "购建固定资产、无形资产和其他长期资产支付的现金"


def financials(p, industry="unknown"):
    validate_packet(p)
    grouped, issues = {}, list(p["gaps"])
    for row in p["statements"]:
        for field, values in row.get("field_conflicts", {}).items():
            issues.append({"module": "financials", "reason": "ambiguous_source_field", "period": row["period"],
                           "field": field, "source_id": row["source_id"], "values": values,
                           "detail": "Repeated source title carries different field IDs/values; field excluded, other values retained"})
        for name, value in row["values"].items():
            if value is None:
                continue
            field = ALIASES.get(name, name)
            unit = "元/股" if field == "基本每股收益" else row["unit"]
            value = amount(value, unit)
            key = (row["period"], row["statement"], row["scope"], row["basis"], field)
            grouped.setdefault(key, []).append({"value": value, "source_id": row["source_id"],
                                                "period": row["period"], "field": field,
                                                "unit": "元/股" if field == "基本每股收益" else "元"})
    clean = {}
    for key, inputs in grouped.items():
        vals = {r["value"] for r in inputs}
        if len(vals) != 1:
            issues.append({"module": "financials", "reason": "source_conflict", "field": key[-1],
                           "period": key[0], "inputs": inputs,
                           "detail": "Conflicting normalized values; excluded from calculation"})
        else:
            clean[key] = inputs
    calculations = []

    def inputs(period, statement, field):
        # Parent-only and unknown-scope rows remain evidence, not consolidated calculations.
        return clean.get((period, statement, "consolidated",
                          "balance" if statement == "fzb" else "ytd", field))

    def add(label, formula, groups, operation, unit, period, boundary=""):
        if not all(groups):
            return
        values = [g[0]["value"] for g in groups]
        result = operation(*values)
        if result is None:
            return
        record = {"label": label, "formula": formula, "period": period, "value": round(result, 8),
                  "unit": unit, "inputs": [r for g in groups for r in g], "boundary": boundary}
        record["id"] = "C-" + digest(record)[:12]
        calculations.append(record)

    periods = sorted({r["period"] for r in p["statements"]})
    for period in periods:
        rev = inputs(period, "lrb", "营业收入")
        profit = inputs(period, "lrb", PARENT_PROFIT)
        cash = inputs(period, "llb", CFO)
        assets = inputs(period, "fzb", "资产总计")
        debt = inputs(period, "fzb", "负债合计")
        equity = inputs(period, "fzb", "所有者权益合计")
        previous = str(int(period[:4]) - 1) + period[4:]
        for name, field, current in (("营业收入同比", "营业收入", rev), ("归母净利润同比", PARENT_PROFIT, profit)):
            add(name, "(current / previous_same_period - 1) * 100",
                [current, inputs(previous, "lrb", field)],
                lambda a, b: (a / b - 1) * 100 if b > 0 else None, "%", period,
                "上年同期非正值不计算常规增长率；累计与累计比较")
        add("资产负债率", "liabilities / assets * 100", [debt, assets],
            lambda a, b: a / b * 100 if b > 0 else None, "%", period)
        if assets and debt and equity:
            delta = assets[0]["value"] - debt[0]["value"] - equity[0]["value"]
            if abs(delta) > max(1, abs(assets[0]["value"]) * 0.0001):
                issues.append({"module": "financials", "reason": "balance_mismatch", "period": period,
                               "difference_cny": delta, "detail": "Assets do not reconcile with liabilities + total equity"})
        if industry in ("bank", "broker", "insurance", "unknown"):
            continue
        add("销售毛利率", "(revenue - operating_cost) / revenue * 100",
            [rev, inputs(period, "lrb", "营业成本")],
            lambda a, b: (a - b) / a * 100 if a > 0 else None, "%", period)
        add("研发费用率", "R&D_expense / revenue * 100",
            [inputs(period, "lrb", "研发费用"), rev],
            lambda a, b: a / b * 100 if b > 0 else None, "%", period)
        add("经营现金流/归母净利", "CFO / attributable_profit", [cash, profit],
            lambda a, b: a / b if b > 0 else None, "倍", period,
            "经营现金流为合并口径，归母净利不含少数股东损益；仅作近似现金质量观察")
        add("简化经营现金结余", "CFO - cash_paid_for_long_term_assets",
            [cash, inputs(period, "llb", CAPEX)],
            lambda a, b: a - b if b >= 0 else None, "元", period,
            "不是标准 FCFF/FCFE；不重复扣营运资本，不含全部资本投入")
        year_start = str(int(period[:4]) - 1) + "-12-31"
        days = (date.fromisoformat(period) - date(int(period[:4]), 1, 1)).days + 1
        add("应收账款周转天数（近似）", "average_AR / YTD_revenue * elapsed_days",
            [inputs(year_start, "fzb", "应收账款"), inputs(period, "fzb", "应收账款"), rev],
            lambda a, b, c: (a + b) / 2 / c * days if c > 0 else None, "天", period,
            "使用期初期末平均应收及营业收入；非赊销收入明细口径")
        add("商誉/归母净资产", "goodwill / parent_equity * 100",
            [inputs(period, "fzb", "商誉"), inputs(period, "fzb", "归属于母公司股东权益合计")],
            lambda a, b: a / b * 100 if b > 0 else None, "%", period)

    # TTM from FY(t-1) + YTD(t) - YTD(t-1), never a quarter times four.
    for period in periods:
        if period.endswith("12-31"):
            continue
        year = int(period[:4])
        for field in ("营业收入", PARENT_PROFIT):
            add(field + " TTM", "previous_FY + current_YTD - previous_same_YTD",
                [inputs(f"{year-1}-12-31", "lrb", field), inputs(period, "lrb", field),
                 inputs(f"{year-1}{period[4:]}", "lrb", field)], lambda a, b, c: a + b - c,
                "元", period, "所有输入须同证券、币种、合并口径；重述与会计政策变更需人工核验")
    return {"schema_version": 1, "security": p["security"]["id"], "packet_hash": digest(p),
            "industry": industry, "calculations": calculations, "issues": issues,
            "boundary": "程序计算不验证源端数字真实性；unknown 行业不套用制造业指标"}
