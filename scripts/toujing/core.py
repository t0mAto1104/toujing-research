"""Evidence contracts and local I/O. Adapted from Toujing V3.12.2 concepts."""
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

CHINA = timezone(timedelta(hours=8))


class DataError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def checked_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise DataError("invalid_date", "Expected YYYY-MM-DD")
    date.fromisoformat(value)
    return value


def identity(value):
    """A-share companies only; explicit exchange prevents index/stock confusion."""
    value = str(value).strip().upper()
    m = re.fullmatch(r"(?:(SH|SZ|BJ))?(\d{6})(?:\.(SH|SZ|BJ|XSHG|XSHE))?", value)
    if not m:
        raise DataError("invalid_security", "Use an A-share company code, e.g. 600519.SH")
    pre, code, post = m.groups()
    post = {"XSHG": "SH", "XSHE": "SZ"}.get(post, post)
    market = "SH" if code.startswith(("600", "601", "603", "605", "688", "689")) else (
        "SZ" if code.startswith(("000", "001", "002", "003", "300", "301")) else (
            "BJ" if code.startswith(("4", "8", "92")) else None))
    if not market or any(p and p != market for p in (pre, post)):
        raise DataError("identity_mismatch", "Unsupported company code or conflicting exchange")
    if market == "BJ" and code.startswith(("4", "8")):
        raise DataError("legacy_security", "Verify current Beijing listing code; legacy codes may return frozen quotes")
    return {"code": code, "exchange": market, "symbol": market.lower() + code,
            "id": code + "." + market, "asset": "A-share company"}


def number(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", "").replace("，", "")
        if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value):
            return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError, OverflowError):
        return None


def amount(value, unit="元"):
    units = {"元": 1, "万元": 10000, "亿元": 100000000, "CNY": 1, "元/股": 1}
    if unit not in units:
        raise DataError("unknown_unit", "Unknown financial unit; do not guess")
    n = number(value)
    return None if n is None else n * units[unit]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     allow_nan=False).encode()).hexdigest()


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 40 * 1024 * 1024:
        raise DataError("input_too_large", "JSON input exceeds 40 MB")
    return json.loads(path.read_text(encoding="utf-8"),
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise DataError("unsafe_output", "Refusing symlink output")
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".toujing-", delete=False) as f:
        temporary = f.name
        try:
            os.chmod(temporary, 0o600)
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write("\n")
        except BaseException:
            os.unlink(temporary)
            raise
    os.replace(temporary, path)


def clean_url(value):
    """Reference metadata only. This function does not grant fetch permission."""
    try:
        if not isinstance(value, str) or re.search(r"[\s\x00-\x1f\x7f<>\[\]()\\]", value):
            return None
        u = urlsplit(value)
        if (u.scheme != "https" or not u.hostname or u.username or u.password
                or u.fragment or u.port not in (None, 443)):
            return None
        if any(re.search(r"key|token|secret|password|authorization|signature|credential", k, re.I)
               for k, _ in parse_qsl(u.query)):
            return None
        import ipaddress
        if u.hostname == "localhost" or u.hostname.endswith((".localhost", ".local", ".internal")):
            return None
        try:
            if not ipaddress.ip_address(u.hostname).is_global:
                return None
        except ValueError:
            pass
        return value
    except (ValueError, TypeError):
        return None


def packet(security, as_of):
    checked_date(as_of)
    if as_of > datetime.now(CHINA).date().isoformat():
        raise DataError("future_date", "Research cutoff cannot be in the future")
    return {"schema_version": 1, "security": identity(security), "as_of": as_of,
            "created_at": now(), "sources": [], "observations": [], "documents": [],
            "statements": [], "gaps": [], "untrusted_content": True}


def source(p, title, url, kind, **extra):
    if not clean_url(url):
        raise DataError("unsafe_url", "Source must be HTTPS without credentials")
    existing = next((s for s in p["sources"] if s["url"] == url), None)
    if existing:
        return existing["id"]
    sid = "S" + str(len(p["sources"]) + 1)
    p["sources"].append({"id": sid, "title": title, "url": url, "kind": kind,
                         "fetched_at": now(), "trust": "untrusted_evidence", **extra})
    return sid


def validate_packet(p):
    expected = identity(p["security"]["id"])
    if p.get("schema_version") != 1 or any(p["security"].get(k) != v for k, v in expected.items()):
        raise DataError("invalid_packet", "Packet schema or security identity mismatch")
    checked_date(p["as_of"])
    if p["as_of"] > datetime.now(CHINA).date().isoformat():
        raise DataError("future_date", "Research cutoff cannot be in the future")
    ids = [s["id"] for s in p["sources"]]
    if len(ids) != len(set(ids)) or any(not clean_url(s["url"]) for s in p["sources"]):
        raise DataError("invalid_sources", "Duplicate source IDs or unsafe source metadata")
    for r in p["statements"]:
        if r["security"] != p["security"]["id"] or r["source_id"] not in ids:
            raise DataError("identity_mismatch", "Statement identity/source mismatch")
        checked_date(r["period"])
        if r["period"] > p["as_of"] or r.get("currency") != "CNY":
            raise DataError("invalid_period", "Statement currency or cutoff mismatch")
        if r.get("published_at"):
            checked_date(r["published_at"])
            if r["published_at"] < r["period"] or r["published_at"] > p["as_of"]:
                raise DataError("invalid_period", "Publication date outside knowledge cutoff")
        elif p["as_of"] < datetime.now(CHINA).date().isoformat():
            raise DataError("publication_date_unknown", "Historical analysis requires known publication dates")
        if r["statement"] not in ("lrb", "fzb", "llb"):
            raise DataError("invalid_statement", "Unknown statement kind")
        if r.get("scope") not in ("consolidated", "parent", "unknown"):
            raise DataError("unknown_scope", "Statement scope required")
        if r.get("basis") != ("balance" if r["statement"] == "fzb" else "ytd"):
            raise DataError("unknown_basis", "Only explicit balance/YTD statements supported")
        for v in r["values"].values():
            if v is not None and number(v) is None:
                raise DataError("invalid_number", "Non-numeric statement value")
    return p
