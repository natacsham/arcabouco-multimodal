"""Regression of the ontology contract using synthetic, in-memory graphs.

These tests do not import the AMADO engine, read private sessions, or claim
expert validation. Run from the project root: python -m unittest discover -s tests.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL
from rdflib.collection import Collection
from pyshacl import validate

M = Namespace("https://w3id.org/mado#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
TBOX = ROOT / "ontology" / "main.ttl"
SHAPES = ROOT / "shapes" / "main.shacl.ttl"


def text(value):
    return Literal(value, lang="pt-BR")


def fixture():
    """Two criteria with distinct support sets inside ONE configuration."""
    g = Graph()
    g.bind("mado", M)
    g.add((M.F1, RDF.type, M.Fonte))
    g.add((M.P1, RDF.type, M.Perspectiva))
    for number in (1, 2):
        k, t, ca, ori = (M[f"{prefix}{number}"] for prefix in ("K", "T", "CA", "ORI"))
        g.add((t, RDF.type, M.TrechoDocumental))
        g.add((t, M.identificador, Literal(f"T{number}")))
        g.add((t, M.conteudoDoTrecho, text("Trecho sintético para teste estrutural.")))
        g.add((t, M.trechoDeFonte, M.F1))
        g.add((k, RDF.type, M.ConhecimentoMultimodalArticulado))
        g.add((k, M.identificador, Literal(f"K{number}")))
        g.add((k, M.enunciado, text(f"Conhecimento sintético {number}.")))
        g.add((k, M.derivadoDe, M.F1))
        g.add((k, M.sustentadoPorTrecho, t))
        g.add((k, M.articuladoSobPerspectiva, M.P1))
        g.add((k, M.classificacaoOperacional, Literal("OPERACIONALIZAVEL")))
        g.add((ca, RDF.type, M.CriterioDeDecisaoMultimodal))
        g.add((ca, M.enunciado, text(f"Critério sintético {number}.")))
        g.add((ca, M.possuiOrigem, ori))
        g.add((ori, RDF.type, M.RelacaoDeOrigemDoCriterio))
        g.add((ori, M.origemEmFonte, M.F1))
        g.add((ori, M.origemSustentadaPorTrecho, t))
    g.add((M.CTX, RDF.type, M.ContextoDeInteracaoDigital))
    g.add((M.CTX, M.identificador, Literal("CTX")))
    g.add((M.CTX, M.descricaoDoContexto, text("Contexto sintético, não empírico.")))
    g.add((M.CTX, M.descritoSobPerspectiva, M.P1))
    g.add((M.CTX, M.statusConfirmacao, Literal("CONFIRMADO_PARA_TESTE")))
    g.add((M.CTX, M.temTarefa, M.TAREFA))
    g.add((M.CTX, M.apresentaNecessidade, M.NECESSIDADE))
    g.add((M.CTX, M.temParticipacao, M.PART))
    g.add((M.PART, RDF.type, M.ParticipacaoNoContexto))
    g.add((M.PART, M.identificador, Literal("PART")))
    g.add((M.PART, M.participacaoEmContexto, M.CTX))
    g.add((M.PART, M.temPapelNoContexto, M.PAPEL))
    g.add((M.PART, M.origemDoRegistro, Literal("SINTETICO_NAO_EMPIRICO")))
    g.add((M.D, RDF.type, M.DecisaoDeAcessibilidadeMultimodal))
    g.add((M.D, M.identificador, Literal("D")))
    g.add((M.D, M.enunciado, text("Decisão sintética.")))
    g.add((M.D, M.rationale, text("Racional sintético.")))
    g.add((M.D, M.statusDecisao, Literal("GERADA")))
    g.add((M.D, M.respondeA, M.CTX))
    g.add((M.D, M.sustentadaPor, M.K1))
    g.add((M.D, M.sustentadaPor, M.K2))
    g.add((M.D, M.aplicaCriterio, M.CA1))
    g.add((M.D, M.aplicaCriterio, M.CA2))
    g.add((M.D, M.atendeRequisitoDeExpressao, M.K1))
    for predicate in (M.alternativa, M.condicaoDeAplicacao, M.limite,
                      M.indicadorDeAcompanhamento, M.resultadoEsperado):
        g.add((M.D, predicate, text("Informação sintética.")))
    g.add((M.D, M.estatutoDoResultadoEsperado, Literal("EXPECTATIVA_NAO_OBSERVADA")))
    add_configuration(g, M.CFG, [(M.CA1, M.K1, M.ORI1), (M.CA2, M.K2, M.ORI2)])
    return g


def add_configuration(g, cfg, applications):
    g.add((M.D, M.possuiConfiguracaoModal, cfg))
    g.add((cfg, RDF.type, M.ConfiguracaoModalDaDecisao))
    g.add((cfg, M.identificador, Literal(str(cfg).split("#")[-1])))
    g.add((cfg, M.configuracaoDeDecisao, M.D))
    g.add((cfg, M.configuraModalidade, M.MOD_TEXTO))
    g.add((cfg, M.executadaPorPapel, M.PAPEL))
    g.add((cfg, M.temPapelModal, M.PRINCIPAL))
    g.add((cfg, M.configuracaoConsideraCondicao, M.NECESSIDADE))
    g.add((cfg, M.cumpreFuncaoDecisoria, M.FUNCAO))
    for predicate in (M.temFuncaoModal, M.temAcaoOperacional, M.condicaoDaConfiguracao,
                      M.alternativaDaConfiguracao, M.acompanhamentoDaConfiguracao,
                      M.limiteDaConfiguracao, M.significadoFuncional):
        g.add((cfg, predicate, text("Informação sintética.")))
    g.add((cfg, M.estadoDeDisponibilidadeDaConfiguracao, Literal("CONFIRMADO_DISPONIVEL")))
    for number, (ca, k, ori) in enumerate(applications, 1):
        app = M[f"{str(cfg).split('#')[-1]}-APP-{number}"]
        g.add((cfg, M.possuiAplicacaoDeCriterio, app))
        g.add((cfg, M.configuracaoAplicaCriterio, ca))
        g.add((cfg, M.configuracaoSustentadaPorConhecimento, k))
        g.add((cfg, M.configuracaoUsaOrigemDoCriterio, ori))
        g.add((app, RDF.type, M.AplicacaoDeCriterio))
        g.add((app, M.aplicacaoNaConfiguracao, cfg))
        g.add((app, M.criterioAplicado, ca))
        g.add((app, M.conhecimentoDaAplicacao, k))
        g.add((app, M.origemDaAplicacao, ori))
        g.add((app, M.justificativaDaAplicacao, text(f"Fundamento sintético do critério {number}.")))


def erase_configurations(g):
    for cfg in list(g.objects(M.D, M.possuiConfiguracaoModal)):
        for app in list(g.objects(cfg, M.possuiAplicacaoDeCriterio)):
            g.remove((app, None, None))
            g.remove((None, None, app))
        g.remove((cfg, None, None))
        g.remove((None, None, cfg))


def add_articulation(g):
    g.add((M.ART, RDF.type, M.ArticulacaoDocumentada))
    g.add((M.ART, M.identificador, Literal("ART")))
    g.add((M.ART, M.tipoDeArticulacao, Literal("COMPLEMENTA")))
    g.add((M.ART, M.articulaConhecimentoDeEntrada, M.K1))
    g.add((M.ART, M.produzConhecimento, M.K2))
    g.add((M.ART, M.articulacaoDerivadaDe, M.F1))
    g.add((M.ART, M.articulacaoSustentadaPorTrecho, M.T1))
    g.add((M.ART, M.origemDaRelacao, Literal("RECONSTRUCAO_SINTETICA_PARA_TESTE")))
    g.add((M.ART, M.nivelDeConfirmacao, Literal("DOCUMENTADA_E_RECONSTRUIDA")))
    g.add((M.ART, M.estadoDeCuradoria, Literal("APROVADA_PARA_CONSULTA_RC3")))
    g.add((M.ART, M.habilitadaParaDecisao, Literal(True)))
    g.add((M.ART, M.condicaoDaArticulacao, text("Condição sintética.")))
    g.add((M.ART, M.limiteDaArticulacao, text("Não é evidência empírica.")))


class OntologyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tbox = Graph().parse(TBOX, format="turtle")
        cls.shapes = Graph().parse(SHAPES, format="turtle")

    def check(self, graph, expected):
        conforms, _, report = validate(graph, shacl_graph=self.shapes,
                                       inference="none", allow_warnings=True)
        self.assertEqual(bool(conforms), expected, str(report))

    def test_positive_complete_graph(self):
        self.check(fixture(), True)

    def test_expression_requirement_not_imposed_without_k33(self):
        g = fixture()
        g.remove((M.D, M.atendeRequisitoDeExpressao, None))
        self.check(g, True)

    @staticmethod
    def with_expression_knowledge():
        g = fixture()
        for predicate, value in list(g.predicate_objects(M.K1)):
            g.add((M.K33, predicate, value))
        g.set((M.K33, M.identificador, Literal("K33")))
        g.add((M.D, M.sustentadaPor, M.K33))
        return g

    def test_selected_k33_without_expression_link_fails(self):
        g = self.with_expression_knowledge()
        g.remove((M.D, M.atendeRequisitoDeExpressao, None))
        self.check(g, False)

    def test_selected_k33_requires_its_own_expression_link(self):
        self.check(self.with_expression_knowledge(), False)

    def test_selected_k33_with_exact_expression_link_passes(self):
        g = self.with_expression_knowledge()
        g.add((M.D, M.atendeRequisitoDeExpressao, M.K33))
        self.check(g, True)

    def test_six_core_classes_remain_disjoint(self):
        expected = {M.Fonte, M.ConhecimentoMultimodalArticulado,
                    M.CriterioDeDecisaoMultimodal, M.ContextoDeInteracaoDigital,
                    M.DecisaoDeAcessibilidadeMultimodal, M.Resultado}
        groups = [set(Collection(self.tbox, head)) for head in self.tbox.objects(None, OWL.members)]
        self.assertIn(expected, groups)
        self.assertNotIn((M.Deficiencia, RDF.type, OWL.Class), self.tbox)
        self.assertNotIn((M.Pessoa, RDF.type, OWL.Class), self.tbox)

    def test_all_local_classes_have_definitions(self):
        for entity in self.tbox.subjects(RDF.type, OWL.Class):
            if str(entity).startswith(str(M)):
                self.assertTrue(list(self.tbox.objects(entity, RDFS.comment)), entity)

    def test_application_domains_ranges_and_inverse(self):
        self.assertIn((M.aplicacaoNaConfiguracao, OWL.inverseOf, M.possuiAplicacaoDeCriterio), self.tbox)
        self.assertIn((M.criterioAplicado, RDFS.domain, M.AplicacaoDeCriterio), self.tbox)
        self.assertIn((M.criterioAplicado, RDFS.range, M.CriterioDeDecisaoMultimodal), self.tbox)
        self.assertIn((M.conhecimentoDaAplicacao, RDFS.range, M.ConhecimentoMultimodalArticulado), self.tbox)
        self.assertIn((M.origemDaAplicacao, RDFS.range, M.RelacaoDeOrigemDoCriterio), self.tbox)

    def test_cq4_returns_only_exact_application_pairs(self):
        g = fixture()
        query = (ROOT / "queries" / "CQ-004.rq").read_text(encoding="utf-8")
        rows = list(g.query(query.replace("mado:D-TESTE-RC4-TRANSFERENCIA", "mado:D")))
        self.assertEqual(len(rows), 2)
        self.assertEqual({(r.criterio, r.conhecimentoFundamento, r.origem) for r in rows},
                         {(M.CA1, M.K1, M.ORI1), (M.CA2, M.K2, M.ORI2)})
        self.assertTrue(all(r.aplicacao and r.justificativa for r in rows))

    def test_decision_without_any_configuration_fails(self):
        g = fixture()
        erase_configurations(g)
        self.check(g, False)

    def test_configuration_without_all_knowledge_fails(self):
        g = fixture()
        g.remove((M.CFG, M.configuracaoSustentadaPorConhecimento, None))
        for app in g.objects(M.CFG, M.possuiAplicacaoDeCriterio):
            g.remove((app, M.conhecimentoDaAplicacao, None))
        self.check(g, False)

    def test_configuration_without_applications_fails(self):
        g = fixture()
        for app in list(g.objects(M.CFG, M.possuiAplicacaoDeCriterio)):
            g.remove((app, None, None))
        g.remove((M.CFG, M.possuiAplicacaoDeCriterio, None))
        self.check(g, False)

    def test_valid_configuration_does_not_hide_invalid_use_of_same_criterion(self):
        g = fixture()
        add_configuration(g, M.CFG_BAD, [(M.CA1, M.K1, M.ORI2)])
        self.check(g, False)

    def test_application_without_knowledge_fails(self):
        g = fixture()
        g.remove((M['CFG-APP-1'], M.conhecimentoDaAplicacao, None))
        self.check(g, False)

    def test_application_without_origin_fails(self):
        g = fixture()
        g.remove((M['CFG-APP-1'], M.origemDaAplicacao, None))
        self.check(g, False)

    def test_application_without_type_still_fails(self):
        g = fixture()
        g.remove((M['CFG-APP-1'], RDF.type, None))
        self.check(g, False)

    def test_blank_application_justification_fails(self):
        g = fixture()
        g.set((M['CFG-APP-1'], M.justificativaDaAplicacao, text("   ")))
        self.check(g, False)

    def test_application_cannot_belong_to_two_configurations(self):
        g = fixture()
        add_configuration(g, M.CFG2, [(M.CA1, M.K1, M.ORI1)])
        g.add((M['CFG-APP-1'], M.aplicacaoNaConfiguracao, M.CFG2))
        self.check(g, False)

    def test_projection_cannot_contain_an_unapplied_criterion(self):
        g = fixture()
        g.add((M.CA3, RDF.type, M.CriterioDeDecisaoMultimodal))
        g.add((M.CFG, M.configuracaoAplicaCriterio, M.CA3))
        self.check(g, False)

    def test_projection_cannot_contain_an_unapplied_origin(self):
        g = fixture()
        g.add((M.ORI3, RDF.type, M.RelacaoDeOrigemDoCriterio))
        g.add((M.ORI3, M.origemEmFonte, M.F1))
        g.add((M.ORI3, M.origemSustentadaPorTrecho, M.T1))
        g.add((M.CFG, M.configuracaoUsaOrigemDoCriterio, M.ORI3))
        self.check(g, False)

    def test_configuration_may_have_additional_noncriterion_knowledge(self):
        g = fixture()
        g.remove((M['CFG-APP-2'], None, None))
        g.remove((M.CFG, M.possuiAplicacaoDeCriterio, M['CFG-APP-2']))
        g.remove((M.CFG, M.configuracaoAplicaCriterio, M.CA2))
        g.remove((M.CFG, M.configuracaoUsaOrigemDoCriterio, M.ORI2))
        self.check(g, True)

    def test_missing_status_cannot_bypass_generated_requirements(self):
        g = fixture()
        g.remove((M.D, M.statusDecisao, None))
        erase_configurations(g)
        self.check(g, False)

    def test_historical_decision_is_not_forced_to_have_new_configuration(self):
        g = fixture()
        erase_configurations(g)
        g.set((M.D, M.statusDecisao, Literal("DECISAO_HISTORICA_RECONSTRUIDA")))
        g.remove((M.D, M.aplicaCriterio, None))
        self.check(g, True)

    def test_suspended_decision_does_not_require_invented_support(self):
        g = fixture()
        erase_configurations(g)
        g.set((M.D, M.statusDecisao, Literal("SUSPENSA_POR_INSUFICIENCIA")))
        g.remove((M.D, M.sustentadaPor, None))
        g.remove((M.D, M.aplicaCriterio, None))
        self.check(g, True)

    def test_suspended_decision_must_not_present_configuration(self):
        g = fixture()
        g.set((M.D, M.statusDecisao, Literal("SUSPENSA")))
        self.check(g, False)

    def test_preparation_state_is_valid(self):
        g = fixture()
        g.set((M.CFG, M.estadoDeDisponibilidadeDaConfiguracao, Literal("REQUER_PREPARACAO")))
        self.check(g, True)

    def test_undeclared_resource_state_fails(self):
        g = fixture()
        g.set((M.CFG, M.estadoDeDisponibilidadeDaConfiguracao, Literal("TALVEZ")))
        self.check(g, False)

    def test_confirmed_articulation_is_valid(self):
        g = fixture()
        add_articulation(g)
        self.check(g, True)

    def test_unknown_confirmation_cannot_enable_articulation(self):
        g = fixture()
        add_articulation(g)
        g.set((M.ART, M.nivelDeConfirmacao, Literal("AINDA_NAO_REVISADA")))
        self.check(g, False)

    def test_unknown_curation_cannot_enable_articulation(self):
        g = fixture()
        add_articulation(g)
        g.set((M.ART, M.estadoDeCuradoria, Literal("PENDENTE")))
        self.check(g, False)

    def test_restricted_excerpt_with_reference_and_location_is_valid(self):
        g = fixture()
        g.remove((M.T1, M.conteudoDoTrecho, None))
        g.add((M.T1, M.estadoDePublicacaoDoTrecho, Literal("TEXTO_NAO_REDISTRIBUIDO")))
        g.add((M.T1, M.localizacaoDocumental, Literal("Registro de teste, seção 1")))
        self.check(g, True)

    def test_missing_excerpt_content_without_explicit_restriction_fails(self):
        g = fixture()
        g.remove((M.T1, M.conteudoDoTrecho, None))
        self.check(g, False)

    def test_restricted_excerpt_without_locator_fails(self):
        g = fixture()
        g.remove((M.T1, M.conteudoDoTrecho, None))
        g.add((M.T1, M.estadoDePublicacaoDoTrecho, Literal("TEXTO_NAO_REDISTRIBUIDO")))
        self.check(g, False)

    def test_restricted_marker_cannot_coexist_with_original_excerpt(self):
        g = fixture()
        g.add((M.T1, M.estadoDePublicacaoDoTrecho, Literal("TEXTO_NAO_REDISTRIBUIDO")))
        g.add((M.T1, M.localizacaoDocumental, Literal("Seção 1")))
        self.check(g, False)

    def test_document_locator_must_match_string_datatype_contract(self):
        g = fixture()
        g.add((M.T1, M.localizacaoDocumental, text("Seção 1")))
        self.check(g, False)

    def test_restricted_excerpt_without_source_fails(self):
        g = fixture()
        g.remove((M.T1, M.conteudoDoTrecho, None))
        g.remove((M.T1, M.trechoDeFonte, None))
        g.add((M.T1, M.estadoDePublicacaoDoTrecho, Literal("TEXTO_NAO_REDISTRIBUIDO")))
        g.add((M.T1, M.localizacaoDocumental, Literal("Registro de teste, seção 1")))
        self.check(g, False)

    def test_restricted_result_preserves_record_without_inventing_outcome(self):
        g = fixture()
        g.add((M.R1, RDF.type, M.Resultado))
        g.add((M.R1, M.identificador, Literal("R1")))
        g.add((M.R1, M.registradoEm, M.F1))
        g.add((M.R1, M.estadoDePublicacaoDoRegistro, Literal("TEXTO_NAO_REDISTRIBUIDO")))
        g.add((M.R1, M.localizacaoDocumental, Literal("Resultado no trecho T1 do documento de teste.")))
        self.check(g, True)

    def test_restricted_result_without_locator_fails(self):
        g = fixture()
        g.add((M.R1, RDF.type, M.Resultado))
        g.add((M.R1, M.identificador, Literal("R1")))
        g.add((M.R1, M.registradoEm, M.F1))
        g.add((M.R1, M.estadoDePublicacaoDoRegistro, Literal("TEXTO_NAO_REDISTRIBUIDO")))
        self.check(g, False)

    def test_result_without_outcome_or_explicit_restriction_fails(self):
        g = fixture()
        g.add((M.R1, RDF.type, M.Resultado))
        g.add((M.R1, M.identificador, Literal("R1")))
        g.add((M.R1, M.registradoEm, M.F1))
        self.check(g, False)


if __name__ == "__main__":
    unittest.main()
