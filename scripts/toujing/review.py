"""Mechanical report checks. Citation presence does not prove semantic support."""
import re
from .core import DataError, digest, number, validate_packet


def review(p, report, workpaper=None):
    validate_packet(p)
    if report.get("security") != p["security"]["id"] or report.get("as_of") != p["as_of"]:
        raise DataError("identity_mismatch", "Report security/cutoff does not match evidence")
    issues = []
    sources = {s["id"]: s for s in p["sources"]}
    calculations = {}
    if workpaper:
        if workpaper.get("packet_hash") != digest(p):
            raise DataError("stale_workpaper", "Workpaper belongs to another evidence revision")
        from .analysis import financials
        expected = financials(p, workpaper.get("industry", "unknown"))
        if digest(expected) != digest(workpaper):
            raise DataError("modified_workpaper", "Recompute workpaper; calculation records differ from source inputs")
        calculations = {c["id"]: c for c in workpaper["calculations"]}
    def issue(path, reason, detail, severity="warning"):
        issues.append({"path": path, "reason": reason, "detail": detail, "severity": severity})
    if report.get("packet_hash") != digest(p):
        issue("packet_hash", "stale_evidence", "Report must bind exact current packet hash", "error")
    if not report.get("summary", "").strip():
        issue("summary", "missing_judgment", "Provide a company-specific conclusion using available evidence")
    for sid in re.findall(r"\[(S\d+)\]", report.get("summary", "")):
        if sid not in sources:
            issue("summary", "unknown_source", "Summary refers to an unknown source", "error")
    sections = report.get("sections")
    if not isinstance(sections, list) or not sections:
        raise DataError("invalid_report", "Report requires non-empty sections")
    for i, section in enumerate(sections):
        path = f"sections[{i}]"
        if not section.get("analysis", "").strip():
            issue(path + ".analysis", "missing_analysis", "Explain implication and conditions, not just data availability")
        if not section.get("conclusion", "").strip():
            issue(path + ".conclusion", "missing_judgment", "Answer this module's question directly")
        if not section.get("facts"):
            issue(path + ".facts", "no_facts", "Module has no explicitly sourced facts")
        section_sids = set()
        for j, fact in enumerate(section.get("facts", [])):
            fpath = path + f".facts[{j}]"
            text = fact.get("text", "")
            ids = fact.get("source_ids", [])
            section_sids.update(ids)
            if not ids:
                issue(fpath, "missing_citation", "Fact must cite source IDs", "error")
            for sid in ids:
                if sid not in sources:
                    issue(fpath, "unknown_source", "Source ID is not in this packet", "error")
                elif sources[sid].get("stale"):
                    issue(fpath, "stale_source", "Old cached evidence must be dated and qualified")
            cid = fact.get("calculation_id")
            if cid:
                calc = calculations.get(cid)
                if not calc:
                    issue(fpath, "unknown_calculation", "Calculation ID absent from matching workpaper", "error")
                elif (number(fact.get("value")) is None or
                      abs(number(fact["value"]) - calc["value"]) > max(1e-8, abs(calc["value"]) * 1e-6)
                      or fact.get("unit") != calc["unit"] or fact.get("period") != calc["period"]):
                    issue(fpath, "calculation_mismatch", "Value, unit or period differs from workpaper", "error")
            for sid in re.findall(r"\[(S\d+)\]", text):
                if sid not in ids:
                    issue(fpath, "unbound_inline_citation", "Inline citation not declared in fact source_ids", "error")
        # Analysis can infer from facts but must preserve the evidence boundary.
        for field in ("analysis", "conclusion", "counterevidence", "watch"):
            text = section.get(field, "")
            if not isinstance(text, str):
                raise DataError("invalid_report", "Narrative fields must be strings")
            if re.search(r"\[S\d+\]", text):
                for sid in re.findall(r"\[(S\d+)\]", text):
                    if sid not in sources:
                        issue(path + "." + field, "unknown_source", "Narrative uses nonexistent source", "error")
            if re.search(r"(?:占比|收入|利润|增长|为)[^。\n]{0,12}[?？]$", text.strip()):
                issue(path + "." + field, "incomplete_sentence", "Unfinished numerical assertion")
        if re.search(r"目标价|低估|高估|买入|卖出", section.get("conclusion", "")):
            issue(path + ".conclusion", "valuation_review", "Manually check valuation inputs, peer comparability and assumptions")
    return {"schema_version": 1, "packet_hash": digest(p), "report_hash": digest(report),
            "status": "mechanical_errors" if any(i["severity"] == "error" for i in issues) else "semantic_review_required",
            "issues": issues, "boundary": "Does not verify source truth, semantic support, omitted facts or model reasoning"}


def render(p, report, workpaper=None):
    result = review(p, report, workpaper)
    if any(i["severity"] == "error" for i in result["issues"]):
        raise DataError("report_validation_failed", "Fix mechanical errors before rendering")
    def text(v):
        # Disable embedded HTML/images and executable/remote Markdown destinations.
        v = str(v).replace("<", "&lt;").replace(">", "&gt;")
        v = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", v)
        for s in p["sources"]:
            v = v.replace("[" + s["id"] + "]", f'[{s["id"]}]({s["url"]})')
        return v
    title = p["security"].get("name", p["security"]["id"])
    lines = ["# " + text(title) + " · 基本面研究", "",
             "> AI 辅助研究，可能存在错误；不构成投资建议。", "",
             "研究截止：" + p["as_of"], "", "## 核心结论", "", text(report["summary"]), ""]
    for section in report["sections"]:
        lines.extend(["## " + text(section["title"]), ""])
        for f in section.get("facts", []):
            refs = " ".join(f'[{sid}]({next(s["url"] for s in p["sources"] if s["id"] == sid)})'
                            for sid in f.get("source_ids", []))
            lines.extend(["- " + text(f["text"]) + " " + refs])
        lines.extend(["", text(section["analysis"]), "", "**判断：** " + text(section["conclusion"]), ""])
        for key, label in (("counterevidence", "反证与风险"), ("watch", "跟踪变量")):
            if section.get(key):
                lines.extend(["**" + label + "：** " + text(section[key]), ""])
    lines.extend(["## 来源", ""])
    for s in p["sources"]:
        lines.append(f'- [{s["id"]} · {text(s["title"])}]({s["url"]})；发布 {s.get("published_at") or "未核验"}；获取 {s["fetched_at"]}'
                     + ("；旧缓存" if s.get("stale") else ""))
    lines.extend(["", "## 资料缺口与适用边界", ""])
    gaps = list(p["gaps"]) + list((workpaper or {}).get("issues", []))
    for sec in report["sections"]:
        gaps.extend({"module": sec["title"], "detail": g} for g in sec.get("data_gaps", []))
    unique = set()
    for g in gaps:
        desc = str(g.get("detail", g.get("reason", "")))
        key = (g.get("module"), desc)
        if key not in unique:
            unique.add(key)
            lines.append("- " + text(g.get("module", "")) + "：" + text(desc))
    if not unique:
        lines.append("本轮未列出具体缺口，不代表资料穷尽或全部事实已独立核实。")
    lines.extend(["", "机械校验不替代原文核验和人工判断；完整审阅记录保留在 review.json。", ""])
    return "\n".join(lines)
