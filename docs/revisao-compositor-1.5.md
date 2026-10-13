# Revisão independente do compositor situado

Data: 2026-10-13. Objeto: `_SituatedRun`, em `experimental/v2/composer.py`. Revisão inicialmente somente leitura; apenas este documento foi escrito pela revisão. As correções de código foram feitas pelo responsável pelo compositor e depois verificadas independentemente.

Foram reproduzidas quatro falhas iniciais e duas variantes adicionais de transferência de escopo. Após as correções pelo responsável, os seis casos mínimos passaram na repetição independente. O gate de fundamento pendente também passou. Não restam falhas abertas nos casos desta revisão; isso não equivale a comprovação de ausência de outros defeitos ou validação com pessoas.

## Achados e estado conferido

| Achado | Efeito anterior reproduzido | Estado após correção | Local atual |
| --- | --- | --- | --- |
| P1 — negativa situada de operação perdia para registro geral de recurso operado | `OP-A:operability=false` produzia checagem `PASS`, valor observado `true` e uma escolha `COMPOSED` | `FAIL`, observado `false`, `INSUFFICIENT`, zero escolhas | compositor:1419 e 1425 |
| P1 — necessidade do contexto atribuída a todas as pessoas | Uma afirmação `need`, cujo sujeito era o contexto, derivava F-A/F-B para participantes a e b | Zero funções pessoais derivadas; zero escolhas | compositor:1114 |
| P1 — variante por lista da situação | `situation.need_ids=['NEED']` derivava F-A/F-B para a e b sem atribuição individual | Zero funções derivadas e zero candidatos condicionais | compositor:1044 |
| P2 — tarefa RDF atribuída também ao destinatário | Uma tarefa com ator e destinatário explícitos derivava sua função para ambos | Função requerida somente para actor, não para recipient | compositor:1195 |
| P2 — função explícita desconhecida descartada da cobertura | F-A mais UNKNOWN-FUNCTION retornava `COMPOSED`, embora registrasse lacuna da função desconhecida | `INSUFFICIENT`, zero escolhas completas e um segmento parcial; lacuna preservada | compositor:1170, 1542 e 1662 |
| P2 — situação adiada interferia na priorização | Situação ativa composta, mas exigência F-B de situação adiada entrava em `unassigned` e mudava o resultado geral para `INSUFFICIENT` | Ativa `COMPOSED`, uma escolha; adiada preservada em `deferred_situation_ids`, sem exigência não atribuída na ativa | compositor:1703 |

Os números de linha correspondem à leitura realizada após a correção; os nomes dos métodos e as condições descritas são as referências estáveis.

## Probes mínimos executados

Fixture exclusivamente sintética: `synthetic_catalogue()` em `tests/test_situated_composition.py`. Não utiliza dados de participantes reais nem modifica a base. Preparação comum:

```python
import sys
sys.path.insert(0, 'tests')
from test_situated_composition import synthetic_catalogue
from experimental.v2.composer import Composer
c = Composer([])
c.base = synthetic_catalogue()
```

1. **AUDIT_GROUP_NEED_SCOPE.** Contexto confirmado `ctx`, pessoas `a`/`b`, situação `s` com tarefa TASK e ambas as pessoas. Uma afirmação confirmada: `subject_id='ctx', situation_id='s', kind='need', value='NEED'`, texto sintético “Alguns precisam de apoio.” Executar `c.compose_context(context)`. Resultado conferido: `required_functions=[]`, `choices=[]`, `status='INSUFFICIENT'`. Não se atribuiu o subconjunto desconhecido a todos.

2. **AUDIT_UNKNOWN_REQUIREMENT.** Contexto confirmado, somente pessoa `a`, situação `s`, tarefa TASK, `function_ids=['F-A', 'UNKNOWN-FUNCTION']`. Resultado conferido: lacuna `UNKNOWN_REQUIRED_FUNCTION`, `status='INSUFFICIENT'`, zero escolhas, um segmento parcial. A operação conhecida não foi apresentada como cobertura completa.

3. **AUDIT_DEFERRED_ISOLATION.** Pessoas `a`/`b`; `active_situation_id='active'`. Situação ativa: participante `a`, TASK, função F-A. Situação `deferred`: participantes a/b, TASK, função F-B. Resultado conferido: `status='COMPOSED'`, uma escolha, `deferred_situation_ids=['deferred']`, `unassigned_scope_requirements=[]`.

4. **AUDIT_NEGATIVE_OPERABILITY.** No contrato sintético OP-A, definir `resource_requirements={'all':['RSC'], 'capability_check_required':True}`. Pessoa `a` com `recurso_operado_ids=['RSC']`; situação `s` com TASK, F-A e RSC `DISPONIVEL_CONFIRMADO`. Adicionar `situated_facts=[{'participant_id':'a','situation_id':'s','fact_id':'OP-A:operability','value':False}]`. Resultado conferido: `INSUFFICIENT`, zero escolhas; checagem de operabilidade `FAIL` com valor observado `false`.

## Gates adicionais e limites

**AUDIT_GROUP_NEED_SITUATION_ARRAY:** mesma configuração de a/b, mas sem afirmações e com `need_ids=['NEED']` diretamente na situação `s`. Resultado inicial: F-A e F-B derivados para ambas as pessoas e dois candidatos condicionais. Resultado após correção, conferido independentemente: zero funções derivadas e zero candidatos condicionais.

**AUDIT_RDF_ACTOR_SCOPE:** `Composer([])` com três triplas sintéticas: TaskSynthetic tipada como `V2.Task`, ligada por `V2.requiresFunction` a FunctionSynthetic tipada como `V2.Function`. Contexto confirmado, situação `s`, tarefa TaskSynthetic, participantes actor/recipient, `actor_ids=['actor']`, `recipient_ids=['recipient']`. Resultado inicial: FunctionSynthetic requerida para ambos. Após correção, somente actor recebe o requisito. Esse probe usa somente grafo em memória; uma tentativa adicional de carregar `ResearchComposer(False)` foi impedida por `PermissionError [WinError 5]` em `Path.resolve(schema.ttl)` e não conta como verificação do catálogo RDF real.

**AUDIT_PENDING_FOUNDATION:** na mesma fixture, mudar somente `operation_claims[0].foundation_status` para `PENDING`; contexto confirmado com TASK, NEED e `facts={'R:sufficiency':True}`. Resultado: zero escolhas, zero candidatos condicionais, uma entrada em `claim_audit` e zero perguntas em `facts_to_confirm`. O gate de `claim()` continua impedindo converter falta de fundamento em condição contextual desconhecida.

A revisão também inspecionou a derivação de funções anterior à consulta de componentes, a separação entre opções de representação e modos selecionados, estados de recursos propostos e dependências de operações. Não confirmou nesses pontos defeitos além dos relatados. O caminho RDF primário foi distinguido da ponte histórica: não se atribuiu promoção automática de K28/K29 sem demonstração de que essa promoção ocorreu. A verificação primária das fontes e a avaliação completa desse caminho pertencem ao relatório de integração, não a estes probes.

As skills de engenharia ontológica e interação multimodal orientaram a preservação de escopo, a separação entre fundamento e operacionalização e a recusa de inferir capacidade individual de condição coletiva. Os resultados registrados são testes técnicos sintéticos, não validação semântica integral ou eficácia da orientação.
