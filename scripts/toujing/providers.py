"""Fixed public adapters, adapted from a-stock-data 3.10.3 and Toujing 3.12.2.

Copyright 2026 Simon Lin (upstream protocols/examples), Toujing contributors.
Changes: stdlib transport, strict identity/null/date contracts, bounded fetches.
"""
import html
import os
import re
from datetime import datetime

from .core import CHINA, DataError, checked_date, number, source

SINA = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
HITHINK = "https://fuyao.aicubes.cn/api/a-share/financials/"
FIELDS = {
    "operating_income": "营业收入", "operating_costs": "营业成本",
    "operating_profit": "营业利润", "profit_total": "利润总额", "net_profit": "净利润",
    "parent_holder_net_profit": "归属于母公司所有者的净利润", "basic_eps": "基本每股收益",
    "income_tax_expense": "所得税费用", "manage_fee": "管理费用", "sales_fee": "销售费用",
    "research_and_development_expenses": "研发费用", "assets_total": "资产总计",
    "total_debt": "负债合计", "holder_equity_total": "所有者权益合计", "cash": "货币资金",
    "accounts_receivable": "应收账款", "act_cash_flow_net": "经营活动产生的现金流量净额",
    "invest_cash_flow_net": "投资活动产生的现金流量净额",
    "financing_cash_flow_net": "筹资活动产生的现金流量净额",
    "pay_fixed_assets_etc_cash": "购建固定资产、无形资产和其他长期资产支付的现金",
    "cash_equivalents_net_addition": "现金及现金等价物净增加额"}
ALIASES = {
    "归属于母公司股东的净利润": "归属于母公司所有者的净利润",
    "归属于母公司的净利润": "归属于母公司所有者的净利润",
    "购建固定资产、无形资产和其他长期资产所支付的现金": "购建固定资产、无形资产和其他长期资产支付的现金",
    "归属于母公司所有者权益合计": "归属于母公司股东权益合计",
    "所有者权益(或股东权益)合计": "所有者权益合计",
    "所有者权益（或股东权益）合计": "所有者权益合计"}


def plain(text):
    return html.unescape(re.sub(r"<[^>]*>", "", str(text)))


def parse_quote(text, security):
    m = re.search(r'v_' + re.escape(security["symbol"]) + r'="([^"\n]*)"', text)
    if not m:
        raise DataError("empty_result", "Requested quote not returned")
    v = m.group(1).split("~")
    if len(v) < 53 or v[2] != security["code"] or not v[1].strip():
        raise DataError("identity_mismatch", "Quote identity/shape mismatch")
    try:
        stamp = datetime.strptime(v[30], "%Y%m%d%H%M%S").replace(tzinfo=CHINA).isoformat()
    except ValueError:
        raise DataError("missing_source_time", "Quote timestamp missing or invalid") from None
    if datetime.fromisoformat(stamp) > datetime.now(CHINA):
        raise DataError("future_source_time", "Quote timestamp is in the future")
    price = number(v[3])
    if price is None or price <= 0:
        raise DataError("invalid_quote", "Quote has no positive price")
    return {"name": v[1], "price": price, "previous_close": number(v[4]),
            "change_pct": number(v[32]), "turnover_pct": number(v[38]), "pe_ttm": number(v[39]),
            "market_cap_cny": None if number(v[45]) is None else number(v[45]) * 1e8,
            "pb": number(v[46]), "source_time": stamp, "currency": "CNY",
            "inactive_possible": number(v[37]) == 0}


def quote(client, p):
    text, meta = client.fetch("https://qt.gtimg.cn/q=" + p["security"]["symbol"], ttl=60)
    data = parse_quote(text, p["security"])
    if data["source_time"][:10] > p["as_of"]:
        raise DataError("after_cutoff", "Current quote cannot be used for a historical research cutoff")
    sid = source(p, "腾讯行情快照", meta.pop("url"), "quote", **meta,
                 source_time=data["source_time"])
    p["security"]["name"] = data.pop("name")
    p["observations"].append({"kind": "quote", "source_id": sid, "data": data})


def parse_sina(data, kind, security, sid, cutoff):
    root = ((data.get("result") or {}).get("data") or {}).get("report_list")
    if not isinstance(root, dict):
        raise DataError("parse_error", "Sina report_list missing")
    rows = []
    for raw_period, report in sorted(root.items(), reverse=True)[:28]:
        if not re.fullmatch(r"\d{8}", raw_period):
            continue
        period = checked_date(f"{raw_period[:4]}-{raw_period[4:6]}-{raw_period[6:]}")
        if period > cutoff:
            continue
        values, origins, conflicts = {}, {}, {}
        for item in report.get("data") or []:
            title = plain(item.get("item_title", "")).strip()
            title = ALIASES.get(title, title)
            field = item.get("item_field")
            if kind == "lrb" and field == "NETPARECOMPPROF":
                if title not in ("归属于母公司所有者的净利润", ""):
                    raise DataError("field_conflict", "Sina financial field ID/title disagree")
                title = "归属于母公司所有者的净利润"
            value = number(item.get("item_value"))
            if not title or value is None:
                continue
            if title in conflicts:
                conflicts[title].append({"field": field, "value": value})
                continue
            if title in values and values[title] != value:
                conflicts[title] = [{"field": origins[title].get("field"), "value": values.pop(title)},
                                    {"field": field, "value": value}]
                continue
            values[title] = value
            origins[title] = {"title": item.get("item_title"), "field": field}
        if values:
            rows.append({"security": security["id"], "period": period, "published_at": None,
                         "statement": kind, "currency": "CNY", "unit": "元",
                         "scope": "consolidated", "basis": "balance" if kind == "fzb" else "ytd",
                         "source_id": sid, "values": values, "field_origins": origins,
                         "field_conflicts": conflicts,
                         "boundary": "API报告期不等于发布日期；合并口径沿用接口定义，重要数字需正式披露核验"})
    if not rows:
        raise DataError("empty_result", "No numeric financial rows returned")
    return rows


def statements(client, p, kind):
    data, meta = client.json(SINA, params={"paperCode": p["security"]["symbol"], "source": kind,
                                          "type": "0", "page": "1", "num": "28"})
    # Parse before registering: an empty/error response must not look like usable evidence.
    rows = parse_sina(data, kind, p["security"], "pending", p["as_of"])
    sid = source(p, "新浪财经 " + kind, meta.pop("url"), "financial_statement", **meta)
    for r in rows:
        r["source_id"] = sid
    p["statements"].extend(rows)


def hithink_statements(client, p, kind):
    key = os.environ.get("HITHINK_FINANCE_API_KEY", "").strip()
    if not key:
        raise DataError("not_configured", "Optional Hithink key is not configured")
    endpoint = {"lrb": "income-statements", "fzb": "balance-sheets", "llb": "cash-flow-statements"}[kind]
    data, meta = client.json(HITHINK + endpoint,
                             params={"thscode": p["security"]["id"], "period": "quarterly", "limit": "8"},
                             key=key)
    if data.get("code") != 0 or not isinstance(data.get("data"), dict):
        raise DataError("provider_rejected", "Hithink authentication, entitlement or business response failed")
    items = data["data"].get("item")
    if not isinstance(items, list) or len(items) > 20:
        raise DataError("parse_error", "Hithink financial list shape changed")
    rows, seen = [], set()
    for r in items:
        if r.get("thscode") != p["security"]["id"] or r.get("currency") != "CNY" or r.get("period") != "quarterly":
            raise DataError("identity_mismatch", "Hithink identity/currency/basis mismatch")
        def day(v):
            n = number(v)
            if n is None:
                raise DataError("missing_source_time", "Hithink financial dates missing")
            return datetime.fromtimestamp(n / 1000, CHINA).date().isoformat()
        period, published = day(r.get("period_end_ms")), day(r.get("report_date_ms"))
        if published < period or period in seen or r.get("fiscal_year") != int(period[:4]):
            raise DataError("invalid_period", "Hithink financial periods invalid/duplicated")
        seen.add(period)
        if period > p["as_of"] or published > p["as_of"]:
            continue
        suffix = period[5:]
        if suffix not in ("03-31", "06-30", "09-30", "12-31") or r.get("fiscal_period") != "Q" + str(int(period[5:7]) // 3):
            raise DataError("invalid_period", "Hithink fiscal quarter mismatch")
        values = {label: number(r[field]) for field, label in FIELDS.items()
                  if field in r and number(r[field]) is not None}
        if values:
            rows.append({"security": p["security"]["id"], "period": period, "published_at": published,
                         "statement": kind, "currency": "CNY", "unit": "元", "scope": "consolidated",
                         "basis": "balance" if kind == "fzb" else "ytd", "values": values})
    if not rows:
        raise DataError("empty_result", "Hithink returned no usable statements")
    sid = source(p, "同花顺金融数据 API " + kind, meta.pop("url"), "financial_statement", **meta)
    for r in rows:
        r["source_id"] = sid
    # Retain both sources for conflict detection, never silently overwrite.
    p["statements"].extend(rows)


def announcements(client, p):
    mapping, _ = client.json("https://www.cninfo.com.cn/new/data/szse_stock.json", ttl=86400)
    stocks = [s for s in mapping.get("stockList", []) if s.get("code") == p["security"]["code"]]
    if len(stocks) != 1 or not stocks[0].get("orgId"):
        raise DataError("identity_unresolved", "No unique CNInfo issuer mapping; do not guess orgId")
    org = stocks[0]["orgId"]
    data, meta = client.json("https://www.cninfo.com.cn/new/hisAnnouncement/query", form={
        "stock": p["security"]["code"] + "," + org, "tabName": "fulltext", "pageSize": "40",
        "pageNum": "1", "column": "", "category": "", "plate": "", "searchkey": "",
        "seDate": "", "sortName": "time", "sortType": "desc", "isHLtitle": "false"}, ttl=3600)
    items = data.get("announcements")
    if not isinstance(items, list):
        raise DataError("parse_error", "CNInfo announcement list missing")
    usable = []
    for item in items:
        if item.get("secCode") != p["security"]["code"]:
            continue
        stamp = number(item.get("announcementTime"))
        if stamp is None:
            continue
        day = datetime.fromtimestamp(stamp / 1000, CHINA).date().isoformat()
        path = str(item.get("adjunctUrl", ""))
        if day > p["as_of"] or not re.fullmatch(r"(?:finalpage/)?[\w/.-]+\.PDF", path, re.I) or ".." in path:
            continue
        usable.append({"title": plain(item.get("announcementTitle", "")), "published_at": day,
                       "url": "https://static.cninfo.com.cn/" + path.lstrip("/")})
    if not usable:
        raise DataError("empty_result", "No identity/date-verified recent announcements")
    for item in usable:
        sid = source(p, item["title"], item["url"], "disclosure_index",
                     published_at=item["published_at"], stale=meta["stale"], fetched_at=meta["fetched_at"])
        p["documents"].append({"source_id": sid, "status": "index_only", "security": p["security"]["id"],
                               "published_at": item["published_at"], "title": item["title"], "pages": []})


def announcement_backup(client, p):
    data, meta = client.json("https://np-anotice-stock.eastmoney.com/api/security/ann", params={
        "sr": "-1", "page_size": "40", "page_index": "1", "ann_type": "A",
        "client_source": "web", "stock_list": p["security"]["code"]}, ttl=3600)
    items = (data.get("data") or {}).get("list")
    if not isinstance(items, list):
        raise DataError("parse_error", "Eastmoney announcement list missing")
    count = 0
    for item in items:
        if not any(c.get("stock_code") == p["security"]["code"] for c in item.get("codes", [])):
            continue
        day = str(item.get("notice_date", ""))[:10]
        try:
            checked_date(day)
        except (DataError, ValueError):
            continue
        aid = str(item.get("art_code", ""))
        if day > p["as_of"] or not re.fullmatch(r"[A-Za-z0-9]+", aid):
            continue
        title = plain(item.get("title", ""))
        sid = source(p, title, f"https://pdf.dfcfw.com/pdf/H2_{aid}_1.pdf", "disclosure_index",
                     published_at=day, stale=meta["stale"], fetched_at=meta["fetched_at"])
        p["documents"].append({"source_id": sid, "status": "index_only", "security": p["security"]["id"],
                               "published_at": day, "title": title, "pages": []})
        count += 1
    if not count:
        raise DataError("empty_result", "No identity-verified fallback announcements")


def kline(client, p):
    if p["security"]["exchange"] == "BJ":
        raise DataError("unsupported_coverage", "Bundled Tencent historical K-line excludes Beijing listings")
    from datetime import date, timedelta
    start = (date.fromisoformat(p["as_of"]) - timedelta(days=550)).isoformat()
    param = f'{p["security"]["symbol"]},day,{start},{p["as_of"]},640,qfq'
    errors = []
    for host in ("https://web.ifzq.gtimg.cn", "https://ifzq.gtimg.cn"):
        try:
            data, meta = client.json(host + "/appstock/app/fqkline/get", params={"param": param}, ttl=3600)
            node = (data.get("data") or {}).get(p["security"]["symbol"])
            if not isinstance(node, dict):
                raise DataError("parse_error", "K-line symbol missing")
            raw = node.get("qfqday", node.get("day"))
            if not isinstance(raw, list) or not raw:
                raise DataError("empty_result", "Adjusted K-line not returned; do not relabel raw series")
            rows, seen = [], set()
            for v in raw:
                day = checked_date(v[0])
                nums = [number(x) for x in v[1:6]]
                if len(nums) != 5 or any(n is None for n in nums) or min(nums[:4]) <= 0 or nums[4] < 0:
                    raise DataError("invalid_kline", "Invalid OHLC/volume; additive adjusted prices may be nonpositive")
                if day in seen or not start <= day <= p["as_of"]:
                    raise DataError("invalid_kline", "Duplicate/out-of-range K-line date")
                seen.add(day)
                o, c, h, low, vol = nums
                if h < max(o, c, low) or low > min(o, c, h):
                    raise DataError("invalid_kline", "OHLC ordering invalid")
                rows.append({"date": day, "open": o, "close": c, "high": h, "low": low,
                             "volume_shares": vol if p["security"]["code"].startswith(("688", "689")) else vol * 100})
            sid = source(p, "腾讯日线（来源前复权）", meta.pop("url"), "kline", **meta)
            p["observations"].append({"kind": "kline", "source_id": sid, "data": sorted(rows, key=lambda r: r["date"]),
                                      "adjustment": "Tencent additive qfq; not total return", "amount": None})
            return
        except (DataError, KeyError, TypeError, ValueError, IndexError) as e:
            errors.append(getattr(e, "code", "parse_error"))
    raise DataError(errors[-1], "Both bounded K-line attempts failed")


def collect(client, p, hithink=False, include_kline=True, include_announcements=True):
    def run(label, fn):
        try:
            fn()
            return True
        except DataError as e:
            p["gaps"].append({"module": label, "reason": e.code, "detail": str(e)})
            return False
        except (ValueError, TypeError, KeyError, IndexError, OverflowError):
            p["gaps"].append({"module": label, "reason": "parse_error", "detail": "Provider schema changed"})
            return False
    run("quote", lambda: quote(client, p))
    for kind in ("lrb", "fzb", "llb"):
        success = run(kind, lambda k=kind: statements(client, p, k))
        core = {"lrb": ("营业收入", "归属于母公司所有者的净利润"),
                "fzb": ("资产总计", "负债合计"), "llb": ("经营活动产生的现金流量净额",)}[kind]
        available = [r for r in p["statements"] if r["statement"] == kind]
        latest = max((r["period"] for r in available), default="")
        missing_core = not any(all(k in r["values"] for k in core) for r in available if r["period"] == latest)
        if hithink and (not success or missing_core):
            run(kind + "_hithink", lambda k=kind: hithink_statements(client, p, k))
    if include_kline:
        run("kline", lambda: kline(client, p))
    if include_announcements and not run("disclosures", lambda: announcements(client, p)):
        run("disclosures_backup", lambda: announcement_backup(client, p))
    if p["as_of"] < datetime.now(CHINA).date().isoformat():
        # Unknown release dates cannot establish historical point-in-time availability.
        excluded = [r for r in p["statements"] if not r.get("published_at")]
        p["statements"] = [r for r in p["statements"] if r.get("published_at")]
        if excluded:
            p["gaps"].append({"module": "financials", "reason": "publication_date_unknown",
                              "detail": "Undated API statements excluded from historical-cutoff analysis"})
    p["collection"] = {"http_calls": client.calls, "cache_only": client.offline,
                       "coverage": "Selected company research endpoints only; not all upstream endpoints"}
    conflicts = sum(len(r.get("field_conflicts", {})) for r in p["statements"])
    if conflicts:
        p["gaps"].append({"module": "financials", "reason": "ambiguous_source_fields",
                          "detail": f"{conflicts} source fields have duplicate labels with different values; only those fields excluded"})
    return p
