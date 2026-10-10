# MADO V2 — composição fundamentada de formas de interação

**Versão experimental `2.0.0-alpha1`.** Este diretório implementa um primeiro piloto da evolução da MADO. O site, o motor público, a base anterior e a versão da tese não são substituídos. Origem preservada: commit `73013190f26cf8806e7f647dbb3fa36a8c07a3c3`.

## O que mudou

Em vez de selecionar somente configurações completas previamente redigidas, este compositor:

1. Lê quais funções a tarefa exige, antes de selecionar qualquer solução.
2. Examina capacidades unitárias de entrada e de revisão.
3. Exige condições funcionais e recursos confirmados, além de fundamentação exata.
4. Liga etapas somente quando existe relação documentada e o conteúdo produzido por uma é aceito pela seguinte.
5. Apresenta as combinações admissíveis com as verificações, contribuições documentais e limites.

Não há lista de pares completos como “teclado + leitura em voz” no motor ou na base. Esse percurso resulta da composição. Existem, entretanto, operações unitárias, condições, tipos de conteúdo e uma regra de sequência previamente modelados. O sistema não inventa capacidades nem interpreta automaticamente uma nova diretriz.

O recorte é **produzir e revisar uma contribuição digital** ou **revisar texto já disponível**. Não é ainda uma substituição integral do AMADO nem um mecanismo para qualquer tarefa.

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

Captura seguida de revisão **não é automaticamente complementaridade CARE**. Aqui se representa uma sequência funcional fundamentada; não se modelam ainda fusão, sincronização temporal ou redundância. A interpretação teórica e seus limites estão em [Fundamentação](docs/fundamentacao.md).

## Executar

Na raiz deste repositório, com Python 3.12 e as dependências do projeto (o diretório `vendor` existente é utilizado quando disponível):

```powershell
python -B experimental/v2/cli.py --context experimental/v2/examples/speech-visual.json
python -B experimental/v2/cli.py --context experimental/v2/examples/keyboard-audio.json
python -B experimental/v2/cli.py --context experimental/v2/examples/keyboard-audio.json --extension experimental/v2/extensions/audio-review.ttl
python -B experimental/v2/verify.py
```

O CLI lê JSON estruturado e emite JSON no terminal. Não salva contexto ou histórico. Também aceita `--context -` para receber o objeto pela entrada padrão. Os exemplos são sintéticos; os identificadores não são consultados para escolher capacidades. Texto livre, diagnósticos e campos desconhecidos não são interpretados silenciosamente.

Disponibilidade e condições usam `true`, `false` ou `null`. Ausência e `null` significam **pendência**, não aprovação. `COMPOSED` significa proposta completa segundo as condições registradas, não execução da atividade nem resultado observado. `INSUFFICIENT` significa ausência de proposta completa; `UNCONFIRMED`, que falta confirmação do contexto. Alternativas não recebem ranking de qualidade.

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

Os critérios analíticos deste piloto são identificados separadamente; não foram renomeados como CA01–CA88. K41/K44 aparecem como antecedentes parciais, sem modificar os registros originais. A integração ampla à base e à interface exigirá revisão semântica e regressão próprias.

## Limites que permanecem

- A tarefa e as condições são estruturadas e confirmadas previamente; não há interpretação de narrativa.
- A composição depende de funções, capacidades e relações representadas. Uma referência bibliográfica nova, sozinha, não muda uma decisão.
- O recorte usa uma capacidade por função, sequência linear e até 64 propostas retornadas, com aviso quando esse limite é atingido.
- Esse limite controla o tamanho da saída, não todo o custo da busca. O piloto não foi dimensionado para grandes catálogos combinatórios.
- A matriz de alternativas não foi avaliada com participantes, leitor de tela ou tarefa real.
- Nenhuma alegação de melhoria da aprendizagem, acessibilidade universal ou escolha ótima é feita.
- Esta V2 não está conectada à página pública. A página continua usando sua versão preservada.
