#!/usr/bin/env python3
"""Toujing CLI. JSON outputs; no model calls, background work or secret setup."""
import argparse
import importlib.util
import json
import os
import platform
import sys
import ssl
from datetime import datetime
from pathlib import Path

from toujing import VERSION
from toujing.core import CHINA, DataError, digest, packet, read_json, validate_packet, write_json
from toujing.http import Client, default_cache
from toujing.providers import collect
from toujing.analysis import financials
from toujing.review import review, render
from toujing.documents import ingest, import_evidence, download_document, pdf_worker


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--version", action="version", version=VERSION)
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Local environment checks only; never prints credentials")
    c = sub.add_parser("collect", help="Bounded public-data collection")
    c.add_argument("security")
    c.add_argument("--as-of", default=datetime.now(CHINA).date().isoformat())
    c.add_argument("--out", required=True)
    c.add_argument("--cache-dir", default=str(default_cache()))
    c.add_argument("--offline", action="store_true")
    c.add_argument("--refresh", action="store_true")
    c.add_argument("--hithink", action="store_true", help="Explicitly enable user's own optional credential")
    c.add_argument("--no-kline", action="store_true")
    c.add_argument("--no-announcements", action="store_true")
    c.add_argument("--budget-seconds", type=int, choices=range(10, 601), default=120, metavar="10..600")
    for command in ("financials", "plan", "ingest", "import-evidence", "read-disclosure", "review", "render"):
        c = sub.add_parser(command)
        c.add_argument("packet")
        c.add_argument("--out", required=True)
        if command in ("financials", "plan"):
            c.add_argument("--industry", choices=("unknown", "industrial", "bank", "broker", "insurance"), default="unknown")
        if command == "ingest":
            c.add_argument("file")
            for flag in ("title", "url", "published-at"):
                c.add_argument("--" + flag, required=True)
        if command == "import-evidence":
            c.add_argument("manifest")
        if command == "read-disclosure":
            c.add_argument("source_id")
            c.add_argument("--cache-dir", default=str(default_cache()))
        if command in ("review", "render"):
            c.add_argument("report")
            c.add_argument("--workpaper")
    c = sub.add_parser("_pdf-worker", help=argparse.SUPPRESS)
    c.add_argument("file")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == "_pdf-worker":
        pdf_worker(args.file)
        return 0
    if args.command == "doctor":
        print(json.dumps({"version": VERSION, "python": platform.python_version(),
                          "supported_python": sys.version_info >= (3, 10),
                          "trusted_ca_certificates_available": bool(ssl.create_default_context().get_ca_certs()),
                          "pdf_reader_available": importlib.util.find_spec("pypdf") is not None,
                          "hithink_key_present": bool(os.environ.get("HITHINK_FINANCE_API_KEY")),
                          "network_tested": False, "extra_model_key_required": False}, indent=2))
        return 0
    if args.command == "collect":
        p = packet(args.security, args.as_of)
        client = Client(args.cache_dir, budget=args.budget_seconds, offline=args.offline, refresh=args.refresh)
        result = collect(client, p, args.hithink, not args.no_kline, not args.no_announcements)
        validate_packet(result)
        write_json(args.out, result)
        usable = bool(result["observations"] or result["statements"] or result["documents"])
        print(json.dumps({"ok": usable, "partial": bool(result["gaps"]), "out": args.out,
                          "sources": len(result["sources"]), "gaps": len(result["gaps"])}))
        return 0 if usable else 2
    p = validate_packet(read_json(args.packet))
    if args.command == "financials":
        result = financials(p, args.industry)
    elif args.command == "plan":
        result = {"schema_version": 1, "security": p["security"]["id"], "packet_hash": digest(p),
                  "industry": args.industry, "roles": [
                      {"id": "business", "modules": ["公司与业务", "同业比较"]},
                      {"id": "financial", "modules": ["财务质量"]},
                      {"id": "industry", "modules": ["行业与政策"]},
                      {"id": "valuation", "modules": ["估值与情景", "风险与跟踪"]}],
                  "synthesis": "核心结论", "max_parallel_roles": 2,
                  "execution": "Host agent executes roles; tools do not invoke models or spawn agents",
                  "supplement_rounds": 1, "supplement_search_calls": 2,
                  "resume": "Reuse files only when packet_hash and plan/method version match; inspect stale inputs"}
    elif args.command == "ingest":
        result = ingest(p, args.file, args.title, args.url, args.published_at)
    elif args.command == "import-evidence":
        result = import_evidence(p, args.manifest)
    elif args.command == "read-disclosure":
        result = download_document(Client(args.cache_dir), p, args.source_id)
    else:
        report = read_json(args.report)
        work = read_json(args.workpaper) if args.workpaper else None
        result = review(p, report, work) if args.command == "review" else render(p, report, work)
    if isinstance(result, str):
        # Reuse atomic, restrictive JSON writer for temp handling, then emit text atomically.
        import tempfile
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.is_symlink():
            raise DataError("unsafe_output", "Refusing symlink output")
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=out.parent, delete=False) as f:
            os.chmod(f.name, 0o600)
            f.write(result)
        os.replace(f.name, out)
    else:
        write_json(args.out, result)
    print(json.dumps({"ok": True, "out": args.out,
                      "status": result.get("status") if isinstance(result, dict) else "rendered"}))
    if args.command == "review" and result["status"] == "mechanical_errors":
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DataError, ValueError, KeyError, TypeError, OSError) as error:
        # Do not echo provider bodies, input paths, private text or credential values.
        code = getattr(error, "code", "invalid_input_or_io")
        print(json.dumps({"ok": False, "error": code,
                          "detail": "Check input contract, local permissions and documented failure boundaries"}), file=sys.stderr)
        raise SystemExit(1)
