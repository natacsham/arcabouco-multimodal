"""Reproducible, scoped curation of the existing RC1 records for RC2.

The JSON remains the canonical curated record. This migration is not run while
serving a case and contains no test narratives or scenario-dependent recipes.
Old knowledge claims and their review states are deliberately preserved.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
DATE = '2026-10-21'
VERSION = '1.5.0-rc2'


def revise(data):
    k = {r['id']: r for r in data['knowledge']}
    arts = {r['id']: r for r in data['articulations']}
    excerpts = {r['id']: r for r in data['excerpts']}
    ops = {r['id']: r['operation_contract'] for r in data['decision_components']
           if r.get('operation_contract')}
    # A new scoped extraction from an already catalogued source, not promotion
    # of the broad historical K38 statement or any additional publication.
    cid = 'C-K38-MMI-NAV'
    statement = 'MMI 1.9 permite explicitar o fluxo de navegação da aplicação.'
    contribution = dict(id=cid, articulation_id='ART-TRF-04', knowledge_id='K38',
        excerpt_id='TD-ORI-0012', statement=statement,
        contribution_role='COORDENACAO_DO_FLUXO', nature='PARAFRASE_DE_SECAO_ORIGINAL',
        justification='Delimita organização do percurso; não prescreve texto curto, memória ou benefício de aprendizagem.',
        verification_status='CONFERIDA_NO_DOCUMENTO',
        reviewer='Assistência computacional; consulta pontual à seção 1.9 original; sem avaliação humana',
        review_date=DATE)
    data['contributions'] = [x for x in data['contributions'] if x['id'] != cid] + [contribution]
    for record in (k['K38'], arts['ART-TRF-04']):
        for field, value in [('fonte_ids', 'FN-MMI'), ('trecho_ids', 'TD-ORI-0012')]:
            if value not in record[field]:
                record[field].append(value)
    for tid in ['TD-ORI-0012', 'TD-ORI-0014', 'TD-ORI-0001', 'TD-ORI-0148', 'TD-ORI-0090']:
        excerpts[tid]['rc2_point_review'] = {
            'date': DATE, 'scope': 'SECAO_ORIGINAL_IDENTIFICADA',
            'url': excerpts[tid]['document_url'],
            'human_evaluation': False, 'all_source_contents_reviewed': False}
    # Copying the record envelope preserves the strict exact-pair contract.
    claim = deepcopy(next(c for c in k['K38']['operation_claims'] if c['id'] == 'CLM-K38-C-K38-02'))
    claim.update(id='CLM-K38-MMI-NAV', statement=statement,
        function_ids=['FUN-ORGANIZAR-CONTEUDO'], source_ids=['FN-MMI'],
        excerpt_ids=['TD-ORI-0012'], contribution_ids=[cid],
        epistemic_status='DOCUMENTED_SCOPED_MMI_REQUIREMENT',
        review_provenance='POINT_SOURCE_REVIEW_2026-10-21_NOT_HUMAN_EVALUATION',
        limits=['MMI é uma Note sobre requisitos das especificações; não certifica aplicações nem prescreve um recurso didático.'], pending_items=[])
    claim['scope']['function_ids'] = claim['function_ids']
    claim['support'] = [dict(source_id='FN-MMI', excerpt_id='TD-ORI-0012',
        support_scope=statement, review_status='CONFERIDO_NA_SECAO_ORIGINAL',
        locator='1.9 Navigation specification, MMI-G16',
        document_url=excerpts['TD-ORI-0012']['document_url'],
        original_document_rechecked_in_this_migration=False,
        subsequent_point_review=deepcopy(excerpts['TD-ORI-0012']['rc2_point_review']))]
    k['K38']['operation_claims'] = [c for c in k['K38']['operation_claims'] if c['id'] != claim['id']] + [claim]
    # Existing scoped WCAG claims become exact contribution records, not new
    # blanket approvals of K42. Their primary sections were checked above.
    for tid, art_id, role in [
            ('TD-ORI-0001','ART-REF-03','FINALIDADE_DA_ALTERNATIVA_TEXTUAL'),
            ('TD-ORI-0148','ART-REF-03','ACESSO_A_PARCELA_SONORA'),
            ('TD-ORI-0090','ART-REF-03','ACESSO_A_PARCELA_VISUAL')]:
        claim = next(c for c in k['K42']['operation_claims'] if c['id']=='CLM-K42-'+tid)
        cid = 'C-K42-WCAG-' + tid.removeprefix('TD-ORI-')
        contribution = dict(id=cid, articulation_id=art_id, knowledge_id='K42',
            excerpt_id=tid, statement=claim['statement'], contribution_role=role,
            nature='PARAFRASE_DE_SECAO_ORIGINAL',
            justification='Parcela específica da WCAG vinculada à afirmação existente; não transfere a exigência para toda mídia nem certifica o resultado.',
            verification_status='CONFERIDA_NO_DOCUMENTO',
            reviewer='Assistência computacional; consulta pontual à seção original; sem avaliação humana',
            review_date=DATE)
        data['contributions']=[x for x in data['contributions'] if x['id']!=cid]+[contribution]
        claim['contribution_ids']=list(dict.fromkeys(claim.get('contribution_ids',[])+[cid]))
        claim['subsequent_point_review']=deepcopy(excerpts[tid]['rc2_point_review'])
        for record in (k['K42'],arts[art_id]):
            for field,value in [('fonte_ids','FN-WCAG'),('trecho_ids',tid)]:
                if value not in record[field]:
                    record[field].append(value)
    claims = {c['id']: (kid, c) for kid, row in k.items() for c in row.get('operation_claims', [])}

    def support(claim_id, criterion=None, origins=(), explanation='Parcela delimitada mobilizada nesta aplicação analítica.'):
        kid, c = claims[claim_id]
        return dict(knowledge_id=kid, claim_id=claim_id, criterion_id=criterion,
            origin_ids=list(origins), justification=explanation, claim_scope_limit=c['limits'],
            semantic_pair_review=dict(status='CONFERIDO_NO_REGISTRO',
                scope='SCOPED_ANALYTICAL_APPLICATION' if criterion else 'CONTEXTUAL_CONTRIBUTION_ONLY',
                claim_excerpt_ids=c['excerpt_ids'],
                origin_excerpt_ids=[next(o['trecho_id'] for o in data['criterion_origins'] if o['id']==oid) for oid in origins],
                original_document_rechecked=False,
                limit='Conferência desta aplicação; mantém o estado documental específico de cada premissa.'))

    def application(art_id, suffix, op, premises, criterion_support, operation, result,
                    relation_ids=(), function_ids=None, conditions=(), limits=()):
        app_id = 'APP-' + art_id + '-' + suffix
        app = dict(id=app_id, status='GROUNDED_ANALYTICAL_APPLICATION',
            premises=[dict(knowledge_id=claims[p][0], claim_id=p,
                           contribution_ids=claims[p][1].get('contribution_ids', [])) for p in premises],
            criterion_support=criterion_support, analytical_operation=operation, result=result,
            authorized_operation_ids=[op['id']], authorized_relation_ids=list(relation_ids),
            function_ids=function_ids or op['function_ids'], conditions=list(conditions),
            limits=list(limits) or list(op['limits']), depends_on_application_ids=[],
            empirical_effect_authorized=False,
            review=dict(date=DATE, scope='EXISTING_RECORDS_AND_POINT_SOURCE_CHECK',
                        human_evaluation=False, whole_historical_claim_promoted=False,
                        note='Síntese de projeto explicitada nesta revisão; os artigos não foram relidos integralmente. A consulta primária limita-se às seções normativas indicadas.'))
        arts[art_id]['operational_applications'] = [x for x in arts[art_id].get('operational_applications', []) if x['id'] != app_id] + [app]
        op['analytical_application_ids'] = [app_id]
        for rel in op.get('relations', []):
            if rel['id'] in relation_ids:
                rel['analytical_application_ids'] = [app_id]
        return app_id

    def phase(op, name, label, phase='verification'):
        return dict(id=op['id'] + ':' + name, label=label, phase=phase)

    # Every contract is reviewed for its operational scope; unknown/candidate
    # claims are never made eligible by the existence of this audit.
    for op in ops.values():
        op['schema_version'] = VERSION
        op['rc2_audit'] = dict(date=DATE, scoped_claim_ids=[s['claim_id'] for s in op['claim_support']],
            result='SCOPED_OPERATION_REVIEW', historical_statement_promoted=False)
        op['independent_support_allowed'] = True
        op['condition_phases'] = [phase(op, 'verify_information',
            'Depois de preparar, conferir com a pessoa se a informação necessária à tarefa permanece disponível e compreensível.')]
        op['historical_conditions'] = op.get('historical_conditions', op.get('conditions', []))
        op['conditions'] = []
    preparation = ['PAD-ORGANIZAR-CONTEUDO-PERSISTENTE', 'PAD-EXPRESSAO-AUTORAL-FALA-AUDIO',
                   'PAD-REPRESENTACAO-VISUAL-EXPLICADA', 'PAD-VIDEO-PROCESSO', 'PAD-CONTEUDO-WEB-EQUIVALENTE']
    for key in preparation:
        op = ops[key]
        op['operation_scope'] = 'PREPARATION_FOR_RECIPIENT'
        op['preparation_responsibility'] = 'A pessoa que prepara ou adapta o material executa a ação; a via de acesso é conferida separadamente para cada destinatário.'
        op['preparation_role_ids'] = ['PAPEL-RESPONSAVEL-ADAPTACAO', 'PAPEL-MEDIADOR', 'PAPEL-PROFESSORA']
        op['resource_requirements']['capability_check_required'] = False
        op['resource_requirements']['all'] = []
        op['resource_requirements']['any'] = [['REC-EDITOR-MULTIMIDIA']]
        op['condition_phases'].insert(0, phase(op, 'produce_resource',
            'Preparar o recurso proposto e conservar a informação identificada como necessária.', 'production'))

    op = ops['PAD-ORGANIZAR-CONTEUDO-PERSISTENTE']
    op['function_ids'] = ['FUN-ORGANIZAR-CONTEUDO', 'FUN-MANTER-INFORMACAO-RECUPERAVEL']
    op['action'] = 'Preparar instruções consultáveis, com a ordem das ações e relações explícitas, para localizar e retomar o ponto necessário.'
    op['selected_representation_ids'] = ['MOD-TEXTO']
    op['output_resource_ids'] = ['REC-ROTEIRO-COLABORATIVO']
    op['requires_facts'] = [dict(id='CanReadText', label='A pessoa consegue acompanhar instruções escritas nesta tarefa?')]
    op['claim_support'] = [support('CLM-K38-C-K38-02'), support('CLM-K43-C-K43-02'),
        support('CLM-K38-MMI-NAV','CA02',['ORI-0012']), support('CLM-K42-C-K42-02','CA02',['ORI-0014'])]
    # Organization alone is not a multimodal relation. The recoverability is
    # a situated design synthesis, not an empirical property of text/personas.
    op['historical_relations'] = op.get('historical_relations', deepcopy(op['relations']))
    op['relations'] = []
    op['limits'] = ['A retomada exige que as instruções permaneçam disponíveis e localizáveis; isso será conferido após a preparação.',
                    'Esta síntese de projeto não demonstra memória, compreensão ou aprendizagem melhores e não exige imagens.',
                    'Organização textual isolada não é apresentada como combinação multimodal.']
    application('ART-TRF-04','ORGANIZAR-RETOMAR',op,
        ['CLM-K38-C-K38-02','CLM-K43-C-K43-02','CLM-K38-MMI-NAV','CLM-K42-C-K42-02'],
        [dict(criterion_id='CA02',origin_ids=['ORI-0012','ORI-0014'])],
        'Relacionar o precedente de organização entre formatos, o limite de competição pela atenção, o fluxo MMI e a preservação da estrutura em texto. A persistência e a localização são condições de projeto, não resultados empíricos dos registros.',
        'Uma versão organizada e consultável pode dar apoio à retomada de uma sequência sem depender exclusivamente de sua apresentação anterior.',
        conditions=['A tarefa tem informação ou etapas identificáveis e requer organização ou retomada.',
                    'A pessoa dispõe de uma forma utilizável de consultar a representação selecionada.',
                    'O material preparado deverá permanecer disponível e permitir localizar a etapa.'])
    op['condition_phases'].append(phase(op,'verify_retrieval','Disponibilizar a instrução e verificar se a pessoa consegue localizar e retomar a etapa necessária.'))

    ops['PAD-EXPRESSAO-AUTORAL-FALA-AUDIO']['output_resource_ids']=['REC-DESCRICAO-TEXTUAL']

    def text_variants(op, app_id, description):
        variants=[]
        for suffix,selected, facts, resources in [
            ('TEXT_VISUAL',['MOD-TEXTO'],['CanReadText'],[]),
            ('TEXT_SCREEN_READER',['MOD-AUDIO'],['UsesScreenReader','AudioUsable'],['REC-LEITOR-DE-TELA','REC-SAIDA-AUDIO'])]:
            rel=deepcopy(op['relations'][0])
            rel['id'] += '-' + suffix
            rel['analytical_application_ids']=[app_id]
            rel['verification_phase']='verification'
            rel['to_representation_ids']=selected
            rel['preserves']=description
            variants.append(dict(id=op['id']+'-'+suffix, parent_operation_id=op['id'],
                selected_representation_ids=selected, recipient_resource_ids=resources,
                output_spec=[dict(representation_id=selected[0],meaning_unit='INFORMACAO_ESSENCIAL_DA_TAREFA',required=True)],
                stored_representation_ids=['MOD-TEXTO'],
                presentation_transformation=('Texto estruturado apresentado visualmente.' if suffix=='TEXT_VISUAL'
                    else 'Descrição armazenada em texto estruturado e apresentada em áudio pelo leitor de tela; a reprodução não comprova compreensão.'),
                requires_facts=[dict(id=f,label={'CanReadText':'A pessoa consegue acompanhar o texto apresentado visualmente?',
                    'UsesScreenReader':'A pessoa utiliza leitor de tela para acessar o conteúdo textual?',
                    'AudioUsable':'A pessoa pode ouvir a leitura neste ambiente?'}[f]) for f in facts],
                analytical_application_ids=[app_id], relations=[rel]))
        op['operation_variants']=variants
        app=next(a for art in arts.values() for a in art.get('operational_applications',[]) if a['id']==app_id)
        app['authorized_operation_ids'] += [v['id'] for v in variants]
        app['authorized_relation_ids'] += [r['id'] for v in variants for r in v['relations']]

    for key in ['PAD-REPRESENTACAO-VISUAL-EXPLICADA','PAD-CONTEUDO-WEB-EQUIVALENTE']:
        op=ops[key]
        op['output_resource_ids']=['REC-DESCRICAO-TEXTUAL']
        op['representation_ids'] = list(dict.fromkeys(op['representation_ids']+['MOD-AUDIO']))
        op['claim_support'] = [support('CLM-K38-C-K38-01'), support('CLM-K42-C-K42-01'),
            support('CLM-K42-TD-ORI-0001','CA01',['ORI-0001']),support('CLM-K42-C-K42-02','CA02',['ORI-0014']),
            support('CLM-K38-MMI-NAV','CA02',['ORI-0012'])]
        op['relations'][0]['claim_support']=deepcopy(op['claim_support'])
        app_id=application('ART-TRF-04', key.removeprefix('PAD-'),op,
            [s['claim_id'] for s in op['claim_support']],
            [dict(criterion_id='CA01',origin_ids=['ORI-0001']),dict(criterion_id='CA02',origin_ids=['ORI-0012','ORI-0014'])],
            'Relacionar a descrição que conserva a função da informação, o limite do mero uso de leitor de tela, a preservação de estrutura e o fluxo de consulta. Distinguir conteúdo textual armazenado da via perceptiva usada pela pessoa.',
            'Preparar uma descrição ligada à informação visual e às suas relações; a apresentação será visual ou pelo leitor de tela, conforme a condição individual.',
            relation_ids=[op['relations'][0]['id']], conditions=['Há conteúdo visual relevante que precisa ser representado por outra via.'])
        text_variants(op,app_id,'Informação relevante do conteúdo visual, suas relações e sua finalidade na tarefa; a equivalência será conferida, não presumida.')

    op=ops['PAD-VIDEO-PROCESSO']
    if not op['relations']:
        op['relations']=deepcopy(op['historical_relations'])
    op['resource_requirements']['any']=[['REC-EDITOR-MULTIMIDIA']]
    op['output_resource_ids']=['REC-LEGENDAS','REC-AUDIODESCRICAO']
    op['operation_variants']=[]
    for suffix,output,facts,claim_id,criterion,oid,res,content,action in [
        ('CAPTIONS','MOD-TEXTO',['CanReadText'],'CLM-K42-TD-ORI-0148','CA17','ORI-0148','REC-LEGENDAS',
         'A informação sonora relevante do vídeo, incluindo falas e sons necessários.','Preparar legendas sincronizadas para as falas e os sons necessários do vídeo; conferir sua leitura durante a reprodução.'),
        ('AUDIO_DESCRIPTION','MOD-AUDIO',['AudioUsable'],'CLM-K42-TD-ORI-0090','CA05','ORI-0090','REC-AUDIODESCRICAO',
         'A informação visual relevante que não está explicada na trilha sonora.','Descrever em áudio as informações visuais relevantes que não estão explicadas na fala; coordenar a descrição com os demais sons.')]:
        rel=deepcopy(op['relations'][0]); rel['id']+='-'+suffix
        rel['to_representation_ids']=[output]; rel['preserves']=content
        rel['from_representation_ids']=['MOD-VIDEO']
        rel['meaning_unit']=content
        rel['temporal']='SYNCHRONIZED_WITH_RELEVANT_CONTENT'
        rel['verification_phase']='verification'
        supports=[support('CLM-K36-C-K36-01'), support(claim_id,criterion,[oid]),support('CLM-K38-MMI-NAV','CA02',['ORI-0012'])]
        rel['claim_support']=deepcopy(supports)
        variant=dict(id=op['id']+'-'+suffix,parent_operation_id=op['id'],function_ids=op['function_ids'],
            action=action, selected_representation_ids=[output],
            input_requirements=[dict(representation_id='MOD-VIDEO',meaning_unit=content,
                content_component=('SONORO' if suffix=='CAPTIONS' else 'VISUAL'),
                required=True,operator='ANY_IN_GROUP')],
            output_spec=[dict(representation_id=output,meaning_unit=content,required=True)],
            output_resource_ids=[res],claim_support=supports,relations=[rel],
            recipient_resource_ids=['REC-REPRODUTOR-VIDEO']+(['REC-SAIDA-AUDIO'] if output=='MOD-AUDIO' else []),
            requires_facts=[dict(id=f,label={'CanReadText':'A pessoa consegue acompanhar as legendas?',
                'AudioUsable':'O áudio é utilizável para esta pessoa neste ambiente?'}[f]) for f in facts])
        app_id=application('ART-TRF-02',suffix,variant,[s['claim_id'] for s in supports],
            [dict(criterion_id=criterion,origin_ids=[oid]),dict(criterion_id='CA02',origin_ids=['ORI-0012'])],
            'Relacionar o precedente de acessibilidade de mídia à cláusula específica de acesso e à organização do fluxo. Separar a parcela sonora da visual e selecionar uma via utilizável pelo destinatário.',
            content+' A alternativa não substitui automaticamente as demais informações do vídeo.',
            relation_ids=[rel['id']],conditions=['Vídeo pré-gravado pertinente à tarefa; não transmissão ao vivo.'],
            limits=['Não garante acesso ao vídeo completo; é preciso conferir a outra parcela informacional.',
                    'Não infere domínio de Libras, leitura, percepção de áudio ou benefício de aprendizagem.'])
        variant['analytical_application_ids']=[app_id];variant['relations'][0]['analytical_application_ids']=[app_id]
        op['operation_variants'].append(variant)
    op['historical_relations']=op.get('historical_relations',deepcopy(op['relations']))
    op['relations']=[]  # Only scoped variants authorize a relationship.

    for key in ['PAD-ORIENTACAO-AUDIO-RECUPERAVEL','PAD-RETORNO-HAPTICO-RUIDO']:
        op=ops[key]
        op['transfer_scope']['requires_existing_representation']=True
        op['transfer_scope']['allow_new_task_with_functional_witness']=False
        op['transfer_scope']['task_ids']=['TAR-NAVEGAR-E-ORIENTAR-SE','TAR-ACOMPANHAR-ORIENTACAO-317CD64']
        barrier_ids=['BAR-AUDIO-PODE-PERDER-EFETIVIDADE-COM-RUIDO-04E2CCE']
        if key=='PAD-ORIENTACAO-AUDIO-RECUPERAVEL':
            barrier_ids.append('BAR-EFEMERIDADE-DO-FEEDBACK-AUDITIVO-611AFB8')
        op['applicability_witness']=dict(all=[
            dict(field='modalidades',ids=['MOD-AUDIO']),
            dict(field='barreiras',ids=barrier_ids),
            dict(field='tarefas',ids=op['transfer_scope']['task_ids'])],
            rationale='Exige orientação sonora situada e sua barreira própria; a coincidência com retomada ou feedback genéricos não autoriza transferência.')
        op.pop('applicability_requirements',None)
        op['requires_facts']=[f for f in op.get('requires_facts',[]) if f['id']!='AudioUsable']+[dict(id='AudioUsable',label='A pessoa consegue acessar a mensagem sonora neste ambiente?')]
    ops['PAD-RETORNO-HAPTICO-RUIDO']['independent_support_allowed']=False
    ops['PAD-EXPRESSAO-AUTORAL-FALA-AUDIO']['applicability_witness']=dict(any=[
        dict(field='tarefas',ids=['TAR-COMUNICAR-E-EXPRESSAR','TAR-COMUNICAR-CONTEUDO-1545B38']),
        dict(field='necessidades',ids=['NEC-COMUNICACAO-MULTIFORMATO'])],
        rationale='A autoria e expressão precisam aparecer como ação/necessidade; acesso a conteúdo de outra pessoa não implica produção autoral.')
    for key, representations, resources in [
            ('PAD-VIDEO-PROCESSO',['MOD-VIDEO'],['RED-VIDEO','RED-VIDEO-HISTORICO','RED-VIDEO-CURTO-HISTORIA']),
            ('PAD-REPRESENTACAO-VISUAL-EXPLICADA',['MOD-IMAGEM','MOD-DESENHO'],['RED-IMAGEM-DIGITAL','RED-SEQUENCIA-MULTIMODAL-DIGITAL']),
            ('PAD-CONTEUDO-WEB-EQUIVALENTE',[],['RED-CONTEUDO-WEB','RED-PAGINA-WEB'])]:
        op=ops[key]
        witnesses=[dict(field='recursos_digitais',ids=resources)]
        if representations:
            witnesses.append(dict(field='modalidades',ids=representations))
        op['applicability_witness']=dict(any=witnesses,
            rationale='A adaptação depende da existência ou proposta explícita desta representação/material; função nominal isolada não basta.')
        op['transfer_scope']['input_context_witness']=deepcopy(op['applicability_witness'])
        op.pop('applicability_requirements',None)
        op['requires_facts']=[f for f in op.get('requires_facts',[]) if f['id']!='AudioUsable']
        for variant in op.get('operation_variants',[]):
            variant['applicability_witness']=deepcopy(op['applicability_witness'])
            variant['transfer_scope']=deepcopy(op['transfer_scope'])
    # Guard reuse by an actual documented audio-navigation task, not the
    # historical population or a free-text match for a topic.
    for key in ['PAD-ORIENTACAO-AUDIO-RECUPERAVEL','PAD-RETORNO-HAPTICO-RUIDO']:
        op=ops[key]
        op['transfer_scope']['requires_existing_representation']=True
    for op in ops.values():
        op['grounded_claim_ids']=list(dict.fromkeys(s['claim_id'] for s in op['claim_support']))
        for contract in [op,*op.get('operation_variants',[])]:
            for relation in contract.get('relations',[]):
                relation['requires_analytical_authorization']=True

    for row in data['functional_matrix']:
        row['rc2_audit']=dict(date=DATE,claim_ids=row.get('inference_contract',{}).get('claim_ids',[]),
            result='REQUIREMENT_ONLY_NOT_INDIVIDUAL_CAPABILITY',candidate_promoted=False)
    for row in data['knowledge']:
        row['rc2_audit']=dict(date=DATE, claim_ids=[c['id'] for c in row.get('operation_claims',[])],
            result='SCOPED_CLAIMS_PRESERVED',whole_statement_promoted=False,
            original_articles_reread=False)
    data['metadata'].update(version=VERSION,title='Base pública do Arcabouço Multimodal — articulação operacional '+VERSION,
        generated_at=DATE,interface_version='AMADO-web-'+VERSION,derived_from_version='1.5.0-rc1')
    data['metadata']['claim_authorization_policy']['analytical_application_state']='GROUNDED_ANALYTICAL_APPLICATION'
    data['metadata']['claim_authorization_policy']['analytical_application_requires_exact_premises']=True
    data['metadata']['migration_note']='RC2: aplicações analíticas delimitadas, alternativas por destinatário e fases de preparação. Estados anteriores e candidatos preservados. Consulta pontual às seções MMI/WCAG, não releitura dos artigos.'
    return data


if __name__ == '__main__':
    path=ROOT/'data/knowledge-base.json'
    data=revise(json.loads(path.read_text(encoding='utf-8')))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    path=ROOT/'experimental/v2/trajectory-bindings.json'
    bindings=json.loads(path.read_text(encoding='utf-8'))
    for row in [*bindings['contracts'].values(),*bindings['applications']]:
        row['requires_facts']=[f for f in row.get('requires_facts',[]) if f!='LearningCommunicationContext']
    bindings['scope_revision_rc2']=dict(date=DATE,
        removed_historical_requirement='LearningCommunicationContext',
        reason='A tarefa do piloto é produzir e revisar o mesmo rascunho; CARE, MMI e a opção de revisão WCAG não exigem contexto educacional.',
        retained='Capacidade, compatibilidade, percepção, controle e correção permanecem necessários.',
        legacy_records_promoted=False)
    # The bridge checks the complete record, including audit metadata. Refresh
    # exactly the already-bound records after this scoped migration; retain the
    # previous fingerprints, rather than weakening that integrity check.
    previous = bindings.setdefault('record_hashes_before_rc2', deepcopy(bindings['records']))
    changed = []
    for collection, records in bindings['records'].items():
        indexed = {row['id']: row for row in data[collection]}
        for identifier in records:
            encoded = json.dumps(indexed[identifier], sort_keys=True,
                                 ensure_ascii=False, separators=(',', ':'))
            current = hashlib.sha256(encoded.encode('utf-8')).hexdigest()
            if previous[collection][identifier] != current:
                changed.append(collection + '/' + identifier)
            records[identifier] = current
    bindings['scope_revision_rc2']['record_hashes_refreshed'] = changed
    bindings['scope_revision_rc2']['record_hash_change_reason'] = (
        'Revisão dos mesmos registros vinculados; metadados de auditoria RC2 '
        'não promovem as afirmações históricas nem removem a checagem de integridade.')
    path.write_text(json.dumps(bindings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
