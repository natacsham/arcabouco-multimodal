# Arcabouço Multimodal para Acessibilidade Digital

**Projeto de pesquisa de doutorado de Natacsha Ordones Raposo de Melo.**

O **Arcabouço Multimodal para Acessibilidade Digital** organiza a articulação e o emprego de conhecimentos para apoiar decisões de interação. A **MADO (Multimodal Accessibility Decision Ontology)** representa esses conhecimentos, suas relações, critérios e condições. O **AMADO** é o instrumento que consulta a base e apresenta orientações com fundamentação rastreável.

**Versão desta revisão: MADO 1.5.0-rc2 / compositor 2.0.0-alpha4 — candidata.** O estado anterior permanece no commit `c8b94d3c344cbe6922078c8b28b8bb5821b92e67`; a implementação desta revisão utiliza a branch `feat/articulation-operational-rc2`. Este repositório não modifica o repositório MADO nem a versão da tese. As avaliações anteriores não validam automaticamente esta revisão.

**Este é o projeto em desenvolvimento.** Base, representação, motor e interface continuam em `arcabouco-multimodal`. As versões da base e do compositor são distintas para identificar exatamente o que foi executado. Não foi criada outra matriz de conhecimento.

No AMADO, conte seu desafio por texto ou ditado, confira o entendimento e responda a até três esclarecimentos por rodada. Os exemplos e os relatos livres passam pelo mesmo contrato de contexto e pelo compositor situado. O assunto da aula e palavras como “turma” não escolhem outro motor. A interpretação é determinística e limitada: correções, informação não reconhecida e condições ainda desconhecidas permanecem visíveis. Refinamentos posteriores são opcionais.

## Qual problema esta pesquisa enfrenta?

Conhecimentos úteis ficam distribuídos entre normas, publicações, estudos, artefatos, personas e resultados. Encontrar esses documentos não basta para decidir **como combinar formas de interação para uma pessoa, uma tarefa e determinadas condições**.

O foco da pesquisa é a articulação desses conhecimentos: o que pode ser relacionado, o que essa relação permite compreender, em quais condições é pertinente e até onde pode ser empregado em uma nova decisão.

| Elemento | Papel no projeto |
| --- | --- |
| **Arcabouço Multimodal para Acessibilidade Digital** | Organiza o raciocínio da pesquisa e sua trajetória cumulativa. |
| **MADO** | Representa semanticamente conhecimentos, articulações, critérios, contextos, decisões e proveniência. |
| **AMADO** | Recupera e seleciona conhecimentos e padrões compatíveis, compõe uma orientação e apresenta sua rastreabilidade. |

## Comece por aqui

- [Veja a correção do relato até a orientação e os três testes sintéticos](docs/relato-para-orientacao.md).
- [Acompanhe a revisão 1.5 e um exemplo integral efetivamente executado](docs/revisao-situada-1.5.md).
- [Entenda a MADO em linguagem simples](docs/entenda-mado.md).
- [Acompanhe um exemplo real da base](docs/exemplo-rastreavel.md).
- [Veja o teste de uma combinação não cadastrada e seus limites](docs/teste-de-reutilizacao.md).
- [Conheça as classes e as camadas de execução](docs/modelo.md).
- [Confira o que muda nesta revisão](docs/revisao.md).
- [Consulte verificações, limites e evidências](docs/verificacao.md).
- [Leia as condições de disponibilização e privacidade](docs/direitos-e-privacidade.md).
- [Execute e reproduza as verificações](docs/reproduzir.md).
- [Confira as licenças dos componentes de terceiros](THIRD_PARTY.md).

Os endereços públicos reúnem [**A pesquisa**](https://natacsham.github.io/arcabouco-multimodal/), [**Documentação técnica da MADO**](https://natacsham.github.io/arcabouco-multimodal/ontologia/) e [**Experimente o AMADO**](https://natacsham.github.io/arcabouco-multimodal/amado/). O [fluxo do GitHub Pages](https://github.com/natacsham/arcabouco-multimodal/actions/workflows/pages.yml) registra cada publicação. A [conferência pública](evidence/situated-public-smoke.json) identifica o commit esperado, os arquivos efetivamente servidos, seus hashes e os limites da verificação. Um relatório de revisão anterior não valida alterações posteriores; publicação e testes técnicos não equivalem à avaliação humana da orientação.

Cada escolha pode ser examinada por duas leituras: **como seu conhecimento foi construído** e **por que ele foi empregado naquele caso**. Ambas usam os mesmos registros, distinguindo contribuição da fonte, operação de articulação, conhecimento, aplicação do critério e limite. Contribuição não detalhada permanece como lacuna, sem justificativa inventada. [Contrato da explicação pública](docs/explicacao-publica.md).

## O que é conhecimento multimodal articulado?

Não é apenas um conjunto de citações nem um resumo de um artigo. É a compreensão produzida ao relacionar conteúdos e registrar convergências, complementações, condições, refinamentos e limites.

Um exemplo executado nesta revisão relaciona **independência entre entrada e saída**, **operação situada** e **possibilidade de conferir e corrigir antes de concluir**. Essa articulação permite examinar entradas e apresentações diferentes para produzir e revisar o mesmo rascunho. Não basta constatar que voz, texto e áudio estão disponíveis: a pessoa precisa poder realizar cada função e a ligação precisa estar fundamentada.

O AMADO não descobre essa síntese intelectual sozinho. Ele consulta articulações previamente documentadas e verifica se os conhecimentos e os padrões disponíveis podem ser empregados no contexto informado. [Veja o exemplo e seus limites](docs/exemplo-rastreavel.md).

## O que torna a orientação multimodal?

A orientação precisa dizer **qual função cada modo cumpre, como os modos se relacionam e o que fazer se uma rota não for viável**. Ter texto, áudio e vídeo na mesma tela não demonstra, por si só, integração multimodal ou acessibilidade.

O modelo diferencia modo de interação, recurso digital, dispositivo e responsável. Um smartphone não é uma modalidade; vídeo pode reunir representações visuais e sonoras; participação de diferentes pessoas não substitui a explicação da relação entre os modos.

## Como funciona, sem LLM

### Duas leituras do mesmo resultado

O resultado do AMADO apresenta **O que fazer**, com ações e passos abertos, quem realiza, para quem, condições essenciais e como conferir. A seção recolhida **Como chegamos a esta orientação** reúne a informação considerada no relato, contribuições localizadas, articulação, critério, verificações e limites. As fontes não são repetidas em outra “orientação completa”. A leitura em voz acompanha somente a parte prática.

As possibilidades recebem os títulos **Orientação 1, 2, 3…**, repetidos na fundamentação para facilitar a consulta. Dentro de um percurso com relações sequenciais explícitas, a contagem dos passos continua entre as operações. A numeração das orientações não significa que seja necessário realizar todas. Ações, condições antes da aplicação e acompanhamento têm áreas visualmente distintas, identificadas também por títulos e bordas.

Esta revisão de apresentação parte do commit `b6cefb8` e não altera a base, a ontologia nem o compositor. Os passos vêm das ações e fases registradas na execução; não acrescentam modalidades, responsáveis presumidos ou novas relações. Alternativas e apoios independentes não são transformados em etapas obrigatórias de um mesmo percurso. As decisões permanecem comparáveis à versão anterior, preservada no histórico.

### O que mudou na articulação operacional

Uma relação histórica entre artigos não autoriza uma recomendação. Nesta revisão, uma **aplicação analítica delimitada** liga afirmações e contribuições conferidas a uma operação ou relação específica. O motor verifica essa autorização durante a consulta. Retirar uma premissa indispensável impede as aplicações dependentes, mesmo que a bibliografia continue cadastrada.

O caminho está na mesma base `data/knowledge-base.json`, sem outra matriz:

| Registro existente | O que o programa verifica |
| --- | --- |
| `knowledge[].operation_claims` | Afirmação documental elegível, fonte e trecho correspondente; não aprovação do conhecimento inteiro. |
| `contributions` | O que o trecho contribui, para qual conhecimento e com qual estado de conferência. |
| `articulations[].operational_applications` | Premissas, operação analítica, compreensão resultante, critérios, operações/relações autorizadas, condições e limites. |
| `decision_components[].operation_contract` | Funções, entrada/saída, ação, recursos, participantes e representações utilizáveis. |
| `execution_evidence` | Verificações efetivamente feitas para a pessoa e a situação, incluindo falhas e pendências. |

**Exemplo da base:** `APP-ART-TRF-04-ORGANIZAR-RETOMAR` relaciona organização perceptível do conteúdo e navegação/retomada. As premissas delimitadas de `K38` e `K43` autorizam preparar instruções consultáveis, não apenas citar fontes ao lado desse conselho. A organização se apoia na informação e nas relações representadas; a retomada exige conservar e tornar localizável a etapa necessária. A aplicação precisa de leitura utilizável pelo destinatário e de um responsável que possa preparar o material. O texto resultante ainda deve ser produzido e conferido. Essa rota textual, sozinha, **não é classificada como combinação multimodal**.

Nas adaptações de mídia, o motor seleciona a rota de cada participante: informações sonoras podem demandar legendas, enquanto informações visuais não expressas na fala podem demandar descrição. A existência de um leitor de tela não confirma, por si, compreensão de gráficos nem acesso a áudio. Os registros mantêm a informação que cada alternativa deve preservar e a conferência ainda necessária. Em produção/revisão, a ligação é uma **sequência dependente sobre o mesmo rascunho**, não complementaridade presumida pela presença de fala e texto.

O compositor separa três fases: **pré-condição**, **material a preparar** e **verificação antes do uso**. Não exige que um resultado proposto já exista, nem apresenta o resultado futuro como pronto. Sem testemunho do tipo de ação ou informação exigido pelo contrato, uma função nominal semelhante não basta para recuperar uma operação.

### Como testar esta revisão

Os três relatos completos estão somente em `tests/fixtures/articulation_transfer_cases.json`. Não são opções da interface e não entram no pacote do navegador. Copie um relato no campo **Qual é o seu desafio de hoje?**, confira o entendimento, responda apenas ao que souber e gere a orientação. A relevância é julgada pela pessoa que examina a saída; o teste não a declara automaticamente.

Os testes comparam relato e contexto estruturado equivalente, retirada de recursos, alteração de acesso e retirada de fundamento. Os efeitos são classificados separadamente: combinação/alternativa acrescentada, restrição descoberta ou somente fundamentação ampliada. Não existe resposta textual esperada por tema.

Para reproduzir: `python -B -m unittest discover -s tests -p 'test_articulation_*.py'`, `python -B -m unittest discover -s tests -p 'test_operational_articulation_rc2.py'` e, após regenerar o pacote, `node tests/articulation-browser.mjs`. O último usa os controles visíveis, inclusive confirmação e revisão, sem fornecer fatos escondidos ao motor. Os demais testes, OWL/SHACL/consultas e a comparação local/navegador continuam necessários; este ensaio não os substitui.

### Onde estão as fontes e como entram na decisão

**O AMADO não lê PDFs nem pesquisa na internet durante a consulta.** Consulta uma base preparada antes da publicação. Não é necessário copiar todos os documentos para o repositório: o endereço original, a edição e a seção ficam vinculados ao registro extraído.

```text
PREPARAÇÃO DO CONHECIMENTO (antes do uso)
Fonte original online → extração localizada → contribuição delimitada
                      → articulação analítica → conhecimento e condições
                      → aplicação do critério a função/padrão existente

USO DO AMADO (no navegador)
Relato → informações a confirmar → contexto confirmado
      → recuperação + verificações → composição → orientação e fundamentos
```

1. **Localizar:** em `data/knowledge-base.json`, `sources` identifica as fontes da trajetória e `references` conserva as referências citadas pelos artigos. URL não comprova leitura do original.
2. **Conferir:** consultar a edição e a seção original; atualizar o registro existente em `excerpts` e sua origem em `criterion_origins`, preservando a localização anterior. Não promover toda a bibliografia a conhecimento operacional.
3. **Articular:** `contributions` delimita o que cada trecho acrescenta; `articulations` explica a operação e a compreensão resultante; `knowledge` registra aplicabilidade e limites. A síntese analítica é anterior à execução, não descoberta pelo programa.
4. **Operacionalizar:** delimitar `operation_claims` nos conhecimentos e `operation_contract` nos onze padrões existentes em `decision_components`. Os contratos qualificam ações, funções, entradas, saídas, relações e aplicações exatas de critérios. `experimental/v2/trajectory-bindings.json` conserva a ponte do piloto e seu refinamento técnico de tarefa; não é uma segunda matriz de casos. Bibliografia não habilita operações: cada afirmação usada precisa de apoio localizado elegível.
5. **Publicar:** regenerar RDF, catálogo, piloto e pacote; reexecutar as verificações; publicar somente os arquivos públicos. O navegador consome a mesma versão empacotada da base, não uma segunda planilha explicativa.

O [catálogo e o desenho do percurso](https://natacsham.github.io/arcabouco-multimodal/ontologia/#fontes) são projeções desses registros. A conferência documental é parcial: o estado, a seção e a versão de cada origem precisam ser lidos no registro correspondente; outras referências permanecem citadas ou pendentes. Acesso restrito a uma norma não é leitura concluída. [O que foi conferido e como reproduzir](docs/fundamentacao-documental.md).

1. O contexto é organizado em conceitos representados na base e conferido pela pessoa usuária.
2. Consultas recuperam conhecimentos pertinentes e articulações documentadas.
3. O motor verifica condições de aplicação, restrições, recursos e fundamentação.
4. Critérios e padrões elegíveis orientam a composição das configurações modais.
5. A orientação apresenta funções, recursos, responsáveis, alternativas, limites e o caminho até as fontes.

**Encontrar conhecimento não significa autorizar seu uso.** Ausência de informações ou de sustentação pode produzir perguntas, condições pendentes ou suspensão da decisão.

O AMADO executa Python no navegador por Pyodide, com RDF e consultas SPARQL. Não há servidor de decisões nem chamada a modelo de linguagem. A ontologia não gera prosa sozinha: o compositor emprega padrões e formulações previamente documentados. A narrativa livre também tem cobertura limitada e exige confirmação.

### O percurso executável nesta revisão

1. `engine.analyze_narrative` e `situated_context.py` conservam **quem**, **qual ação**, **situação**, **dificuldade**, **apoio** e o trecho de origem. Não atribuem uma capacidade a alguém por diagnóstico.
2. `situations` separa interações, por exemplo apresentação coletiva e consulta individual. `assertions` conserva o sujeito, a situação, o estado e as correções. O objetivo textual continua sendo descrição; não é anunciado como interpretação semântica geral.
3. A matriz funcional existente relaciona dificuldades reconhecidas a requisitos documentados. Quando não há suporte ou a atribuição é ambígua, isso gera uma lacuna específica, não uma necessidade inventada.
4. `DecisionEngine.generate_situated` chama `ResearchComposer.compose_context`. A recuperação operacional percorre registros curados em JSON e relações representadas; RDF conserva o modelo e a hierarquia, e SPARQL permite conferir as questões de competência. Não se afirma que o reasoner OWL compõe a orientação nem que toda verificação Python é uma inferência OWL.
5. A função necessária precede a escolha de operações. Cada aplicação relaciona a **afirmação delimitada**, seu trecho/fonte, critério, participante e situação. `PROPOSED_OPERATIONALIZATION` sem apoio autorizado permanece na auditoria. Uma condição contextual desconhecida, com fundamento já disponível, pode produzir uma possibilidade condicional.
6. As operações reaproveitam ações da base. Sequência dependente, alternativa funcional, complementaridade e redundância têm contratos diferentes. Identidade de tipos não prova preservação do significado; conteúdo, suficiência e acesso ainda podem precisar de confirmação situada.
7. A saída mantém escolhas, apoios parciais, condições, exclusões, limites da busca e `execution_evidence`. A interface apresenta ações e fundamentos da **mesma execução**. Não gera frases sobre modalidades ausentes.

O método `DecisionEngine.generate()` permanece para regressão de compatibilidade do seletor antigo. A operação pública `generate` usa `generate_situated()`. Essa distinção evita apresentar testes históricos do seletor como testes do novo compositor. A operação pública `compose` aceita o formato de entrada do piloto por um adaptador e executa o mesmo compositor situado; o método Python antigo `Composer.compose` permanece somente para reprodução histórica. Não há desvio automático por assunto ou palavra da narrativa.

**Como conferir:** [relatório e roteiro de reprodução desta revisão](docs/revisao-situada-1.5.md). Os resultados atuais e os itens não executados devem ser consultados nesse relatório, não inferidos de relatórios históricos.

### Um exemplo realmente executado, do fundamento à ação

O caso **sintético** `SYN-NOVEL-COLLAB-908` prepara notas para um encontro comunitário. A tarefa de produzir e revisar uma contribuição é atribuída separadamente a A e B. A declara fala e revisão visual utilizáveis; B declara teclado e revisão por fala utilizáveis. Recursos, correção, controle de conclusão e possibilidade de conferir o significado são entradas explícitas, não inferências sobre diagnósticos.

A cadeia documental é a seguinte:

1. **Fontes e contribuições:** os registros CARE e WCAG de teclado alimentam `CInputCARE` e `CInputKeyboard`, distinguindo alternativa funcional de operação individual. W3C MMI e WCAG 3.3.6 alimentam `CReviewMMI` e `CReviewWCAG`, distinguindo entrada/saída e revisão/correção. A WCAG de teclado não sustenta voz; a opção de revisão é uma escolha de projeto baseada em critério AAA, não exigência universal de modalidade.
2. **Articulação:** `ArtInput → KInput` estabelece produção por entrada operável; `ArtReview → KReview` liga o rascunho à conferência corrigível. `ArtAudioReview → KAudioReview` delimita a revisão por fala. Essas sínteses já estavam registradas; o programa não as descobriu durante o atendimento.
3. **Funções e aplicação:** a tarefa exige produzir (`Expression`) e conferir/corrigir (`Review`) antes da seleção. O executor verifica as aplicações exatas de `CriterionInput` e `CriterionReview`, seus apoios e condições por pessoa.
4. **Relação:** `ProductionThenReview` liga a saída e a entrada do mesmo `TextDraft`, com correção disponível. É sequência de produção/revisão, não complementaridade CARE inferida da presença de duas mídias.

| Pessoa | Operações e ações admitidas no ensaio |
| --- | --- |
| A | `CaptureSpeech → ReviewText`: registrar por fala, manter o rascunho editável e apresentá-lo visualmente para conferir e corrigir. |
| B | `CaptureKeyboard → ReviewSpeech`: registrar por teclado e ler o mesmo rascunho em voz, com pausa, repetição e correção sob controle da pessoa. |

Quando apenas `AudioUsable` de B é negado, a sequência de A é preservada e B mantém somente o registro por teclado; o conjunto deixa de ser declarado completo. Retirar em memória a regra `ProductionThenReview`, ou a operação analítica de `ArtReview` mantendo as fontes, também elimina as sequências completas. São verificações estruturais e de execução, **não prova de compreensão, aprendizagem ou coordenação entre pessoas**.

O [exemplo integral explicado](docs/revisao-situada-1.5.md) apresenta fontes com links/localizadores, contribuições, critérios, condições e limites. O [JSON reproduzível](experimental/v2/evidence/situated-report.json) conserva entradas, ações, verificações, ablações e hashes antes/depois. Também registra o refinamento condicionado das tarefas principais de produção e revisão, quando atribuídas à mesma pessoa e ao mesmo rascunho; comunicar genericamente não basta.

**Limite do repertório:** onze contratos não equivalem a onze composições completas. `PAD-PAPEIS-TURNOS-AUTORIA` permanece somente na auditoria por falta de aplicação admissível de critério. A alegação de consolidação da aprendizagem por jogo (`K37`) continua pendente; a parcela operacional trata apenas de feedback e conferência em atividade interativa já escolhida. Vínculos entre outros PAD ainda exigem curadoria específica.

O ditado é opcional. Quando o navegador não oferece processamento local disponível, uma confirmação informa que a voz pode ser enviada ao serviço de transcrição do navegador. O AMADO recebe o texto e não grava áudio. A organização anterior da interface continua em `amado/completo.html` e `amado/completo-guiado.html`, utilizando a mesma versão atual dos motores. A versão anterior completa permanece no histórico do repositório.

### Correção do entendimento de aulas remotas

Instrumento `AMADO-web-1.5.0-rc2-remote-intake1`, desenvolvido a partir do commit preservado `1ff173c1fb9bb5f02febe11091b2b6b5723dec14`. A base MADO, as afirmações documentais e os contratos de composição não foram alterados nesta correção.

- O relato distingue o total da turma, o subgrupo com TEA informado, quem conduz a explicação e familiares propostos como apoio. Diagnóstico não preenche habilidade de leitura, percepção, expressão ou dificuldade cognitiva.
- “Ministrar conteúdo” identifica uma ação; o tema da aula não seleciona uma resposta. Ensino remoto é uma condição registrada na situação, não evidência de computador, internet disponível ou AVA específico.
- A primeira rodada pergunta pelo acompanhamento/resposta dos estudantes e pelo material pretendido. As perguntas não dependem da existência de um cenário pronto; respostas desconhecidas não são repetidas nem confirmadas automaticamente.
- Sem orientação selecionada, `next_questions` apresenta os esclarecimentos reais ainda disponíveis; `unresolved_answers` conserva respostas desconhecidas para revisão, sem reabrir perguntas automaticamente. `intake_status` distingue esclarecimento disponível, contexto ainda desconhecido e limite desta consulta à base, sem prometer que mais respostas necessariamente resolverão uma lacuna operacional. Apoios parciais continuam visíveis.
- A menção genérica a celular identifica o dispositivo, não confirma orientação por áudio e vibração. Os sinônimos da interface deixaram de reunir indevidamente essas condições.

**Limite conferido:** reconhecer uma aula remota não autoriza gerar um plano didático completo. Quando uma dificuldade de sequência/retomada é explicitamente relatada, a operação existente de instruções consultáveis pode ser recuperada, com condições individuais e recursos a conferir. Isso não comprova uma combinação multimodal ou cobertura integral da aula. A orientação pedagógica elaborada na conversa não foi incorporada como resposta pronta.

Verificação reproduzível: `python -B -m unittest discover -s tests -p 'test_remote_*.py'` e `node tests/remote-browser.mjs`. Complementos usados para testar o percurso são identificados como sintéticos, separados do relato original, e não entram no pacote do navegador. A revisão também mantém a regressão dos casos anteriores.

## Registros históricos preservados

Os blocos abaixo documentam etapas anteriores. Foram mantidos para rastrear decisões e limitações, mas não descrevem o contrato nem a situação de entrega da candidata 1.5.

<details>
<summary>Histórico RC3 — seletor e adaptação da matriz funcional; descrição substituída pelo percurso situado acima</summary>

### Registro histórico: o que foi adaptado na RC3

Esta seção descreve a etapa anterior. A execução e os limites atuais são os do contrato situado descrito acima; nomes de campos históricos abaixo não substituem a evidência da revisão 1.5.

Não foi criada outra matriz nem uma resposta pronta para um assunto. O motor passa a consumir `functional_matrix`, dentro de `data/knowledge-base.json`, junto aos conhecimentos, critérios e articulações já existentes. A matriz é uma camada operacional curada; o reasoner OWL não interpreta o texto livre nem presume capacidades individuais.

| Etapa | O que o programa faz | Registro para conferir |
|---|---|---|
| **Relato** | Identifica termos controlados, participantes e fatos mencionados; solicita conferência | Contexto organizado e texto informado |
| **Conhecimento recuperado** | Reconhece sinais funcionais mapeados na matriz e recupera requisitos e conhecimentos vinculados | `access_requirements`: matriz, participante, sinal, fontes e trechos |
| **Condições** | Confronta as rotas existentes com recursos, papéis e impedimentos; prioriza percursos pertinentes que precisam de menos esclarecimentos | Verificações satisfeitas, pendentes ou incompatíveis |
| **Combinação** | Emprega os padrões existentes e suas aplicações exatas de critérios; desconhecido não significa disponível | Configuração selecionada ou condicional, conhecimentos e articulações utilizados |
| **Ação explicada** | Mostra um cartão por configuração e passos ligados à sua instrução original | `sintese_pratica.etapas[].passos`, componente, campo e fragmento de origem |

Por exemplo, uma descrição de acesso não visual pode recuperar **MF-01 → K10/K42** e os requisitos de acesso equivalente. Isso não preenche “usa leitor de tela”. Uma referência a dificuldade de ouvir mobiliza o registro auditivo **MF-11**, operacionalizado nesta mesma matriz com origens já existentes de **CA16/CA17**; não preenche “usa Libras” ou “compreende texto”. **MF-02** liga barreiras de operação explicitamente relatadas à necessidade de entrada alternativa. Os demais registros continuam na base, mas não são anunciados como reconhecedores de qualquer narrativa.

Os vínculos auditivos são delimitados pelas seções conferidas: alternativa para áudio gravado e legenda para áudio em vídeo gravado. Não comprovam uma solução para toda comunicação ao vivo. O padrão de acesso por leitor de tela não deve ser escolhido apenas porque uma pessoa surda precisa de alternativa à informação sonora. Em grupos mistos, os requisitos conservam seus participantes; uma rota não é apresentada como atendimento de todos.

Foi corrigida também uma omissão no índice de K10: **página web** não aparecia entre seus recursos digitais, embora o próprio conhecimento e seus registros WABlind tratem de conteúdo web. O vínculo existente foi completado no JSON e projetado no RDF, para não restringir a pergunta a apresentação ou imagem digital. Isso não cria outro conhecimento nem altera o tema da tarefa.

O tema — Matemática, História ou outro — contextualiza a atividade, não seleciona uma resposta cadastrada. Uma combinação desconhecida pode reutilizar um padrão existente. Isso não significa que toda tarefa esteja coberta: se faltam funções ou uma rota não está conferida, o apoio é parcial ou condicional, com a lacuna indicada.

</details>

<details>
<summary>Histórico intake1 / base 1.4.0-rc3 — fluxo e limites daquela entrega, não da revisão 1.5</summary>

### Como as perguntas avançam e como ler o resultado

**Revisão de entrada: `AMADO-web-1.4.0-rc3-intake1`.** A ontologia e a base de conhecimento permanecem na versão 1.4.0-rc3. Esta revisão adapta a interpretação, o diálogo e a edição do contexto; não acrescenta conhecimentos ou padrões para fazer um exemplo funcionar. A implementação anterior permanece no histórico (`f9f5eec`).

O percurso passa por **relato → entendimento → esclarecimentos necessários → revisão → confirmação**. Antes das perguntas, a pessoa confere uma síntese do que foi reconhecido. Relatar “ensinar a usar Google Forms” identifica um formulário, mas não confirma que a atividade seja ler conteúdo ou preencher respostas. A ação pretendida precisa ser esclarecida quando ambígua. O nome do produto e o tema da aula não selecionam uma resposta pronta.

Quem solicita pode realizar a atividade, apoiar alguém, preparar material ou orientar outra pessoa responsável. Essa relação é separada dos papéis dos participantes. Reconhecer “mediadora” não significa substituí-la por professora; “sou mediadora e quero conversar com o professor” não é uma única participação. Padrões realmente escolares continuam delimitados: não se pede que alguém assuma um papel ausente apenas para habilitar uma orientação.

As perguntas consideram primeiro ambiguidades de tarefa e participação. Quando o ambiente altera as opções, ele é esclarecido antes dos equipamentos. Sala de aula explicitamente informada não é perguntada novamente; “dar aula” sozinho não confirma presença física. Ambiente, material/aplicativo e equipamento são campos diferentes.

Cada pergunta identifica a atividade e, quando necessário, a pessoa ou o grupo a que se refere. A primeira rodada contém até três perguntas, podendo conter nenhuma. Uma resposta encerra essa pergunta no diálogo: não é necessário marcar todas as opções. “Ainda não sei” permite continuar sem transformar ausência de informação em confirmação. O indicador mostra a posição e o total da rodada; esclarecimentos adicionais são opcionais.

O limite da rodada pertence à interface (`web/amado/simple-flow.js`); a seleção das perguntas considera os percursos no motor e em `intake.mjs`. Não se reúnem automaticamente as exigências de todos os padrões. Escolher uma dificuldade não confirma as demais. O refinamento permite retomar pontos pendentes sem repetir automaticamente perguntas já respondidas.

**Revisar informações** abre os campos preenchidos e as lacunas. É possível completar um “não sei”, retirar ou substituir equipamento e corrigir participantes, ambiente ou atividade sem recomeçar a rodada. A edição substitui os valores do campo, em vez de somente acumular opções. Uma mudança invalida a orientação e exige nova confirmação; as respostas não afetadas são preservadas. Alterar e reinterpretar o relato original é uma ação distinta, pois pode mudar o contexto reconhecido.

A habilidade de uma pessoa para operar um recurso não comprova que esse recurso esteja disponível nesta atividade. Retirar um equipamento deixa sua disponibilidade em aberto sem apagar a habilidade pessoal. Informar que o equipamento está impedido exclui essa possibilidade; ausência de informação pode mantê-la apenas condicional. Remover uma pessoa interpretada indevidamente retira seus requisitos derivados, sem eliminar os requisitos das demais.

O progresso corresponde à execução: carregamento e conferência do pacote; recuperação na base RDF; verificações de condições e apoios; composição; apresentação do resultado. Cada solicitação possui sua identificação para não misturar mensagens de execuções diferentes. Na rota de composição por funções, recuperação e verificações são intercaladas: a mensagem informa essa operação conjunta, sem simular etapas separadas. Falha não é mostrada como conclusão. Não há porcentagem estimada, espera artificial ou leitura online de ABNT/WCAG durante a consulta.

As fontes exibidas junto ao resultado vêm dos apoios efetivamente usados, com referência, seção, paráfrase e link quando disponíveis. Fonte apenas cadastrada, recuperação sem autorização e leitura direta de documento são estados distintos. Acesso restrito ou conferência documental pendente permanecem explícitos.

A orientação começa por **O que você pode fazer**: uma ação por configuração, seus passos e as condições antes de aplicar. A ordem interna dos passos não transforma configurações independentes em um procedimento obrigatório. Cada passo conserva o fragmento da ação que o sustenta; a impressão digital da ação impede reaproveitar uma simplificação antiga após mudança da base. Não se acrescentam modalidades de outros cartões. Alternativas, acompanhamento, limites e fundamentos ficam no próprio bloco. Apoio parcial ou condicional continua identificado; não equivale a uma solução completa. [Fluxo de leitura e verificações](docs/visao-guiada.md).

A cobertura permanece delimitada: reconhecer o aplicativo, a tarefa ou a pessoa não garante uma configuração elegível. Falta de informação, falha de interpretação e ausência de padrão para a função requerida precisam ser distinguidas. Esta entrega não reorganiza toda a saída nem elimina seus aprofundamentos; a revisão em duas áreas (orientação prática e fundamentação técnica) é uma etapa posterior.

</details>

## Arquivos e reprodução

- `ontology/`: formalização e grafo da distribuição pública.
- `data/`: base pública estruturada e vocabulário de interface.
- `queries/`: consultas SPARQL das questões de competência.
- `shapes/`: restrições SHACL.
- `tests/` e `evidence/`: verificações e resultados desta revisão.
- `experimental/v2/`: compositor reutilizado, piloto preservado e relatório situado reproduzível.
- `web/`: documentação navegável e AMADO no navegador.

Os relatórios gerados em `evidence/` são a autoridade para saber **o que foi efetivamente executado**, em qual versão e com quais resultados. A descrição de um teste nesta documentação não equivale à sua aprovação.

## Alcance da contribuição

O projeto permite examinar a representação e o emprego rastreável do conhecimento no recorte implementado. Não demonstra compreensão automática de qualquer narrativa, cobertura de qualquer pessoa ou contexto, eficácia educacional ou acessibilidade integral da interface.

Consistência lógica, integridade dos dados, respostas às consultas, comportamento do motor e avaliação humana são verificações diferentes. Uma não substitui as outras.

## Autoria e referência

**Autora:** Natacsha Ordones Raposo de Melo.  
**Pesquisa:** *Arcabouço Multimodal para Acessibilidade Digital*.

Referência simples sugerida:

> MELO, Natacsha Ordones Raposo de. Arcabouço Multimodal para Acessibilidade Digital: representação MADO e instrumento AMADO. Versão 1.5.0-rc2 (candidata). Repositório do projeto.

Não há DOI exigido para consultar ou compreender este trabalho. Referências bibliográficas, autores de terceiros e perspectivas participantes conservam sua própria atribuição.

## Disponibilização

Não foi concedida licença aberta de reutilização nesta etapa. A disponibilização permite examinar a pesquisa; não deve ser interpretada como licença MIT, autorização geral para redistribuir os materiais ou transferência de direitos de terceiros. Dependências mantêm suas próprias licenças. [Condições e materiais omitidos](docs/direitos-e-privacidade.md).

[Consulte os componentes de terceiros e suas licenças](THIRD_PARTY.md), incluindo o runtime Pyodide, Python e os pacotes distribuídos.
