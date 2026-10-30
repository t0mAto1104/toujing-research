"""Bounded HTTPS transport: fixed destinations, no redirects, no credential logs."""
import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from .core import DataError, now, read_json, write_json

HOSTS = {"qt.gtimg.cn", "web.ifzq.gtimg.cn", "ifzq.gtimg.cn", "proxy.finance.qq.com",
         "quotes.sina.cn", "www.cninfo.com.cn", "static.cninfo.com.cn",
         "np-anotice-stock.eastmoney.com", "pdf.dfcfw.com", "fuyao.aicubes.cn"}
PDF_HOSTS = {"static.cninfo.com.cn", "pdf.dfcfw.com"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, cache, timeout=12, budget=120, offline=False, refresh=False):
        self.cache = Path(cache)
        self.timeout = timeout
        self.deadline = time.monotonic() + budget
        self.offline, self.refresh = offline, refresh
        # Do not inherit proxy credentials or install cookie jars/auth handlers.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.last_request = 0
        self.calls = 0

    def fetch(self, url, params=None, form=None, ttl=21600, key=None, binary=False):
        u = urlsplit(url)
        if (u.scheme != "https" or u.hostname not in HOSTS or u.username or u.password
                or u.port not in (None, 443) or u.fragment):
            raise DataError("blocked_destination", "Destination not allowlisted")
        if key and u.hostname != "fuyao.aicubes.cn":
            raise DataError("blocked_credential", "Credentials restricted to provider origin")
        if params:
            url += "?" + urlencode(params)
        body = urlencode(form).encode() if form is not None else None
        # Authenticated data never enters the shared public HTTP cache.
        cache_id = hashlib.sha256(url.encode() + (body or b"")).hexdigest()
        cache_path = self.cache / (cache_id + ".json")
        cached = None
        if not key and not binary and cache_path.exists():
            try:
                cached = read_json(cache_path)
                if cached["request_hash"] != cache_id:
                    cached = None
                else:
                    age = (datetime.now(timezone.utc) - datetime.fromisoformat(cached["fetched_at"])).total_seconds()
                    if age < 0 or age > 7 * 86400:
                        cached = None
                    elif self.offline or (age <= ttl and not self.refresh):
                        return cached["text"], {"fetched_at": cached["fetched_at"], "cache": True,
                                                "stale": age > ttl, "url": url}
            except (ValueError, KeyError, OSError):
                cached = None
        if self.offline:
            raise DataError("offline_missing", "No usable local cache")
        remaining = self.deadline - time.monotonic()
        if remaining <= 0 or self.calls >= 24:
            raise DataError("budget_exhausted", "Public-data request budget exhausted")
        wait = max(0, 1.05 - (time.monotonic() - self.last_request))
        if wait >= remaining:
            raise DataError("budget_exhausted", "Public-data request budget exhausted")
        time.sleep(wait)
        headers = {"User-Agent": "ToujingResearch/0.1 (+https://github.com/t0mAto1104)",
                   "Accept-Encoding": "identity", "Accept": "application/json, text/plain, */*"}
        if form is not None:
            headers.update({"Content-Type": "application/x-www-form-urlencoded",
                            "Referer": "https://www.cninfo.com.cn/"})
        if key:
            headers["X-api-key"] = key
        req = urllib.request.Request(url, data=body, headers=headers)
        self.calls += 1
        self.last_request = time.monotonic()
        try:
            with self.opener.open(req, timeout=min(self.timeout, self.deadline - time.monotonic())) as response:
                limit = 25 * 1024 * 1024 if binary else 12 * 1024 * 1024
                chunks, size = [], 0
                while True:
                    if time.monotonic() > self.deadline:
                        raise DataError("timeout", "HTTP body deadline exceeded")
                    chunk = response.read(min(65536, limit + 1 - size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > limit:
                        raise DataError("response_too_large", "HTTP response exceeds size limit")
                raw = b"".join(chunks)
                if binary:
                    if not raw.startswith(b"%PDF-"):
                        raise DataError("not_pdf", "Response is not a PDF")
                    return raw, {"fetched_at": now(), "url": url, "cache": False, "stale": False}
                encoding = "gb18030" if u.hostname == "qt.gtimg.cn" else "utf-8"
                text = raw.decode(encoding)
                stamp = now()
                if not key:
                    write_json(cache_path, {"request_hash": cache_id, "fetched_at": stamp, "text": text})
                return text, {"fetched_at": stamp, "url": url, "cache": False, "stale": False}
        except urllib.error.HTTPError as e:
            code = "rate_limited" if e.code == 429 else "access_denied" if e.code in (401, 403) else "http_error"
            if 300 <= e.code < 400:
                code = "redirect_blocked"
            e.close()
        except urllib.error.URLError as e:
            code = "tls_certificate_error" if isinstance(e.reason, ssl.SSLCertVerificationError) else "connection_failed"
        except (TimeoutError, OSError):
            code = "connection_failed"
        except UnicodeError:
            code = "parse_error"
        if cached and not key and not binary:
            return cached["text"], {"fetched_at": cached["fetched_at"], "cache": True,
                                    "stale": True, "refresh_error": code, "url": url}
        raise DataError(code, "Upstream request failed; no provider response or credentials logged")

    def json(self, url, **kwargs):
        text, metadata = self.fetch(url, **kwargs)
        try:
            return json.loads(text), metadata
        except (json.JSONDecodeError, TypeError):
            raise DataError("parse_error", "Upstream did not return JSON") from None


def default_cache():
    return Path(os.environ.get("TOUJING_CACHE_DIR", Path.home() / ".cache" / "toujing-research"))
