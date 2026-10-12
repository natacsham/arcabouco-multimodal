# Arcabouço Multimodal para Acessibilidade Digital

**Projeto de pesquisa de doutorado de Natacsha Ordones Raposo de Melo.**

O **Arcabouço Multimodal para Acessibilidade Digital** organiza a articulação e o emprego de conhecimentos para apoiar decisões de interação. A **MADO (Multimodal Accessibility Decision Ontology)** representa esses conhecimentos, suas relações, critérios e condições. O **AMADO** é o instrumento que consulta a base e apresenta orientações com fundamentação rastreável.

**Versão deste projeto: 1.4.0-rc3 — candidata.** Este repositório dá continuidade à distribuição pública sem modificar o repositório e o site MADO anteriores. A versão da tese permanece preservada. Os resultados de avaliações anteriores não são automaticamente resultados desta revisão.

**Este é o projeto em desenvolvimento.** As melhorias da ontologia e do AMADO são integradas aqui, em `arcabouco-multimodal`; não existe um produto separado chamado “Evolution”. O repositório `MADO` anterior permanece preservado. A versão 1.4 da base e o módulo de composição 2.0.0-alpha2 têm identificadores distintos para permitir conferir exatamente o que foi executado.

No AMADO, conte seu desafio por texto ou ditado, responda às perguntas necessárias e confira as informações antes de gerar a orientação. Os exemplos são opcionais. Escrita com revisão e revisão de texto usam o compositor por funções; acesso a conteúdo e demais tarefas seguem o motor existente, conforme sua cobertura. Tema da aula não é chave de busca, e condições pessoais são conferidas por participante. A interpretação é limitada e precisa de confirmação. [Como usar e o que já está coberto](docs/composicao-por-funcoes.md).

## Qual problema esta pesquisa enfrenta?

Conhecimentos úteis ficam distribuídos entre normas, publicações, estudos, artefatos, personas e resultados. Encontrar esses documentos não basta para decidir **como combinar formas de interação para uma pessoa, uma tarefa e determinadas condições**.

O foco da pesquisa é a articulação desses conhecimentos: o que pode ser relacionado, o que essa relação permite compreender, em quais condições é pertinente e até onde pode ser empregado em uma nova decisão.

| Elemento | Papel no projeto |
| --- | --- |
| **Arcabouço Multimodal para Acessibilidade Digital** | Organiza o raciocínio da pesquisa e sua trajetória cumulativa. |
| **MADO** | Representa semanticamente conhecimentos, articulações, critérios, contextos, decisões e proveniência. |
| **AMADO** | Recupera e seleciona conhecimentos e padrões compatíveis, compõe uma orientação e apresenta sua rastreabilidade. |

## Comece por aqui

- [Entenda a MADO em linguagem simples](docs/entenda-mado.md).
- [Acompanhe um exemplo real da base](docs/exemplo-rastreavel.md).
- [Veja o teste de uma combinação não cadastrada e seus limites](docs/teste-de-reutilizacao.md).
- [Conheça as classes e as camadas de execução](docs/modelo.md).
- [Confira o que muda nesta revisão](docs/revisao.md).
- [Consulte verificações, limites e evidências](docs/verificacao.md).
- [Leia as condições de disponibilização e privacidade](docs/direitos-e-privacidade.md).
- [Execute e reproduza as verificações](docs/reproduzir.md).
- [Confira as licenças dos componentes de terceiros](THIRD_PARTY.md).

Os endereços públicos reúnem [**A pesquisa**](https://natacsham.github.io/arcabouco-multimodal/), [**Documentação técnica da MADO**](https://natacsham.github.io/arcabouco-multimodal/ontologia/) e [**Experimente o AMADO**](https://natacsham.github.io/arcabouco-multimodal/amado/). A publicação é condicionada ao sucesso das verificações no fluxo do GitHub Pages. A [conferência do endereço publicado](evidence/public-smoke.json) identifica separadamente a revisão e os fluxos realmente executados.

Cada escolha pode ser examinada por duas leituras: **como seu conhecimento foi construído** e **por que ele foi empregado naquele caso**. Ambas usam os mesmos registros, distinguindo contribuição da fonte, operação de articulação, conhecimento, aplicação do critério e limite. Contribuição não detalhada permanece como lacuna, sem justificativa inventada. [Contrato da explicação pública](docs/explicacao-publica.md).

## O que é conhecimento multimodal articulado?

Não é apenas um conjunto de citações nem um resumo de um artigo. É a compreensão produzida ao relacionar conteúdos e registrar convergências, complementações, condições, refinamentos e limites.

Um exemplo é relacionar a necessidade de **retomar uma explicação**, a **preservação do significado entre formatos** e a **organização da atenção**. Essa articulação pode fundamentar uma configuração em que a fala preserva a expressão da pessoa, o texto mantém pontos recuperáveis e a imagem representa relações, cada qual com função e condições explícitas.

O AMADO não descobre essa síntese intelectual sozinho. Ele consulta articulações previamente documentadas e verifica se os conhecimentos e os padrões disponíveis podem ser empregados no contexto informado. [Veja o exemplo e seus limites](docs/exemplo-rastreavel.md).

## O que torna a orientação multimodal?

A orientação precisa dizer **qual função cada modo cumpre, como os modos se relacionam e o que fazer se uma rota não for viável**. Ter texto, áudio e vídeo na mesma tela não demonstra, por si só, integração multimodal ou acessibilidade.

O modelo diferencia modo de interação, recurso digital, dispositivo e responsável. Um smartphone não é uma modalidade; vídeo pode reunir representações visuais e sonoras; participação de diferentes pessoas não substitui a explicação da relação entre os modos.

## Como funciona, sem LLM

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
4. **Operacionalizar:** adaptar os vínculos existentes em `decision_components` e nos contratos versionados de `experimental/v2/trajectory-bindings.json`. Uma função só integra a orientação se suas condições e apoios forem satisfeitos; ter uma fonte a mais não cria automaticamente uma capacidade.
5. **Publicar:** regenerar RDF, catálogo, piloto e pacote; reexecutar as verificações; publicar somente os arquivos públicos. O navegador consome a mesma versão empacotada da base, não uma segunda planilha explicativa.

O [catálogo e o desenho do percurso](https://natacsham.github.io/arcabouco-multimodal/ontologia/#fontes) são projeções desses registros. A conferência desta revisão é parcial: sete origens WCAG/MMI receberam seção e versão verificadas; outras referências permanecem citadas ou pendentes. O acesso restrito a uma norma não é tratado como leitura concluída. [O que foi conferido e como reproduzir](docs/fundamentacao-documental.md).

1. O contexto é organizado em conceitos representados na base e conferido pela pessoa usuária.
2. Consultas recuperam conhecimentos pertinentes e articulações documentadas.
3. O motor verifica condições de aplicação, restrições, recursos e fundamentação.
4. Critérios e padrões elegíveis orientam a composição das configurações modais.
5. A orientação apresenta funções, recursos, responsáveis, alternativas, limites e o caminho até as fontes.

**Encontrar conhecimento não significa autorizar seu uso.** Ausência de informações ou de sustentação pode produzir perguntas, condições pendentes ou suspensão da decisão.

O AMADO executa Python no navegador por Pyodide, com RDF e consultas SPARQL. Não há servidor de decisões nem chamada a modelo de linguagem. A ontologia não gera prosa sozinha: o compositor emprega padrões e formulações previamente documentados. A narrativa livre também tem cobertura limitada e exige confirmação.

O ditado é opcional. Quando o navegador não oferece processamento local disponível, uma confirmação informa que a voz pode ser enviada ao serviço de transcrição do navegador. O AMADO recebe o texto e não grava áudio. A organização anterior da interface continua em `amado/completo.html` e `amado/completo-guiado.html`, utilizando a mesma versão atual dos motores. A versão anterior completa permanece no histórico do repositório.

### Da descrição à ação: o que foi adaptado na RC3

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

### Como as perguntas avançam e como ler o resultado

Cada pergunta identifica a atividade e, quando necessário, a pessoa ou o grupo a que se refere. A primeira rodada contém até três perguntas, podendo conter nenhuma. Uma resposta encerra essa pergunta no diálogo: não é necessário marcar todas as opções. “Ainda não sei” permite continuar sem transformar ausência de informação em confirmação. O indicador mostra a posição e o total da rodada; esclarecimentos adicionais são opcionais.

O limite da rodada pertence à interface (`web/amado/simple-flow.js`); a seleção das perguntas considera os percursos no motor e em `intake.mjs`. Não se reúnem automaticamente as exigências de todos os padrões. Escolher uma dificuldade não confirma as demais. O refinamento permite retomar pontos pendentes sem repetir automaticamente perguntas já respondidas.

A orientação começa por **O que você pode fazer**: uma ação por configuração, seus passos e as condições antes de aplicar. A ordem interna dos passos não transforma configurações independentes em um procedimento obrigatório. Cada passo conserva o fragmento da ação que o sustenta; a impressão digital da ação impede reaproveitar uma simplificação antiga após mudança da base. Não se acrescentam modalidades de outros cartões. Alternativas, acompanhamento, limites e fundamentos ficam no próprio bloco. Apoio parcial ou condicional continua identificado; não equivale a uma solução completa. [Fluxo de leitura e verificações](docs/visao-guiada.md).

## Arquivos e reprodução

- `ontology/`: formalização e grafo da distribuição pública.
- `data/`: base pública estruturada e vocabulário de interface.
- `queries/`: consultas SPARQL das questões de competência.
- `shapes/`: restrições SHACL.
- `tests/` e `evidence/`: verificações e resultados desta revisão.
- `web/`: documentação navegável e AMADO no navegador.

Os relatórios gerados em `evidence/` são a autoridade para saber **o que foi efetivamente executado**, em qual versão e com quais resultados. A descrição de um teste nesta documentação não equivale à sua aprovação.

## Alcance da contribuição

O projeto permite examinar a representação e o emprego rastreável do conhecimento no recorte implementado. Não demonstra compreensão automática de qualquer narrativa, cobertura de qualquer pessoa ou contexto, eficácia educacional ou acessibilidade integral da interface.

Consistência lógica, integridade dos dados, respostas às consultas, comportamento do motor e avaliação humana são verificações diferentes. Uma não substitui as outras.

## Autoria e referência

**Autora:** Natacsha Ordones Raposo de Melo.  
**Pesquisa:** *Arcabouço Multimodal para Acessibilidade Digital*.

Referência simples sugerida:

> MELO, Natacsha Ordones Raposo de. Arcabouço Multimodal para Acessibilidade Digital: representação MADO e instrumento AMADO. Versão 1.4.0-rc3. Repositório do projeto.

Não há DOI exigido para consultar ou compreender este trabalho. Referências bibliográficas, autores de terceiros e perspectivas participantes conservam sua própria atribuição.

## Disponibilização

Não foi concedida licença aberta de reutilização nesta etapa. A disponibilização permite examinar a pesquisa; não deve ser interpretada como licença MIT, autorização geral para redistribuir os materiais ou transferência de direitos de terceiros. Dependências mantêm suas próprias licenças. [Condições e materiais omitidos](docs/direitos-e-privacidade.md).

[Consulte os componentes de terceiros e suas licenças](THIRD_PARTY.md), incluindo o runtime Pyodide, Python e os pacotes distribuídos.
