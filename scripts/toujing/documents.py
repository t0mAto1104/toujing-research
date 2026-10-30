"""Read-only evidence ingestion. Extracted text remains untrusted data."""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from .core import DataError, checked_date, clean_url, digest, source, validate_packet
from .http import PDF_HOSTS


def pdf_worker(path):
    # OS process limits are defense in depth, not a security sandbox.
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (40, 40))
        resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
    except (ImportError, ValueError, OSError):
        pass
    from pypdf import PdfReader
    reader = PdfReader(path, strict=True)
    if reader.is_encrypted:
        raise DataError("encrypted_pdf", "Encrypted PDF requires a user-decrypted copy")
    total = len(reader.pages)
    if total > 1000:
        raise DataError("too_many_pages", "PDF exceeds 1000 pages")
    pages, chars = [], 0
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        chars += len(text)
        if chars > 4_000_000:
            raise DataError("text_too_large", "PDF extraction exceeds text budget")
        pages.append({"page": i + 1, "text": text})
    print(json.dumps({"total_pages": total, "pages": pages}, ensure_ascii=False))


def extract_file(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 25 * 1024 * 1024:
        raise DataError("input_too_large", "Evidence file must be at most 25 MB")
    if path.suffix.lower() == ".pdf":
        try:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "toujing_cli.py"),
                                     "_pdf-worker", str(path)], capture_output=True, text=True, timeout=55)
        except subprocess.TimeoutExpired:
            raise DataError("pdf_timeout", "PDF extraction timed out; use selected pages or OCR") from None
        if result.returncode:
            raise DataError("pdf_read_failed", "PDF unreadable, encrypted, over resource limits, or pypdf not installed")
        data = json.loads(result.stdout)
    elif path.suffix.lower() in (".txt", ".md"):
        data = {"total_pages": None, "pages": [{"page": None, "text": path.read_text(encoding="utf-8")} ]}
    else:
        raise DataError("unsupported_file", "Use PDF or UTF-8 TXT/Markdown; no executable/Office input")
    text_pages = sum(len(r["text"].strip()) >= 20 for r in data["pages"])
    data["status"] = "text_extracted" if text_pages == len(data["pages"]) and text_pages else "partial_or_needs_ocr"
    data["text_pages"] = text_pages
    data["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    data["boundary"] = "Text extraction is not visual/table verification or proof of complete reading; inspect material pages"
    return data


def ingest(p, path, title, url, published_at, kind="disclosure"):
    validate_packet(p)
    checked_date(published_at)
    if published_at > p["as_of"] or not clean_url(url):
        raise DataError("invalid_source", "Source date exceeds cutoff or URL is unsafe")
    data = extract_file(path)
    text = "\n".join(x["text"] for x in data["pages"])
    code = p["security"]["code"]
    # Presence is only a weak signal: append an explicit review requirement.
    observed = bool(re.search(r"(?<!\d)" + re.escape(code) + r"(?!\d)", text))
    sid = source(p, title, url, kind, published_at=published_at,
                 identity_status="code_observed_unverified" if observed else "unverified")
    p["documents"].append({"source_id": sid, "security": p["security"]["id"], "title": title,
                           "published_at": published_at, **data})
    p["gaps"].append({"module": "disclosures", "reason": "identity_review_required", "source_id": sid,
                      "detail": "Verify issuer, cover, reporting period, consolidated scope and original page layout"})
    return p


def download_document(client, p, sid):
    s = next((s for s in p["sources"] if s["id"] == sid), None)
    if not s or s["kind"] != "disclosure_index" or urlsplit(s["url"]).hostname not in PDF_HOSTS:
        raise DataError("blocked_document", "Fetch only a disclosure selected from this packet's fixed-source index")
    raw, _ = client.fetch(s["url"], binary=True)
    with tempfile.TemporaryDirectory(prefix="toujing-pdf-") as folder:
        path = Path(folder) / "evidence.pdf"
        path.write_bytes(raw)
        data = extract_file(path)
    p["documents"] = [d for d in p["documents"] if d["source_id"] != sid]
    p["documents"].append({"source_id": sid, "security": p["security"]["id"],
                           "title": s["title"], "published_at": s.get("published_at"), **data})
    s["identity_status"] = "unverified"
    p["gaps"].append({"module": "disclosures", "reason": "identity_review_required", "source_id": sid,
                      "detail": "Downloaded text still requires issuer/report scope and material page verification"})
    return p


def import_evidence(p, path):
    """Import only an explicit user/agent-created manifest, never auto-execute URLs."""
    from .core import read_json, identity
    data = read_json(path)
    if identity(data["security"])["id"] != p["security"]["id"]:
        raise DataError("identity_mismatch", "Imported evidence belongs to a different security")
    for e in data.get("items", []):
        day = checked_date(e["published_at"])
        if day > p["as_of"]:
            raise DataError("after_cutoff", "Imported evidence exceeds cutoff")
        if e.get("kind") not in ("company", "macro", "industry", "news", "disclosure"):
            raise DataError("invalid_source", "Unsupported evidence kind")
        text = e.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 60000:
            raise DataError("invalid_evidence", "Imported evidence text missing/too large")
        sid = source(p, e["title"], e["url"], e["kind"], published_at=day,
                     identity_status="unverified", read_status="user_or_agent_supplied_excerpt")
        p["documents"].append({"source_id": sid, "security": p["security"]["id"], "title": e["title"],
                               "published_at": day, "status": "excerpt_only", "total_pages": None,
                               "pages": [{"page": e.get("page"), "text": text}], "sha256": digest(text)})
    return p
