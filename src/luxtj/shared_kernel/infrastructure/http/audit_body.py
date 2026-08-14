"""Compress / prettify booking API audit request & response bodies.

Storage keeps minified JSON/XML; admin downloads re-indent for readability.
"""

from __future__ import annotations

import json
import re
from typing import Any

from lxml import etree

_BETWEEN_TAGS_WS = re.compile(r">\s+<")


def _sniff_format(body: str, hint: str | None = None) -> str:
    stored = (hint or "").strip().lower()
    sample = body.lstrip("\ufeff \t\r\n")
    if not sample:
        if stored in {"json", "xml", "soap"}:
            return "xml" if stored == "soap" else stored
        return "text"

    if stored in {"xml", "soap"}:
        return "xml"
    if stored == "json" and sample[0] in "{[":
        return "json"

    if sample[0] in "{[":
        return "json"
    if sample.startswith("<") or sample.lower().startswith("<?xml"):
        return "xml"
    lower = sample[:500].lower()
    if "<soap" in lower or ":envelope" in lower:
        return "xml"
    if stored == "json":
        return "json"
    return "text"


def _compress_json(text: str) -> str:
    parsed: Any = json.loads(text)
    return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))


def _prettify_json(text: str) -> str:
    parsed: Any = json.loads(text)
    return json.dumps(parsed, ensure_ascii=False, indent=2) + "\n"


def _xml_root(text: str) -> etree._Element:
    parser = etree.XMLParser(remove_blank_text=True, recover=True, huge_tree=True)
    root = etree.fromstring(text.encode("utf-8"), parser=parser)
    if root is None:
        raise ValueError("empty XML")
    return root


def _compress_xml(text: str) -> str:
    try:
        root = _xml_root(text)
        out = etree.tostring(root, encoding="unicode", xml_declaration=False)
        return out.strip()
    except Exception:
        # Fallback: collapse whitespace between tags only.
        return _BETWEEN_TAGS_WS.sub("><", text.strip())


def _prettify_xml(text: str) -> str:
    try:
        root = _xml_root(text)
        out = etree.tostring(
            root,
            encoding="unicode",
            pretty_print=True,
            xml_declaration=False,
        )
        return out if out.endswith("\n") else out + "\n"
    except Exception:
        return text


def compress_audit_body(
    body: str | None,
    *,
    request_format: str | None = None,
) -> str | None:
    """Return a compact JSON/XML body suitable for DB storage."""
    if body is None:
        return None
    text = body.lstrip("\ufeff")
    if not text:
        return ""

    fmt = _sniff_format(text, request_format)
    if fmt == "json":
        try:
            return _compress_json(text)
        except json.JSONDecodeError, TypeError, ValueError:
            return text.strip()
    if fmt == "xml":
        return _compress_xml(text)
    return text


def prettify_audit_body(
    body: str | None,
    *,
    request_format: str | None = None,
) -> str:
    """Return indented JSON/XML for admin downloads."""
    if body is None:
        return ""
    text = body.lstrip("\ufeff")
    if not text:
        return ""

    fmt = _sniff_format(text, request_format)
    if fmt == "json":
        try:
            return _prettify_json(text)
        except json.JSONDecodeError, TypeError, ValueError:
            return text
    if fmt == "xml":
        return _prettify_xml(text)
    return text
