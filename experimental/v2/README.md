# MADO V2 — composição fundamentada de formas de interação

**Versão experimental `2.0.0-alpha4`, integrada à MADO `1.5.0-rc2`.** Este diretório contém o módulo de composição do AMADO no `arcabouco-multimodal`. Não é outro repositório ou site. O repositório MADO e a versão da tese não são substituídos. Origem do piloto preservada: commit `73013190f26cf8806e7f647dbb3fa36a8c07a3c3`; estado anterior desta revisão: `c8b94d3`. Os pilotos anteriores permanecem no histórico.

A ponte introduzida na `alpha2` relaciona **os registros reais da pesquisa** e separa proposta completa, condicional e parcial. Na `alpha4`, aplicações analíticas delimitadas também autorizam operações e relações: são conferidas premissas, contribuições, critérios, alvos autorizados e condições por participante e situação. [O README principal descreve o contrato atual e a base consultada](../../README.md). O documento [Reutilização da trajetória](docs/reutilizacao-da-trajetoria.md) conserva o recorte do piloto original.

## O que mudou

Em vez de selecionar somente configurações completas previamente redigidas, este compositor:

1. Lê quais funções a tarefa exige, antes de selecionar qualquer solução.
2. Examina capacidades unitárias de entrada e de revisão.
3. Exige condições funcionais e recursos confirmados, além de fundamentação exata.
4. Liga etapas somente quando existe relação documentada e o conteúdo produzido por uma é aceito pela seguinte.
5. Apresenta as combinações admissíveis com as verificações, contribuições documentais e limites.
6. Quando não há percurso completo, identifica as condições a confirmar e as etapas sustentadas que ainda podem ser aproveitadas, sem apresentá-las como solução integral.

Não há lista de pares completos como “teclado + leitura em voz” no motor ou na base. Esse percurso resulta da composição. Existem, entretanto, operações unitárias, condições, tipos de conteúdo e uma regra de sequência previamente modelados. O sistema não inventa capacidades nem interpreta automaticamente uma nova diretriz.

O piloto RDF cobre **produzir e revisar uma contribuição digital** ou **revisar texto já disponível**. A composição situada emprega também os contratos da base curada, incluindo organização, retomada e alternativas de acesso a conteúdo audiovisual, no escopo efetivamente fundamentado. Recurso disponível, material a preparar e conferência posterior são separados. Apoios independentes podem permanecer úteis sem formar uma sequência; não são chamados automaticamente de combinação multimodal. A cobertura continua delimitada, não universal.

## Experimento central: conhecimento muda o que pode ser composto

Uma pessoa pode escrever usando teclado, não pode conferir visualmente o texto e pode revisar por leitura em voz, com pausa, repetição e correção. Nenhum diagnóstico é necessário para representar essas condições.

| Execução com o mesmo contexto | Resultado esperado |
|---|---|
| Base inicial | Insuficiência: a capacidade de revisão por áudio existe, mas ainda não tem aplicação de conhecimento autorizada |
| Base + `extensions/audio-review.ttl` | Escrita por teclado → revisão do mesmo rascunho por leitura em voz |
| Extensão removida | Insuficiência novamente |
| Extensão mantida, saída de áudio impedida | Insuficiência: a rota depende de áudio utilizável |
| Correção não confirmada | Candidata pendente; nenhuma orientação pronta |

A extensão acrescenta **conhecimento, articulação, contribuições localizadas e o vínculo exato que fundamenta a capacidade**. Não acrescenta motor, capacidade, tarefa, regra de sequência ou texto de uma resposta completa. As quatro capacidades já estão declaradas na base. Com todas as condições viáveis, as combinações passam de duas a quatro.

Esse é um teste de **extensibilidade por conhecimento e recombinação de capacidades representadas**. Não é prova de descoberta automática, superioridade sobre todas as alternativas nem eficácia educacional. A retirada deliberada do fundamento na base é uma ablação experimental, não uma lacuna descoberta num atendimento real.

## Onde está a articulação multimodal

- **Alternativas de entrada:** escrita e fala podem atender à função de produzir um rascunho, mas possuem requisitos diferentes. Acesso individual e esforço não são presumidos equivalentes.
- **Entrada e saída distintas:** produzir por uma forma não obriga revisar pela mesma. O rascunho editável é o conteúdo comum entre as etapas.
- **Coordenação:** a revisão depende do controle de pausa, correção e conclusão. Uma etapa não pode simplesmente entregar informação a outra sem conferir suas condições.
- **Fundamentação:** cada capacidade liga-se a um critério, um conhecimento e uma articulação específicos; cada contribuição documental leva a um trecho localizado e sua fonte.

Captura seguida de revisão **não é automaticamente complementaridade CARE**. As relações funcionais registradas distinguem sequência dependente, alternativa, complementaridade e redundância, sem deduzi-las da presença de duas mídias. Isso não implementa fusão de sinais ou sincronização temporal de dispositivos, nem comprova benefício empírico. A interpretação do piloto e seus limites estão em [Fundamentação](docs/fundamentacao.md).

## Executar

Na raiz deste repositório, com Python 3.12 e as dependências do projeto (o diretório `vendor` existente é utilizado quando disponível):

```powershell
python -B experimental/v2/cli.py --context experimental/v2/examples/speech-visual.json
python -B experimental/v2/cli.py --context experimental/v2/examples/keyboard-audio.json
python -B experimental/v2/cli.py --context experimental/v2/examples/keyboard-audio.json --extension experimental/v2/extensions/audio-review.ttl
python -B experimental/v2/verify.py
python -B experimental/v2/cli.py --trajectory --context experimental/v2/examples/learning-contribution.json
python -B experimental/v2/verify_trajectory.py --output experimental/v2/evidence/trajectory-report.json
```

O CLI lê JSON estruturado e emite JSON no terminal. Não salva contexto ou histórico. Também aceita `--context -` para receber o objeto pela entrada padrão. Os exemplos são sintéticos; os identificadores não são consultados para escolher capacidades. Texto livre, diagnósticos e campos desconhecidos não são interpretados silenciosamente.

Disponibilidade e condições usam `true`, `false` ou `null`. Ausência e `null` significam **pendência**, não aprovação. `COMPOSED` significa proposta completa segundo as condições registradas, não execução da atividade nem resultado observado. `INSUFFICIENT` significa ausência de proposta completa; `UNCONFIRMED`, que falta confirmação do contexto. Alternativas não recebem ranking de qualidade.

O campo `proposal_status` detalha esse resultado: `COMPLETE`, `CONDITIONAL`, `PARTIAL`, `NONE` ou `UNCONFIRMED`. Portanto, `INSUFFICIENT` não significa que todo o conhecimento foi descartado. `partial_segments` conserva trechos contíguos do percurso com apoio verificado; sua entrada pode depender de uma etapa anterior ainda não coberta. Não se deve juntar esses segmentos na interface como se uma composição completa tivesse sido verificada.

Use `--trajectory` no CLI para carregar a ponte da trajetória em vez do piloto genérico. Esse modo lê `data/knowledge-base.json` e os vínculos específicos de `trajectory-bindings.json`; não interpreta publicações ou uma narrativa em texto livre durante a execução. Condições adicionais derivadas de K41 são obrigatórias e ficam pendentes quando não informadas.

## Conferir o raciocínio

No resultado, cada item de `choices` contém:

- `steps`: função, forma de interação, recurso, ação unitária, limite e fundamentos exatos;
- `relations`: estado informacional compartilhado e justificativa da ligação entre etapas;
- `groundings`: critério → conhecimento → articulação → contribuição → trecho → fonte;
- `check_ids`: vínculos para as verificações realmente realizadas em `execution_evidence`;
- `pending_candidates` e `exclusions`: informações pendentes e motivos de exclusão, fora das propostas prontas.

Os estados das verificações são `PASS`, `FAIL`, `PENDING` e `NOT_EXECUTED`. Confirmar uma condição na entrada não significa medi-la empiricamente. A equivalência entre tipos de conteúdo também não prova que uma transcrição preservou efetivamente o significado.

## Arquivos e verificação

| Arquivo | Papel |
|---|---|
| `schema.ttl` | Vocabulário experimental, preservando as seis categorias centrais |
| `base.ttl` | Capacidades, condições, critérios e fundamentos do piloto |
| `extensions/audio-review.ttl` | Incremento documental comparado no experimento |
| `shapes.ttl` | Integridade e pareamento dos registros |
| `composer.py` | Composição determinística; não interpreta fontes ou narrativa |
| `trajectory.py` | Projeção da parcela utilizada da base real, com hashes, origem e condições preservadas |
| `trajectory-bindings.json` | Aplicações analíticas propostas para operacionalizar registros da trajetória |
| `verify_trajectory.py` | Execuções sintéticas e verificação da ponte com a base |
| `queries/` | Consultas de fundamentação exata e relações funcionais |
| `tests/test_composition.py` | Testes sintéticos, positivos e adversos |
| `project/competency-questions.csv` | Oito questões específicas do piloto e respectivos limites |
| `evidence/verification.json` | Resultados reproduzidos, ablação, testes e hashes dos arquivos preservados |
| `evidence/novel-case-trace.json` | Execução completa do caso sintético teclado–áudio |
| `evidence/combined.owl` | RDF/XML do piloto para inspeção no Protégé |
| `evidence/reasoner-report.json` | Verificação OWL 2 DL/HermiT, quando executada |
| `evidence/manifest.json` | Hashes dos arquivos desta entrega |

O executor usa as relações RDF diretamente; as consultas SPARQL tornam a fundamentação examinável. OWL formaliza categorias e relações; SHACL verifica integridade; Python compõe os percursos. **HermiT não gera as orientações.**

## Estado documental e autoria analítica

As contribuições são paráfrases acompanhadas de fontes e localizações; PDFs de terceiros não são redistribuídos. `PRIMARY_CHECKED` indica consulta do trecho primário registrado; `LEGACY_RECORD_ONLY` preserva a distância até os documentos originais da trajetória. Um registro legado sozinho não autoriza o uso no piloto.

`CURATED_FOR_PILOT` significa habilitação técnica nesta proposta de modelagem assistida, **não aprovação semântica pela autora ou especialista**. Os conhecimentos são sínteses de projeto (`DESIGN_SYNTHESIS_NOT_EMPIRICAL`), não resultados empíricos. A autora ainda deve conferir a síntese, suas condições e sua adequação à trajetória da tese.

No piloto genérico, os critérios analíticos são identificados separadamente; não foram renomeados como CA01–CA88. A ponte da trajetória mantém os identificadores reais que emprega, como CA38, e explicita as novas aplicações como propostas. K28/K29 continuam candidatos reconstruídos e K41 permanece documentalmente parcial. A interface oferece explicitamente as duas tarefas deste módulo; não transforma automaticamente qualquer caso em uma delas.

## Limites que permanecem

- A tarefa e as condições são estruturadas e confirmadas previamente; não há interpretação de narrativa.
- A composição depende de funções, capacidades e relações representadas. Uma referência bibliográfica nova, sozinha, não muda uma decisão.
- O recorte usa uma capacidade por função, sequência linear e até 64 propostas retornadas, com aviso quando esse limite é atingido.
- A busca também limita a enumeração a 4.096 tentativas por fase e registra interrupção. Esse controle não demonstra escalabilidade para grandes catálogos; se o limite for atingido, ausência de resultado não comprova inexistência de outra combinação.
- A matriz de alternativas não foi avaliada com participantes, leitor de tela ou tarefa real.
- Nenhuma alegação de melhoria da aprendizagem, acessibilidade universal ou escolha ótima é feita.
- A integração no mesmo AMADO utiliza operações próprias de catálogo e composição; os casos anteriores mantêm seu executor. Veja o escopo em [Composição por funções](../../docs/composicao-por-funcoes.md). Disponibilidade no endereço público depende da publicação e da verificação registradas na entrega.
