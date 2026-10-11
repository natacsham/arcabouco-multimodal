"""Catalogue metadata tests, not documentary validation of cited publications."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "vendor"))
import source_catalog as catalog
import prepare_public_data as public_data


def fixture():
    return {
        "metadata": {"version": "test", "public_projection": True},
        "sources": [{"id": "F1", "titulo": "Synthetic source", "status": "DOCUMENTADO"}],
        "references": [{"id": "R1", "fonte_que_cita_id": "F1", "referencia_exata": catalog.WITHHELD,
                        "status": "REFERENCIA_CITADA"}],
        "reference_audit": [{"reference_id": "R1", "citation": "", "promotion_status": "BIBLIOGRAFIA_CITADA",
                             "full_text_available": "NAO_CONFIRMADO", "priority": "A_AVALIAR"}],
        "excerpts": [{"id": "T1", "fonte_id": "F1", "localizacao_publica": "Section 2",
                      "trecho": "PRIVATE DOCUMENT QUOTATION"}],
        "contributions": [{"id": "C1", "excerpt_id": "T1", "knowledge_id": "K1", "articulation_id": "A1",
                           "statement": "Own paraphrase", "verification_status": "CONFERIDA_NO_REGISTRO"}],
        "knowledge": [{"id": "K1", "enunciado": "Unmodified decision knowledge"}],
        "articulations": [{"id": "A1", "operation_explanation": "Unmodified analysis"}],
    }


class SourceCatalogTests(unittest.TestCase):
    def test_http_and_https_not_misclassified_as_windows_paths(self):
        citation = "A citation. https://www.w3.org/TR/WCAG22/"
        self.assertEqual(public_data.scrub(citation), citation)
        self.assertEqual(public_data.scrub("http://example.org/"), "http://example.org/")
        self.assertEqual(public_data.scrub(r"At C:\Users\example\file.pdf"), catalog.WITHHELD)
        self.assertEqual(public_data.scrub("file:///private.pdf"), catalog.WITHHELD)

    def test_unbroken_doi_and_wcag_edition_do_not_imply_consultation(self):
        row = catalog.extract_metadata("WCAG 2.2. https://doi.org/10.1234/abc_1.")
        self.assertEqual(row["doi"], "10.1234/abc_1")
        self.assertEqual(row["edition"], "WCAG 2.2")
        self.assertEqual(row["url"], "https://doi.org/10.1234/abc_1")
        self.assertNotIn("consulted_at", row)

    def test_spaced_url_is_candidate_not_repaired_fact(self):
        row = catalog.extract_metadata("WCAG 2.2. ⟨https: //www.w3.org/TR/WCAG22/⟩.")
        self.assertIsNone(row["url"])
        self.assertEqual(row["url_candidates"][0]["status"], "CANDIDATA_REPARO_ESPACAMENTO")
        self.assertEqual(row["url_candidates"][0]["value"], "https://www.w3.org/TR/WCAG22/")

    def test_split_bare_url_not_published_as_partial_link(self):
        row = catalog.extract_metadata("Available: http://example.org/toasts. html.")
        self.assertIsNone(row["url"])
        self.assertEqual(row["url_candidates"][0]["status"], "POSSIVEL_QUEBRA_NA_URL")

    def test_historical_access_date_not_current_consultation(self):
        data = fixture()
        data["references"][0]["referencia_exata"] = "<https://www.w3.org/TR/>. Acesso em: 21 jun. 2025."
        result = catalog.reconcile(data)
        self.assertIsNone(result["references"][0]["consulted_at"])
        self.assertEqual(result["references"][0]["access_status"], catalog.UNCONSULTED)

    def test_repair_id_and_citing_source_guard_without_promotion(self):
        data = fixture()
        preserved = copy.deepcopy(data)
        preserved["references"][0]["referencia_exata"] = "Synthetic citation. https://example.org/publication"
        result = catalog.reconcile(data, preserved, "a" * 64)
        ref = result["references"][0]
        self.assertEqual(ref["referencia_exata"], preserved["references"][0]["referencia_exata"])
        self.assertEqual(ref["bibliographic_repair"]["source_sha256"], "a" * 64)
        self.assertEqual(result["reference_audit"][0]["promotion_status"], "BIBLIOGRAFIA_CITADA")
        self.assertEqual(result["reference_audit"][0]["full_text_available"], "NAO_CONFIRMADO")
        for key in data.keys() - catalog.EDITABLE:
            self.assertEqual(data[key], result[key], key)
        self.assertEqual(catalog.reconcile(result, preserved, "a" * 64), result)
        preserved["references"][0]["fonte_que_cita_id"] = "OTHER"
        self.assertEqual(catalog.reconcile(data, preserved)["references"][0]["referencia_exata"], catalog.WITHHELD)

    def test_repair_does_not_copy_actual_private_path(self):
        data = fixture()
        preserved = copy.deepcopy(data)
        preserved["references"][0]["referencia_exata"] = r"Private C:\Users\example\file.pdf"
        self.assertEqual(catalog.reconcile(data, preserved)["references"][0]["referencia_exata"], catalog.WITHHELD)

    def test_existing_manually_verified_metadata_preserved(self):
        data = fixture()
        data["sources"][0].update(url="https://example.org/source", urls=["https://example.org/source"],
                                  consulted_at="2026-10-11", access_status="CONSULTADA_ONLINE", edition="2")
        result = catalog.reconcile(data)
        for key in ("url", "urls", "consulted_at", "access_status", "edition"):
            self.assertEqual(data["sources"][0][key], result["sources"][0][key])

    def test_duplicate_candidate_keeps_two_citing_occurrences(self):
        data = fixture()
        data["references"][0]["referencia_exata"] = "Citation <https://doi.org/10.1234/example>"
        data["references"].append({**data["references"][0], "id": "R2"})
        data["reference_audit"].append({**data["reference_audit"][0], "reference_id": "R2"})
        result = catalog.reconcile(data)
        self.assertEqual(len(result["references"]), 2)
        self.assertIn("R2", result["reference_audit"][0]["duplicate_candidates"][0]["reference_ids"])

    def test_public_projection_connects_existing_records_without_document_text(self):
        result = catalog.public_catalog(catalog.reconcile(fixture()))
        source = result["sources"][0]
        self.assertEqual(source["excerpts"][0]["id"], "T1")
        self.assertEqual(source["contributions"][0]["id"], "C1")
        self.assertEqual(source["contributions"][0]["knowledge_id"], "K1")
        self.assertNotIn("PRIVATE DOCUMENT QUOTATION", json.dumps(result))
        self.assertNotIn("arquivo", source)

    def test_public_projection_rejects_private_locator(self):
        data = fixture()
        data["excerpts"][0]["localizacao_publica"] = r"C:\Users\example\private.pdf"
        with self.assertRaises(ValueError):
            catalog.public_catalog(catalog.reconcile(data))

    def test_norm_number_in_citation_not_silently_corrected(self):
        row = catalog.extract_metadata("ABNT NBR 170060: requisitos. 2022.")
        self.assertEqual(row["edition"], "NBR 170060:2022")
        self.assertEqual(row["edition_status"], "DECLARADA_NA_CITACAO_A_CONFERIR")

    def test_invalid_links_or_foreign_keys_are_rejected(self):
        for url in ("javascript:alert(1)", "file:///private", "https://localhost/", "https://127.0.0.1/",
                    "https://10.0.0.1/", "https://user:secret@example.org/", "https://example.org/has space",
                    "https://example.org/\x00x", r"https://example.org\wrong"):
            with self.subTest(url=url):
                self.assertFalse(catalog.public_url(url))
        data = fixture()
        data["excerpts"][0]["fonte_id"] = "MISSING"
        self.assertFalse(catalog.audit_catalog(data)["passed"])
        with self.assertRaises(ValueError):
            catalog.public_catalog(data)

    def test_check_never_writes_and_rejects_write_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "base.json"
            path.write_text(json.dumps(fixture()), encoding="utf8")
            before = path.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(catalog.main(["--base", str(path), "--check"]), 0)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(len(list(Path(directory).iterdir())), 1)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                catalog.main(["--base", str(path), "--check", "--apply"])

    def test_actual_catalogue_integrity_and_unpromoted_references(self):
        data = json.loads((ROOT / "data/knowledge-base.json").read_text(encoding="utf8"))
        report = catalog.audit_catalog(data)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["counts"]["references"], 156)
        self.assertEqual(report["counts"]["reference_audit"], 156)
        self.assertTrue(all(r["promotion_status"] == "BIBLIOGRAFIA_CITADA" for r in data["reference_audit"]))


if __name__ == "__main__":
    unittest.main()
