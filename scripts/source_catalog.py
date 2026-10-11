"""Reconcile existing source metadata and project a public link catalogue.

No network, PDF download, document extraction or promotion of knowledge occurs
here. --check is read-only. Bibliographic repairs require an explicit input and
--apply; all other knowledge-base collections are preserved byte-semantically.
"""
import argparse
import copy
import hashlib
import ipaddress
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
EDITABLE = frozenset({"sources", "references", "reference_audit"})
LOCAL_PATH = re.compile(r"(?<![\w:/\\])[A-Za-z]:[\\/]|file://", re.I)
WITHHELD = "[Caminho local omitido da distribuição pública]"
UNCONSULTED = "NAO_CONSULTADA_NESTA_REVISAO"


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def normalized_text(value):
    return " ".join(unicodedata.normalize("NFC", value or "").casefold().split())


def public_url(value):
    """Accept a syntactic public HTTP(S) locator, not evidence of its existence."""
    if not isinstance(value, str) or re.search(r"\s|[\x00-\x1f\x7f<>⟨⟩\\]", value):
        return False
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        if parsed.username or parsed.password or parsed.hostname.lower() == "localhost":
            return False
        if "." not in parsed.hostname or parsed.hostname.endswith((".local", ".internal")):
            return False
        try:
            return ipaddress.ip_address(parsed.hostname).is_global
        except ValueError:
            return True
    except ValueError:
        return False


def trim_locator(value):
    value = value.rstrip(".,;:")
    while value.endswith(")") and value.count(")") > value.count("("):
        value = value[:-1]
    return value


def extract_metadata(citation):
    """Conservative metadata extraction; OCR repairs remain unverified candidates."""
    candidates, masked = [], citation or ""
    spans = list(re.finditer(r"[<⟨]([^>⟩]+)[>⟩]", masked))
    for match in spans:
        raw = match.group(1).strip()
        compact = re.sub(r"\s+", "", raw)
        if compact.startswith(("http://", "https://")):
            candidate = trim_locator(compact)
            candidates.append({"raw": raw, "value": candidate,
                               "status": "CANDIDATA_REPARO_ESPACAMENTO" if compact != raw
                               else "EXTRAIDA_NAO_CONFERIDA"})
    # Preserve offsets while excluding locators already delimited by brackets.
    for match in reversed(spans):
        masked = masked[:match.start()] + " " * (match.end() - match.start()) + masked[match.end():]
    for match in re.finditer(r"https?://[^\s<>⟨⟩]+", masked):
        raw = match.group(0)
        following = masked[match.end():].strip()
        boundary = not following or bool(re.match(
            r"^[.,;]?\s*(?:Acesso|Access|Retrieved|Dispon[ií]vel|DOI|Latest)\b", following, re.I))
        candidates.append({"raw": raw, "value": trim_locator(raw),
                           "status": "EXTRAIDA_NAO_CONFERIDA" if boundary
                           else "POSSIVEL_QUEBRA_NA_URL"})
    valid, unique = [], []
    for item in candidates:
        if not public_url(item["value"]):
            item["status"] = "LOCALIZADOR_A_CONFERIR"
        if item not in unique:
            unique.append(item)
        if item["status"] == "EXTRAIDA_NAO_CONFERIDA" and item["value"] not in valid:
            valid.append(item["value"])
    dois = []
    for value in valid:
        parsed = urlsplit(value)
        if parsed.hostname in {"doi.org", "dx.doi.org"}:
            candidate = parsed.path.lstrip("/")
            if re.fullmatch(r"10\.\d{4,9}/\S+", candidate, re.I):
                dois.append(candidate.lower())
    # Bare, unbroken DOI, with no attempt to repair text extraction artifacts.
    for match in re.finditer(r"(?<![/\w])10\.\d{4,9}/[^\s<>⟨⟩]+", masked):
        tail = masked[match.end():].strip()
        if not tail or re.match(r"^(?:Acesso|Access|Retrieved)\b", tail, re.I):
            candidate = trim_locator(match.group(0)).lower()
            if candidate not in dois:
                dois.append(candidate)
    edition, edition_status = None, "NAO_IDENTIFICADA"
    wcag = re.search(r"(?:WCAG\)?\s*|WCAG\s+)(\d+\.\d+)", citation or "", re.I)
    nbr = re.search(r"NBR\s*(\d{4,6})\s*[:–—-].*?\b((?:19|20)\d{2})\b", citation or "", re.I)
    if wcag:
        edition, edition_status = "WCAG " + wcag.group(1), "DECLARADA_NA_CITACAO"
    elif nbr:
        edition, edition_status = "NBR " + nbr.group(1) + ":" + nbr.group(2), "DECLARADA_NA_CITACAO_A_CONFERIR"
    return {"url": valid[0] if valid else None, "urls": valid,
            "url_candidates": unique, "doi": dois[0] if len(set(dois)) == 1 else None,
            "edition": edition, "edition_status": edition_status}


def duplicate_groups(references):
    """Candidate equivalences only; keep every occurrence and its citing source."""
    buckets = defaultdict(set)
    for row in references:
        if row.get("doi"):
            buckets[("DOI", row["doi"].lower())].add(row["id"])
        for url in row.get("urls", []):
            if public_url(url):
                p = urlsplit(url)
                normalized = urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), p.query, ""))
                buckets[("URL", normalized)].add(row["id"])
        citation = row.get("referencia_exata", "")
        if citation and citation != WITHHELD:
            buckets[("CITACAO_EXATA_NORMALIZADA", normalized_text(citation))].add(row["id"])
    return [{"basis": basis, "reference_ids": sorted(ids)}
            for (basis, _), ids in sorted(buckets.items()) if len(ids) > 1]


def reconcile(data, preserved=None, preserved_sha256=None):
    updated = copy.deepcopy(data)
    originals = {r["id"]: r for r in (preserved or {}).get("references", [])}
    for row in updated.get("references", []):
        original = originals.get(row["id"])
        if row.get("referencia_exata") == WITHHELD and original:
            citation = original.get("referencia_exata", "")
            # ID AND citing source must agree; never recover document passages.
            if (original.get("fonte_que_cita_id") == row.get("fonte_que_cita_id")
                    and citation and citation != WITHHELD and not LOCAL_PATH.search(citation)):
                row["referencia_exata"] = citation
                row["bibliographic_repair"] = {
                    "reason": "HTTP_URL_MISCLASSIFIED_AS_LOCAL_PATH",
                    "previous_value": WITHHELD,
                    "source_version": (preserved or {}).get("metadata", {}).get("version"),
                    "source_sha256": preserved_sha256,
                    "reference_id": row["id"],
                    "previous_value_sha256": digest(WITHHELD),
                    "restored_citation_sha256": digest(citation),
                }
    for collection in ("sources", "references"):
        for row in updated.get(collection, []):
            extracted = extract_metadata(row.get("referencia_exata", row.get("titulo", "")))
            for key, value in extracted.items():
                row.setdefault(key, value)
            row.setdefault("consulted_at", None)
            row.setdefault("access_status", UNCONSULTED)
            row.setdefault("metadata_origin", "BIBLIOGRAFIA_PRESERVADA" if collection == "references"
                           else "REGISTRO_EXISTENTE_NAO_RECONFERIDO_ONLINE")
    groups = duplicate_groups(updated.get("references", []))
    audits = {r["reference_id"]: r for r in updated.get("reference_audit", [])}
    for ref in updated.get("references", []):
        # The 156 existing audit rows are reconciled, never replaced or promoted.
        audit = audits.get(ref["id"])
        if audit is not None:
            audit["citation"] = ref.get("referencia_exata", "")
            audit["duplicate_candidates"] = [
                {"basis": g["basis"], "reference_ids": [i for i in g["reference_ids"] if i != ref["id"]]}
                for g in groups if ref["id"] in g["reference_ids"]]
            audit["metadata_status"] = "LOCALIZADOR_EXTRAIDO_NAO_CONFERIDO" if ref.get("url") or ref.get("doi") else (
                "LOCALIZADOR_CANDIDATO_A_CONFERIR" if ref.get("url_candidates") else "SEM_LOCALIZADOR_ESTRUTURADO")
    if any(updated.get(key) != value for key, value in data.items() if key not in EDITABLE):
        raise ValueError("Reconciliation modified a non-catalogue collection")
    return updated


def audit_catalog(data):
    errors = []
    source_ids = {r["id"] for r in data.get("sources", [])}
    reference_ids = {r["id"] for r in data.get("references", [])}
    for collection, field in (("sources", "id"), ("references", "id"), ("reference_audit", "reference_id")):
        ids = [r[field] for r in data.get(collection, [])]
        if len(ids) != len(set(ids)):
            errors.append({"collection": collection, "reason": "DUPLICATE_ID"})
    if reference_ids != {r["reference_id"] for r in data.get("reference_audit", [])}:
        errors.append({"reason": "REFERENCE_AUDIT_IDS_MISMATCH"})
    for row in data.get("references", []):
        if row.get("fonte_que_cita_id") not in source_ids:
            errors.append({"id": row["id"], "reason": "CITING_SOURCE_MISSING"})
    for row in data.get("excerpts", []):
        if row.get("fonte_id") not in source_ids:
            errors.append({"id": row["id"], "reason": "EXCERPT_SOURCE_MISSING"})
    for collection in ("sources", "references"):
        for row in data.get(collection, []):
            for url in row.get("urls", []) + ([row["url"]] if row.get("url") else []):
                if not public_url(url):
                    errors.append({"id": row["id"], "reason": "UNSAFE_OR_MALFORMED_URL"})
            if row.get("consulted_at"):
                try:
                    date.fromisoformat(row["consulted_at"])
                except (ValueError, TypeError):
                    errors.append({"id": row["id"], "reason": "INVALID_CONSULTATION_DATE"})
            if row.get("access_status") == UNCONSULTED and row.get("consulted_at"):
                errors.append({"id": row["id"], "reason": "UNCONSULTED_WITH_CONSULTATION_DATE"})
            if LOCAL_PATH.search(row.get("referencia_exata", "")):
                errors.append({"id": row["id"], "reason": "LOCAL_PATH_IN_CITATION"})
    refs = data.get("references", [])
    return {"passed": not errors, "errors": errors,
            "counts": {"sources": len(source_ids), "references": len(refs),
                       "reference_audit": len(data.get("reference_audit", [])),
                       "excerpts": len(data.get("excerpts", [])),
                       "with_url": sum(bool(r.get("url")) for r in refs),
                       "with_doi": sum(bool(r.get("doi")) for r in refs),
                       "repaired_bibliographies": sum(bool(r.get("bibliographic_repair")) for r in refs)},
            "unresolved_reference_ids": [r["id"] for r in refs if not r.get("url") and not r.get("doi")],
            "unverified_reference_ids": [r["id"] for r in refs if r.get("access_status", UNCONSULTED) == UNCONSULTED],
            "duplicate_candidates": duplicate_groups(refs),
            "unchanged_collection_sha256": {k: digest(v) for k, v in data.items() if k not in EDITABLE},
            "limits": ["Localizadores não equivalem a documentos consultados ou fundamentos conferidos.",
                       "Nenhuma duplicata é mesclada automaticamente; cada ocorrência bibliográfica mantém seu ID."]}


def public_catalog(data):
    report = audit_catalog(data)
    if not report["passed"]:
        raise ValueError("Invalid catalogue: " + json.dumps(report["errors"]))
    # Explicit allowlist excludes document text, private filenames and audit paths.
    fields = ("id", "titulo", "tipo", "status", "url", "urls", "doi", "edition", "edition_status",
              "consulted_at", "access_status", "metadata_origin")
    result = {"schema_version": "1.0", "base_version": data.get("metadata", {}).get("version"),
              "source_collections_sha256": {k: digest(data.get(k, [])) for k in (
                  "sources", "references", "reference_audit", "excerpts", "contributions")},
              "summary": {**report["counts"],
                          "unresolved_references": len(report["unresolved_reference_ids"]),
                          "unverified_references": len(report["unverified_reference_ids"]),
                          "duplicate_candidate_groups": len(report["duplicate_candidates"])},
              "limits": report["limits"], "sources": [], "references": []}
    for source in data.get("sources", []):
        row = {key: source.get(key) for key in fields}
        excerpts = [x for x in data.get("excerpts", []) if x.get("fonte_id") == source["id"]]
        row["excerpts"] = [{key: x.get(key) for key in (
            "id", "localizacao_publica", "estado_publicacao", "status_curadoria",
            "document_url", "document_version", "document_review_status", "document_review_date")} for x in excerpts]
        excerpt_ids = {x["id"] for x in excerpts}
        row["contributions"] = [{key: c.get(key) for key in (
            "id", "excerpt_id", "articulation_id", "knowledge_id", "contribution_role", "verification_status")}
            for c in data.get("contributions", []) if c.get("excerpt_id") in excerpt_ids]
        row["excerpt_review_stats"] = {
            "total": len(excerpts),
            "by_curation_status": dict(Counter(x.get("status_curadoria") or "NAO_REGISTRADO" for x in excerpts)),
            "contributions_by_verification_status": dict(Counter(
                c.get("verification_status") or "NAO_REGISTRADO" for c in row["contributions"])),
        }
        result["sources"].append(row)
    audits = {r["reference_id"]: r for r in data.get("reference_audit", [])}
    for reference in data.get("references", []):
        row = {key: reference.get(key) for key in fields if key not in {"titulo", "tipo"}}
        row.update({"referencia_exata": reference.get("referencia_exata"),
                    "fonte_que_cita_id": reference.get("fonte_que_cita_id"),
                    "audit": {key: audits.get(reference["id"], {}).get(key) for key in (
                        "priority", "full_text_available", "promotion_status", "metadata_status", "duplicate_candidates")}})
        result["references"].append(row)
    def reject_private_paths(value):
        if isinstance(value, dict):
            for child in value.values():
                reject_private_paths(child)
        elif isinstance(value, list):
            for child in value:
                reject_private_paths(child)
        elif isinstance(value, str) and LOCAL_PATH.search(value):
            raise ValueError("Private local path in the public catalogue projection")
    reject_private_paths(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=ROOT / "data/knowledge-base.json")
    parser.add_argument("--check", action="store_true", help="Read-only catalogue audit; no files written")
    parser.add_argument("--reconcile-from", type=Path, help="Read bibliographic metadata only from an existing private JSON")
    parser.add_argument("--apply", action="store_true", help="Explicitly update ONLY the three catalogue collections")
    parser.add_argument("--write-projection", type=Path, help="Explicit output for a derived public catalogue")
    parser.add_argument("--check-projection", type=Path, help="Read-only comparison with the projection of the current base")
    args = parser.parse_args(argv)
    if args.check and (args.apply or args.write_projection or args.reconcile_from):
        parser.error("--check is read-only and cannot be combined with mutation or reconciliation")
    if args.write_projection and args.write_projection.resolve() == args.base.resolve():
        parser.error("Projection must not overwrite the knowledge base")
    original = json.loads(args.base.read_text(encoding="utf-8-sig"))
    data = original
    if args.reconcile_from or args.apply:
        preserved, checksum = None, None
        if args.reconcile_from:
            raw = args.reconcile_from.read_bytes()
            preserved, checksum = json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()
        data = reconcile(original, preserved, checksum)
    report = audit_catalog(data)
    if args.check_projection:
        try:
            actual = json.loads(args.check_projection.read_text(encoding="utf-8-sig"))
            report["projection_matches_base"] = actual == public_catalog(data)
        except (OSError, ValueError) as error:
            report["projection_matches_base"] = False
            report["errors"].append("Projection cannot be checked: " + type(error).__name__)
        report["passed"] = report["passed"] and report["projection_matches_base"]
    if args.apply and report["passed"]:
        # Mechanical metadata transformation; never edit arbitrary base collections.
        args.base.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.write_projection and report["passed"]:
        args.write_projection.parent.mkdir(parents=True, exist_ok=True)
        args.write_projection.write_text(json.dumps(public_catalog(data), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
