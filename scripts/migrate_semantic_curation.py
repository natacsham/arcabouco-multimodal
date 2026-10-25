"""Curate the existing catalogue; never promote a historical statement wholesale.

The only new documentary extraction is a point review of CARE section 3.
Research synthesis, scoped executable applications and situated verification
remain separate. This transformation is idempotent and preserves legacy fields.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

VERSION = "1.6.0-rc1"
REVIEW_DATE = "2026-10-25"
ROOT = Path(__file__).resolve().parents[1]
CARE_URL = "https://danielsalber.com/publications/interact1995.pdf"
CARE_CLAIM = "CLM-K40-CARE-COMPLEMENTARITY"
CARE_CRITERION = "CA-CARE-COMPLEMENTARITY"
CARE_ORIGIN = "ORI-CARE-COMPLEMENTARITY"
HAPTIC_APP = "APP-ART-REF-02-HAPTIC-AUDIO"
HAPTIC_OP = "OP-PAD-RETORNO-HAPTICO-RUIDO"
HAPTIC_REL = "REL-PAD-RETORNO-HAPTICO-RUIDO-01"

# The reasons are authored per record, not inferred from a count or a review flag.
KNOWLEDGE_REASONS = {
 "K01": ("CURATION_REQUIRED", "O aumento de robustez do enunciado inteiro excede a sugestão registrada de retorno háptico; somente a proposta delimitada em K40 pode orientar exame situado."),
 "K02": ("SCOPED_REUSE", "A recuperação da última mensagem é uma necessidade registrada; o intervalo observado não se torna um parâmetro universal de repetição."),
 "K03": ("CONDITIONAL_PRINCIPLE", "Variar entrada conforme tarefa não autoriza escolher voz, toque ou outro movimento sem verificar controle disponível e compatibilidade."),
 "K04": ("CONDITIONAL_PRINCIPLE", "Comunicar pré-requisitos e estado organiza o fluxo, mas não estabelece sozinho uma combinação de modalidades nem uma técnica de comunicação."),
 "K05": ("CONDITIONAL_PRINCIPLE", "Coordenação e prioridade de mensagens impõem um cuidado de integração; a presença simultânea de saídas não comprova complementaridade."),
 "K06": ("CURATION_REQUIRED", "A hipótese de reduzir manipulação por controles físicos exige correspondência entre controle, movimento e tarefa antes de orientar aplicação."),
 "K07": ("CONDITIONAL_PRINCIPLE", "A escolha situada fornece dimensões a conferir, não uma regra de seleção automática de modalidade pela deficiência."),
 "K08": ("METHODOLOGICAL_RECORD", "A organização em camadas descreve como conservar fundamentos e casos; não é, por si, fundamento perceptivo de uma ação oferecida."),
 "K09": ("METHODOLOGICAL_RECORD", "A reutilização de experiências depende da preservação da situação; uma decisão anterior não é evidência de eficácia nem uma resposta nova."),
 "K10": ("SCOPED_REUSE", "A descrição da informação relevante pode apoiar acesso não visual; compatibilidade técnica e compreensão continuam verificações diferentes."),
 "K11": ("SCOPED_REUSE", "A mediação na descrição preserva a decisão sobre relevância do conteúdo; não autoriza presumir que toda pessoa solicitante seja professora."),
 "K12": ("CONDITIONAL_PRINCIPLE", "A comunicabilidade da ferramenta de adaptação é condição do trabalho do mediador, não prova de que uma transformação de conteúdo esteja correta."),
 "K13": ("METHODOLOGICAL_RECORD", "O resultado de conformidade técnica deve ficar separado de uso e compreensão; este registro limita alegações, não cria configuração modal."),
 "K14": ("CONDITIONAL_PRINCIPLE", "Contexto, tarefa e tempo delimitam a escolha; faltam papéis informacionais locais para tratar qualquer conjunto de modos como combinação válida."),
 "K15": ("CONDITIONAL_PRINCIPLE", "Entrada alternativa depende do movimento realizável; o precedente não autoriza atribuir movimentos a alguém por diagnóstico."),
 "K16": ("CONDITIONAL_PRINCIPLE", "Viabilidade arquitetural é impedimento ou condição de transferência, não evidência de acesso de uma pessoa a um dispositivo."),
 "K17": ("SCOPED_REUSE", "A síntese da persona sustenta atribuição de funções e organização entre formatos; ganhos gerais de foco e aprendizagem não foram demonstrados aqui."),
 "K18": ("CONDITIONAL_PRINCIPLE", "A trajetória da persona relaciona sistemas e continuidade; a mesma experiência e as mesmas ferramentas não são atribuídas a outra pessoa."),
 "K19": ("SCOPED_REUSE", "O alerta sobre competição entre formatos delimita multiplicidade; não fornece limite quantitativo de sobrecarga para cada participante."),
 "K20": ("CURATION_REQUIRED", "Conforto sensorial é relevante, mas o contrato MF-05 permanece proposto e sem autorização para inferir preferência individual."),
 "K21": ("CONDITIONAL_PRINCIPLE", "Interdependência entre ambiente e dispositivo orienta conferência de viabilidade; não comprova autonomia ou desempenho para uma nova pessoa."),
 "K22": ("METHODOLOGICAL_RECORD", "A avaliação de personas orienta explicitar tarefas e limites, sem converter a persona em perfil clínico ou premissa universal."),
 "K23": ("METHODOLOGICAL_RECORD", "Agrupar normas e preservar origem descreve a construção dos critérios; cada aplicação ainda exige o item documental exato."),
 "K24": ("METHODOLOGICAL_RECORD", "O estudo contextualiza critérios em tarefas e tecnologias; o nome do ambiente avaliado não é condição de recuperação."),
 "K25": ("CURATION_REQUIRED", "A composição ampla de voz, áudio e ajustes visuais precisa ser decomposta em funções e apoios específicos, sem exigir todas as modalidades."),
 "K26": ("SCOPED_REUSE", "Alternativas perceptivas dependem da informação sonora ou visual presente; legenda e descrição não são intercambiáveis por terem o mesmo recurso audiovisual."),
 "K27": ("CURATION_REQUIRED", "A formulação sobre apoio cognitivo é ampla e não autoriza uma instrução genérica para qualquer tarefa de aprendizagem."),
 "K28": ("SCOPED_REUSE", "Rótulos, erros e feedback sustentam revisão do fluxo; apoio ao feedback não autoriza inferir eficácia de jogo ou aprendizagem."),
 "K29": ("SCOPED_REUSE", "Alternativas de expressão preservam escolha e acesso próprio; Libras, leitura e produção oral não são habilidades presumidas."),
 "K30": ("TRANSFER_LIMIT", "Arquitetura e maturidade técnica limitam transferir estratégias; este limite deve acompanhar, não substituir, fundamento da ação."),
 "K31": ("CURATION_REQUIRED", "A percepção elicitada de interesse não prova engajamento causado por recurso; preserve o relato e não promova o efeito inteiro."),
 "K32": ("CONTEXTUAL_PRINCIPLE", "Condições levantadas na elicitação orientam perguntas e acompanhamento; não são observações confirmadas para um novo caso."),
 "K33": ("METHODOLOGICAL_RECORD", "As expectativas sobre uma orientação útil definem sua apresentação e limites; não validam seu efeito nem o raciocínio do motor."),
 "K34": ("CONDITIONAL_PRINCIPLE", "Relacionar condição funcional e tarefa impede prescrição por diagnóstico; não supre capacidades ou recursos ainda desconhecidos."),
 "K35": ("SCOPED_REUSE", "A mediação documentada sustenta distribuição situada de responsabilidades; a divisão específica professora-estudante-colegas não é universal."),
 "K36": ("SCOPED_REUSE", "As parcelas documentadas autorizam examinar alternativas perceptivas do vídeo; duração curta, pergunta introdutória e valor pedagógico integral permanecem delimitados."),
 "K37": ("CURATION_REQUIRED", "Consolidação histórica e eficácia de jogo permanecem propostas; feedback explicativo pode ter apoio próprio sem promover o jogo inteiro."),
 "K38": ("SCOPED_REUSE", "Organização, descrição e retomada possuem parcelas localizadas; unidade central, autoria e publicação não são todas autorizadas por uma única ligação."),
 "K39": ("SCOPED_REUSE", "Tarefa, proficiência e dispositivo delimitam uso; possuir o recurso não comprova conseguir operar a configuração."),
 "K40": ("SCOPED_REUSE", "Retomada e sugestão háptica são registros distintos; CARE permite formular uma aplicação condicional com aviso e conteúdo separados, sem eficácia demonstrada."),
 "K41": ("SCOPED_REUSE", "Movimento, compatibilidade e confirmação são condições distintas da entrada alternativa e não podem ser assumidas como pacote."),
 "K42": ("SCOPED_REUSE", "Preservação da finalidade e alternativas perceptivas possuem cláusulas delimitadas; o motor não verifica automaticamente equivalência do conteúdo produzido."),
 "K43": ("SCOPED_REUSE", "Organização e controle de formatos são apoiados por registros; não é permitido derivar benefício cognitivo universal da quantidade ou ordem de modos."),
 "K44": ("SCOPED_REUSE", "Perceptibilidade e recuperabilidade apoiam continuidade; periodicidade, retenção e compreensão continuam verificações próprias."),
 "K45": ("SCOPED_REUSE", "Contextualização sustenta autoria situada; interesse, diagnóstico, transições e engajamento não se confirmam uns aos outros."),
}

ART_REASONS = {
 "ART-TRJ-01": "A trajetória WABlind–Marcia sintetiza necessidades de descrição e mediação; a síntese histórica não autoriza automaticamente um contrato.",
 "ART-TRJ-02": "A trajetória RotaColab–Gustavo preserva mobilidade e continuidade entre recursos; não transfere capacidades da persona ao usuário.",
 "ART-TRJ-03": "A avaliação técnica WABlind–Lidiane informa limites da multiplicidade; não constitui uma mensuração geral de carga cognitiva.",
 "ART-TRJ-04": "A ligação entre dois artefatos e Bruno é trajetória cumulativa; conforto e continuidade ainda precisam de premissas operacionais localizadas.",
 "ART-TRJ-05": "A articulação ACAT/MPD–RotaColab em João explicita interdependência técnica; não é uma integração implementada para outra pessoa.",
 "ART-TRJ-06": "A avaliação das personas orienta refinamento de contexto e requisitos, preservando diferenças entre avaliação e aplicação posterior.",
 "ART-TRJ-07": "Personas e critérios foram empregados em análise de um ambiente educacional; o ambiente nomeado é local de estudo, não chave de decisão.",
 "ART-TRF-01": "Autoria colaborativa é proposta contextualizada; o registro da mediação não autoriza toda divisão de papéis do caso.",
 "ART-TRF-02": "As aplicações verificadas delimitam legenda e descrição pela informação do vídeo, sem promover a hipótese pedagógica inteira de K36.",
 "ART-TRF-03": "A transferência para jogo permanece candidata; a existência de feedback fundamentado não demonstra consolidação de relações pelo jogo.",
 "ART-TRF-04": "As aplicações exatas conectam descrição, organização e retomada da mesma informação; a sequência não é automaticamente complementaridade modal.",
 "ART-TESTE-NAO-CONFIRMADA": "Controle negativo deliberadamente não confirmado; permanece inelegível mesmo se apontar para K38 ou funções válidas.",
 "ART-REF-01": "Condições funcionais e proficiência refinam a aplicabilidade; não descobrem capacidades individuais durante uma consulta.",
 "ART-REF-02": "Ruptura observada, sugestão de participantes e definição CARE são entradas diferentes da proposta condicional aviso–conteúdo recuperável.",
 "ART-REF-03": "Alternativas perceptivas e organização entre formatos refinam preservação do significado; não provam equivalência semântica do produto final.",
 "ART-REF-04": "O registro de contexto e potencialidade delimita autoria; não autoriza generalizar o diagnóstico ou o efeito sobre vínculo e aprendizagem.",
 "ART-REF-05": "Movimento disponível, arquitetura e feedback condicionam entrada alternativa; nenhuma dessas premissas substitui a outra.",
}

MATRIX_REASONS = {
 "MF-01": "Deriva acesso à informação visual por condição relatada; não presume leitor de tela nem ausência total de visão.",
 "MF-02": "Deriva necessidade de examinar operação alternativa; o movimento realizável e o dispositivo precisam de observação própria.",
 "MF-03": "Preserva expressão informada; não deduz preferência por fala, desenho ou imagem a partir de diagnóstico.",
 "MF-04": "Organização e retomada podem ser examinadas sem supor déficit cognitivo; a sequência concreta depende da tarefa.",
 "MF-05": "Permanece proposta: conforto sensorial individual não foi operacionalizado por premissas documentais suficientes.",
 "MF-06": "Coordenação de participação não define sozinha quem ensina, quem prepara ou quem precisa de apoio.",
 "MF-07": "Experiência relatada não comprova domínio desta configuração; a verificação de operação é situada.",
 "MF-08": "Interesse e conhecimento informado podem orientar autoria, mas não implicam compreensão ou engajamento automaticamente.",
 "MF-09": "Mediação é necessidade possível de tarefa e conteúdo, não profissão obrigatória da pessoa solicitante.",
 "MF-10": "Ruído e dispositivo delimitam disponibilidade efetiva; recurso cadastrado não é recurso perceptível e operante.",
 "MF-11": "Deriva alternativa à informação sonora; não presume Libras, leitura fluente ou perda auditiva total.",
}


def index(data, collection):
    return {r['id']: r for r in data[collection]}


def add_unique(rows, value):
    if value not in rows:
        rows.append(value)


def upsert(rows, value):
    if not any(row['id'] == value['id'] for row in rows):
        rows.append(value)


def stamp(row, disposition, reason, **extra):
    previous = row.get('semantic_curation', {})
    snapshot = previous.get('history') or {
        'sha256': hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        'state_fields': {k: copy.deepcopy(v) for k, v in row.items() if k in (
            'status', 'status_revisao', 'foundation_review_status', 'eligibility', 'verification_status',
            'estado_curadoria', 'nivel_confirmacao', 'habilitada_para_decisao', 'classificacao_operacional')},
    }
    row['semantic_curation'] = dict(schema_version=VERSION, review_date=REVIEW_DATE,
        disposition=disposition, reason=reason, history=snapshot, human_evaluation=False,
        whole_statement_promoted=False, review_scope='RECORDED_SCOPE_WITH_EXPLICIT_POINT_REVIEWS', **extra)


def add_care_application(data):
    """Theory authorizes a conditional design analysis, never empirical success."""
    k = index(data, 'knowledge')['K40']
    art = index(data, 'articulations')['ART-REF-02']
    upsert(data['sources'], {'id':'FN-CARE', 'titulo':'Four Easy Pieces for Assessing the Usability of Multimodal Interaction: The CARE Properties',
        'tipo':'FUNDAMENTO_TEORICO_MMI', 'arquivo':None, 'estudo_ids':[], 'status':'SECAO_CONFERIDA_PONTUALMENTE',
        'url':CARE_URL, 'document_url':CARE_URL, 'urls':[CARE_URL], 'url_candidates':[], 'doi':None,
        'edition':'INTERACT 1995', 'document_version':'1995', 'edition_status':'IDENTIFICADA',
        'consulted_at':REVIEW_DATE, 'document_review_date':REVIEW_DATE,
        'access_status':'SECAO_3_CONSULTADA_NO_ORIGINAL', 'document_review_status':'SECAO_3_CONFERIDA_NO_DOCUMENTO',
        'metadata_origin':'FONTE_JA_PRESENTE_NO_PILOTO_V2_CONFERIDA_NESTA_EVOLUCAO',
        'pilot_source_id':'SourceCARE', 'thesis_reference_claimed':False,
        'document_paraphrase':'CARE distingue escolha de uma modalidade, redundância e complementaridade pelo objetivo alcançável e pela coordenação temporal.'})
    upsert(data['excerpts'], {'id':'TD-CARE-COMPLEMENTARITY', 'fonte_id':'FN-CARE', 'pagina':'4',
        'localizacao_publica':'Seção 3, Complementarity; página 4 do PDF de 7 páginas',
        'efeito_no_raciocinio':'DELIMITA_RELACAO_MULTIMODAL', 'natureza':'PARAFRASE_ANALITICA_DE_SECAO_CONFERIDA',
        'classificacao':'TRECHO_DOCUMENTAL', 'status_curadoria':'SECAO_CONFERIDA_PONTUALMENTE',
        'document_url':CARE_URL, 'document_review_status':'CONFERIDA_NO_DOCUMENTO',
        'document_review_date':REVIEW_DATE, 'estado_publicacao':'PARAFRASE_PROPRIA_SEM_TRECHO_LITERAL',
        'document_paraphrase':'Na complementaridade, as modalidades são necessárias conjuntamente para alcançar o objetivo: nenhuma o realiza sozinha. A combinação pode ser sequencial ou paralela dentro de uma janela temporal.'})
    for record in (k, art):
        add_unique(record['fonte_ids'], 'FN-CARE')
        add_unique(record['trecho_ids'], 'TD-CARE-COMPLEMENTARITY')
    upsert(data['contributions'], {'id':'C-K40-CARE', 'articulation_id':art['id'], 'knowledge_id':k['id'],
        'excerpt_id':'TD-CARE-COMPLEMENTARITY', 'statement':'A complementaridade deve declarar um objetivo ao qual cada modalidade contribui sem ser suficiente isoladamente, com coordenação temporal explicitada.',
        'contribution_role':'CONDICAO_TEORICA_DA_COMBINACAO', 'nature':'PARAFRASE_DE_FONTE_PRIMARIA',
        'justification':'Delimita a proposta aviso tátil e conteúdo sonoro; não afirma que CARE tenha avaliado essa configuração ou que qualquer áudio com vibração seja complementar.',
        'verification_status':'CONFERIDA_NO_DOCUMENTO', 'reviewer':'Assistência computacional: conferência pontual da seção 3; sem avaliação humana da aplicação', 'review_date':REVIEW_DATE})
    claim = copy.deepcopy(next(c for c in k['operation_claims'] if c['id']=='CLM-K40-C-K40-02'))
    claim.update(id=CARE_CLAIM, statement='Uma relação complementar requer objetivo conjunto, contribuições não suficientes isoladamente e coordenação temporal; sua adequação à pessoa depende de verificação situada.',
        epistemic_status='DOCUMENTED_SCOPED_THEORETICAL_PROPOSITION', source_ids=['FN-CARE'], excerpt_ids=['TD-CARE-COMPLEMENTARITY'],
        contribution_ids=['C-K40-CARE'], review_basis_ids=[], review_provenance='POINT_REVIEW_CARE_SECTION_3_'+REVIEW_DATE,
        limits=['Fundamento teórico da classificação, não evidência empírica do arranjo háptico-áudio.', 'A atribuição aviso/conteúdo é proposta analítica desta evolução; deve ser confirmada no caso.'])
    claim['support'] = [{'source_id':'FN-CARE', 'excerpt_id':'TD-CARE-COMPLEMENTARITY',
        'support_scope':'Condição formal de complementaridade em relação a objetivo e tempo.',
        'review_status':'CONFERIDA_NO_DOCUMENTO', 'locator':'Seção 3, Complementarity, p. 4 do PDF', 'document_url':CARE_URL,
        # The original migration field describes the earlier record migration;
        # the separate point-review field records this actual document reading.
        'original_document_rechecked_in_this_migration':False,
        'subsequent_point_review':{'date':REVIEW_DATE, 'original_document_consulted':True, 'section':'3', 'method':'WEB_PRIMARY_PDF_TEXT'}}]
    claim['scope']['allow_new_task_with_functional_witness'] = False
    upsert(k['operation_claims'], claim)
    upsert(data['criteria'], {'id':CARE_CRITERION, 'codigo_trabalho':CARE_CRITERION,
        'enunciado':'Classificar uma proposta como complementar somente quando o objetivo conjunto, a parcela necessária de cada modalidade e sua coordenação temporal estiverem explícitos; nenhuma modalidade isolada deve cumprir esse mesmo objetivo no escopo declarado.',
        'natureza':'CRITERIO_ANALITICO_DE_CLASSIFICACAO_MMI', 'conhecimento_ids':['K40'],
        'status_fundamentacao':'FUNDAMENTO_TEORICO_LOCALIZADO_APLICACAO_ANALITICA_CONDICIONAL',
        'origem_mmi_no_catalogo':'CARE_SECAO_3', 'tipo_relacao_mmi':'COMPLEMENTARITY',
        'justificativa_fundamentacao':'Operacionalização analítica da definição CARE; o critério classifica a relação proposta e não afirma benefício empírico, conformidade normativa ou aprovação da autora.',
        'limites':['Não pertence ao conjunto histórico de 88 critérios.',
            'Não é requisito WCAG ou ABNT e não prescreve áudio ou vibração universalmente.',
            'A suficiência conjunta e a adequação à pessoa precisam de confirmação situada; o resultado é proposta, não efeito observado.'],
        'introduced_in':VERSION, 'document_review_date':REVIEW_DATE, 'human_evaluation':False})
    upsert(data['criterion_origins'], {'id':CARE_ORIGIN,'criterio_id':CARE_CRITERION,
        'codigo_trabalho':CARE_CRITERION,'fonte_id':'FN-CARE','fonte_item':'CARE — Complementarity',
        'trecho_id':'TD-CARE-COMPLEMENTARITY','status_localizacao':'SECAO_3_CONFERIDA_NO_ORIGINAL',
        'estado_publicacao':'PARAFRASE_ANALITICA_SEM_TRECHO_LITERAL','localizacao_publica':'Seção 3, Complementarity, p. 4 do PDF',
        'document_url':CARE_URL,'document_review_date':REVIEW_DATE,
        'natureza':'ORIGEM_TEORICA_DE_CRITERIO_ANALITICO','introduced_in':VERSION,
        'limit':'O critério operacional é síntese analítica desta evolução, não item normativo nem avaliação empírica.'})
    app = {'id':HAPTIC_APP, 'status':'GROUNDED_ANALYTICAL_APPLICATION',
        'premises':[{'knowledge_id':'K40', 'claim_id':cid, 'contribution_ids':[cc]} for cid,cc in (
            ('CLM-K40-C-K40-01','C-K40-01'), ('CLM-K40-C-K40-02','C-K40-02'), (CARE_CLAIM,'C-K40-CARE'))],
        'criterion_support':[{'criterion_id':CARE_CRITERION,'origin_ids':[CARE_ORIGIN]}],
        'analytical_operation':'Distinguir a perda da mensagem da percepção do aviso; relacionar a sugestão háptica registrada à recuperabilidade e ao critério teórico CARE. Propor uma alocação em que o tato anuncia disponibilidade e o áudio recuperável fornece o conteúdo da mesma orientação.',
        'result':'Quando a pessoa precisa de aviso tátil e consegue recuperar a mensagem sonora vinculada, examinar a combinação como uma proposta complementar: o aviso não transmite o conteúdo e o áudio não cumpre o papel tátil requerido naquele contexto.',
        'authorized_operation_ids':[HAPTIC_OP], 'authorized_relation_ids':[HAPTIC_REL], 'authorized_requirement_ids':[],
        'function_ids':['FUN-FEEDBACK-PERCEPTIVEL','FUN-MANTER-INFORMACAO-RECUPERAVEL'],
        'conditions':['A necessidade de um aviso tátil adicional está confirmada para esta tarefa, não apenas inferida da presença de ruído.',
            'A pessoa percebe e distingue o sinal tátil, consegue ouvir o conteúdo e acionar a repetição da mesma mensagem.',
            'O aviso e a mensagem referem-se ao mesmo evento; sua ligação e a janela de recuperação são estabelecidas com a pessoa.'],
        'limits':['Proposta de projeto, não configuração observada nem eficácia avaliada nesta migração.',
            'A sugestão histórica foi conferida no registro; o PDF original do estudo não foi relido nesta revisão.',
            'Se o áudio já realiza sozinho todo o objetivo ou se o tato não é necessário, não afirmar complementaridade CARE.',
            'A vibração não substitui instrução verbal complexa, e áudio inacessível impede a combinação proposta.',
            'O critério CA88 permanece uma associação delimitada do registro anterior; CARE não é a origem normativa de CA88.'],
        'depends_on_application_ids':[], 'empirical_effect_authorized':False,
        'review':{'date':REVIEW_DATE, 'scope':'EXISTING_DESIGN_PRECEDENT_AND_PRIMARY_CARE_POINT_REVIEW',
            'human_evaluation':False, 'whole_historical_claim_promoted':False,
            'note':'A proposta analítica é explícita; a conferência de CARE não transforma a sugestão dos participantes em resultado empírico.'}}
    upsert(art.setdefault('operational_applications',[]), app)
    existing_app=next(a for a in art['operational_applications'] if a['id']==HAPTIC_APP)
    if not existing_app.get('criterion_support'):
        existing_app['criterion_support'] = copy.deepcopy(app['criterion_support'])
        existing_app['criterion_curation'] = {'date':REVIEW_DATE, 'previous_support':[],
            'reason':'Explicitada a origem teórica exata do critério analítico exigido pela aplicação; CA88 não é usado para provar complementaridade.',
            'human_approval':False}
    op = next(c['operation_contract'] for c in data['decision_components'] if c.get('operation_contract',{}).get('id')==HAPTIC_OP)
    op.setdefault('semantic_change_history', {'previous_analytical_application_ids':op.get('analytical_application_ids',[]),
        'previous_selected_representation_ids':op.get('selected_representation_ids',[]), 'date':REVIEW_DATE})
    op['analytical_application_ids'] = [HAPTIC_APP]
    op['selected_representation_ids'] = ['MOD-HAPTICO','MOD-AUDIO']
    rel = op['relations'][0]
    rel['analytical_application_ids'] = [HAPTIC_APP]
    for fact in [
        {'id':HAPTIC_OP+':tactile_notice_needed', 'label':'Nesta tarefa, a pessoa precisa de um aviso tátil adicional e consegue distingui-lo?'},
        {'id':HAPTIC_OP+':same_event_binding', 'label':'O aviso tátil identifica a mesma orientação sonora, que pode ser retomada no momento necessário?'}]:
        upsert(op.setdefault('requires_facts',[]), fact)
    rel['goal'] = 'Perceber o aviso tátil necessário e recuperar o conteúdo da mesma orientação sonora.'
    rel['required_information'] = ['DISPONIBILIDADE_DA_MENSAGEM','CONTEUDO_DA_ORIENTACAO']
    rel['information_roles'] = [
        {'representation_id':'MOD-HAPTICO','function_id':'FUN-FEEDBACK-PERCEPTIVEL','information_component':'DISPONIBILIDADE_DA_MENSAGEM',
         'role':'Anunciar a disponibilidade da orientação; não codifica sua instrução verbal.', 'alone_sufficient_for_goal':False,
         'claim_ids':['CLM-K40-C-K40-02',CARE_CLAIM]},
        {'representation_id':'MOD-AUDIO','function_id':'FUN-MANTER-INFORMACAO-RECUPERAVEL','information_component':'CONTEUDO_DA_ORIENTACAO',
         'role':'Fornecer conteúdo recuperável do evento anunciado; não realiza o aviso tátil exigido neste arranjo.', 'alone_sufficient_for_goal':False,
         'claim_ids':['CLM-K40-C-K40-01',CARE_CLAIM]}]
    rel['each_alone_sufficient'] = {'MOD-HAPTICO':False,'MOD-AUDIO':False}
    rel['joint_sufficiency_scope'] = 'Somente para o objetivo composto confirmado e a alocação proposta aviso/conteúdo; não equivale a comprovar compreensão ou segurança da navegação.'
    rel['temporal_contract'] = {'organization':'SEQUENTIAL_OR_CO_TEMPORAL_WITH_BOUND_EVENT', 'window_requirement':'A janela liga o aviso ao acesso à mesma mensagem; duração a confirmar no contexto.',
        'verification_required':True, 'binding_status':'PROPOSED_ALLOCATION_REQUIRES_SITUATED_CONFIRMATION'}


def contracts(data):
    for component in data['decision_components']:
        op = component.get('operation_contract')
        if op:
            yield op, op
            for variant in op.get('operation_variants',[]):
                yield variant, dict(op, **variant)


def add_information_roles(record, effective, applications):
    for rel in record.get('relations',[]):
        if rel['id'] == HAPTIC_REL:
            continue
        claim_ids = sorted({s['claim_id'] for s in rel.get('claim_support',[])})
        if not claim_ids:
            claim_ids = sorted({p['claim_id'] for aid in rel.get('analytical_application_ids',[])
                                for p in applications[aid]['premises']})
        source = rel.get('from_representation_ids',[])
        target = rel.get('to_representation_ids',[])
        funcs = rel.get('from_function_ids',[])+rel.get('to_function_ids',[])
        component = ('INFORMACAO_SONORA_RELEVANTE' if 'CAPTIONS' in rel['id'] else
                     'INFORMACAO_VISUAL_RELEVANTE' if any(r in source for r in ('MOD-IMAGEM','MOD-DESENHO','MOD-VIDEO')) else
                     'CONTEUDO_A_RETOMAR' if rel['kind']=='SEQUENTIAL' else 'CONTRIBUICAO_AUTORAL_INFORMADA')
        rel['required_information'] = [component]
        rel['information_roles'] = []
        for side, reps, functions in [('SOURCE',source,rel.get('from_function_ids',funcs)),('TARGET',target,rel.get('to_function_ids',funcs))]:
            for rep in reps:
                rel['information_roles'].append({'representation_id':rep, 'function_id':functions[0],
                    'information_component':component,
                    'role':('Apresentar a informação de partida que delimita a transformação.' if side=='SOURCE' else
                            'Disponibilizar a mesma informação relevante na representação de destino; preservação deve ser conferida.'),
                    'role_side':side, 'alone_sufficient_for_goal':None, 'claim_ids':claim_ids})
        rel['each_alone_sufficient'] = {r:None for r in source+target}
        rel['goal'] = ('Disponibilizar para organização o conteúdo descrito da mesma situação.' if rel['kind']=='SEQUENTIAL' else
                       'Oferecer acesso à informação relevante por uma representação de destino adequada à pessoa.')
        rel['joint_sufficiency_scope'] = ('Encadeamento de operações sobre o mesmo conteúdo; não é complementaridade CARE.' if rel['kind']=='SEQUENTIAL' else
            'Alternativa delimitada à informação indicada; não comprova equivalência integral nem exige uso simultâneo das representações.')
        rel['temporal_contract'] = {'organization':('OUTPUT_THEN_INPUT' if rel['kind']=='SEQUENTIAL' else
            'SYNCHRONIZED_WITH_RELEVANT_MEDIA' if any(x in rel['id'] for x in ('CAPTIONS','AUDIO_DESCRIPTION')) else 'NO_SIMULTANEITY_REQUIRED'),
            'verification_required':True, 'window_requirement':'Conferir a ligação com a informação de origem e a possibilidade de consulta no momento necessário.'}


def migrate(original):
    data = copy.deepcopy(original)
    if set(KNOWLEDGE_REASONS) != set(index(data,'knowledge')) or set(ART_REASONS) != set(index(data,'articulations')):
        raise ValueError('Catalogue changed: review each knowledge/articulation before migration.')
    # Preserve the pre-change fingerprint before adding the new point review.
    for row in data['knowledge']:
        disposition, reason = KNOWLEDGE_REASONS[row['id']]
        stamp(row, disposition, reason)
    for row in data['articulations']:
        stamp(row, 'REVIEWED_REGISTER_NOT_BLANKET_AUTHORIZATION', ART_REASONS[row['id']])
    add_care_application(data)
    contributions = index(data,'contributions')
    excerpts = index(data,'excerpts')
    for row in data['contributions']:
        stamp(row, 'DOCUMENT_LOCATED' if row['verification_status']=='CONFERIDA_NO_DOCUMENTO' else
            'RECORDED_EXTRACTION_ONLY' if row['verification_status']=='CONFERIDA_NO_REGISTRO' else 'PENDING',
            row['justification'], excerpt_id=row['excerpt_id'], articulation_id=row['articulation_id'], knowledge_id=row['knowledge_id'])
    for row in data['articulations']:
        located = [c for c in contributions.values() if c['articulation_id']==row['id']]
        applications = row.get('operational_applications',[])
        row['intellectual_synthesis'] = {
            'status':'RETROSPECTIVE_EXPLICIT_ANALYTICAL_RECORD', 'authorship':'Explicitação assistida dos registros da pesquisa; não reconstrução comprovada do pensamento original da autora.',
            'premises':[{'contribution_id':c['id'], 'knowledge_id':c['knowledge_id'], 'excerpt_id':c['excerpt_id'],
                        'source_id':excerpts[c['excerpt_id']]['fonte_id'], 'content':c['statement'],
                        'contribution_role':c['contribution_role'], 'verification_status':c['verification_status']} for c in located],
            'historical_input_ids':row.get('conteudo_entrada_ids',[]),
            'input_knowledge_ids':row.get('conhecimento_entrada_ids',[]),
            'operation':row.get('operation_explanation') or ART_REASONS[row['id']],
            'resulting_understanding':row.get('added_understanding') or ART_REASONS[row['id']],
            'conditional_formulation':{'when':row.get('condicao'), 'understanding':row.get('added_understanding') or ART_REASONS[row['id']], 'limit':row.get('limite')},
            'conditions':[row['condicao']] if row.get('condicao') else [],
            'limits':[row.get('limite',''), ART_REASONS[row['id']]],
            'result_knowledge_ids':row.get('conhecimento_resultante_ids',[]),
            'authorized_application_ids':[a['id'] for a in applications],
            'operational_targets':sorted({t for a in applications for field in ('authorized_operation_ids','authorized_relation_ids','authorized_requirement_ids') for t in a.get(field,[])}),
            'missing_localized_premises':not bool(located),
            'runtime_creates_this_synthesis':False, 'historical_enabled_flag_is_authorization':False,
            'human_evaluation':False}
        row['semantic_curation']['authorized_application_ids'] = [a['id'] for a in applications]
    for row in data['knowledge']:
        row['semantic_curation']['eligible_claim_ids'] = [c['id'] for c in row.get('operation_claims',[]) if c.get('eligibility')=='DOCUMENTED_OPERATIONAL_CLAIM']
        row['semantic_curation']['pending_claim_ids'] = [c['id'] for c in row.get('operation_claims',[]) if c.get('eligibility')!='DOCUMENTED_OPERATIONAL_CLAIM']
        row['semantic_curation']['localized_contribution_ids'] = [c['id'] for c in contributions.values() if c['knowledge_id']==row['id']]
        row['semantic_curation']['whole_statement_eligibility'] = 'NOT_INFERRED_FROM_SCOPED_CLAIMS'
    for row in data['functional_matrix']:
        stamp(row, 'PROPOSED_NOT_AUTHORIZED' if row['id']=='MF-05' else 'SCOPED_REQUIREMENT_ONLY', MATRIX_REASONS[row['id']],
            claim_ids=row.get('inference_contract',{}).get('claim_ids',[]))
    applications = {a['id']:a for art in data['articulations'] for a in art.get('operational_applications',[])}
    for row, effective in contracts(data):
        stamp(row, 'SCOPED_CONTRACT_WITH_SITUATED_GATES',
            'Contrato '+row['id']+': '+effective['action']+' Sua autorização limita-se aos apoios exatos; recursos, acesso e integração continuam sujeitos às verificações declaradas.',
            claim_ids=sorted({s['claim_id'] for s in effective.get('claim_support',[])}))
        add_information_roles(row,effective,applications)
    old_version = data['metadata'].get('version')
    if old_version != VERSION:
        data['metadata']['semantic_curation_previous_metadata'] = copy.deepcopy(data['metadata'])
    data['metadata'].update(version=VERSION, generated_at=REVIEW_DATE, derived_from_version='1.5.0-rc3',
        title='Base pública do Arcabouço Multimodal — articulação semântica 1.6.0-rc1', interface_version='AMADO-web-'+VERSION,
        migration_note='Curadoria explícita de todos os registros, sínteses condicionais e contribuições informacionais por modalidade. Conferência pontual CARE; sem promover enunciados históricos nem alegar avaliação humana.')
    data['metadata']['semantic_curation_counts'] = {key:len(data[key]) for key in ('knowledge','articulations','contributions','functional_matrix')}
    data['metadata']['criterion_origin_count'] = len(data['criterion_origins'])
    data['metadata']['criteria_inventory'] = {'historical_criteria':88,'analytical_criteria_added':1,
        'historical_origins':416,'analytical_origins_added':1,'criterion_ids_added':[CARE_CRITERION]}
    validate_semantic_curation(data)
    return data


def validate_semantic_curation(data):
    applications = {a['id']:a for art in data['articulations'] for a in art.get('operational_applications',[])}
    for key in ('knowledge','articulations','contributions','functional_matrix'):
        for row in data[key]:
            c = row.get('semantic_curation',{})
            if not all(c.get(f) for f in ('disposition','reason','history')) or c.get('whole_statement_promoted') is not False:
                raise ValueError('Incomplete scoped curation: '+row['id'])
    for row in data['articulations']:
        synthesis = row.get('intellectual_synthesis',{})
        if not synthesis.get('operation') or not synthesis.get('resulting_understanding') or synthesis.get('runtime_creates_this_synthesis') is not False:
            raise ValueError('Incomplete intellectual synthesis: '+row['id'])
    for row, effective in contracts(data):
        for rel in row.get('relations',[]):
            roles = rel.get('information_roles',[])
            represented = {r.get('information_component') for r in roles}
            if not roles or not set(rel.get('required_information',[])) <= represented:
                raise ValueError('Uncovered information role: '+rel['id'])
            admitted = {s['claim_id'] for s in rel.get('claim_support',[])}
            admitted.update(p['claim_id'] for aid in rel.get('analytical_application_ids',[])
                            for p in applications[aid]['premises'])
            for role in roles:
                if (not role.get('claim_ids') or not set(role['claim_ids']) <= admitted
                    or role.get('representation_id') not in rel.get('from_representation_ids',[])+rel.get('to_representation_ids',[])
                    or role.get('function_id') not in rel.get('from_function_ids',[])+rel.get('to_function_ids',[])):
                    raise ValueError('Unfounded modal information role: '+rel['id'])
            if rel['kind']=='COMPLEMENTARITY':
                if len(represented)<2 or any(r.get('alone_sufficient_for_goal') is not False for r in roles):
                    raise ValueError('Invalid complementary information allocation: '+rel['id'])
                if not {r['representation_id'] for r in roles} <= set(effective.get('selected_representation_ids',[])):
                    raise ValueError('Complementary contribution not selected: '+rel['id'])
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--path',type=Path,default=ROOT/'data'/'knowledge-base.json')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    original=json.loads(args.path.read_text(encoding='utf-8'))
    result=migrate(original)
    if args.check:
        if result != original:
            raise SystemExit('Semantic curation is not current.')
    else:
        args.path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result['metadata']['semantic_curation_counts'],ensure_ascii=False))
