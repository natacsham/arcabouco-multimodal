# MADO — Ontologia do Arcabouço Multimodal para Acessibilidade Digital

**Projeto de pesquisa de doutorado de Natacsha Ordones Raposo de Melo.**

Nesta pesquisa, construí a **MADO (Multimodal Accessibility Decision Ontology)** para representar conhecimentos sobre acessibilidade e interação multimodal, as relações entre eles e as condições em que podem orientar uma decisão. O **AMADO** é o instrumento que permite consultar essa representação e acompanhar a fundamentação de uma orientação.

**Versão deste projeto: 1.3.0-rc1 — candidata, posterior à versão da tese.** A tese V21 e a MADO 1.2.0-RC4 permanecem preservadas. Os resultados de avaliações anteriores não são automaticamente resultados desta revisão.

## Qual problema esta pesquisa enfrenta?

Conhecimentos úteis ficam distribuídos entre normas, publicações, estudos, artefatos, personas e resultados. Encontrar esses documentos não basta para decidir **como combinar formas de interação para uma pessoa, uma tarefa e determinadas condições**.

Investiguei a articulação desses conhecimentos: o que pode ser relacionado, o que essa relação permite compreender, em quais condições é pertinente e até onde pode ser empregado em uma nova decisão.

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

A página pública reúne [**Entenda a MADO**](https://natacsham.github.io/MADO/), [**Explore a ontologia**](https://natacsham.github.io/MADO/ontologia/) e [**Experimente o AMADO**](https://natacsham.github.io/MADO/amado/). A publicação é condicionada ao sucesso das verificações no fluxo do GitHub Pages.

## O que é conhecimento multimodal articulado?

Não é apenas um conjunto de citações nem um resumo de um artigo. Na pesquisa, construí essa compreensão ao relacionar conteúdos e registrar convergências, complementações, condições, refinamentos e limites.

Um exemplo é relacionar a necessidade de **retomar uma explicação**, a **preservação do significado entre formatos** e a **organização da atenção**. Essa articulação pode fundamentar uma configuração em que a fala preserva a expressão da pessoa, o texto mantém pontos recuperáveis e a imagem representa relações, cada qual com função e condições explícitas.

O AMADO não descobre essa síntese intelectual sozinho. Ele consulta articulações previamente documentadas e verifica se os conhecimentos e os padrões disponíveis podem ser empregados no contexto informado. [Veja o exemplo e seus limites](docs/exemplo-rastreavel.md).

## O que torna a orientação multimodal?

A orientação precisa dizer **qual função cada modo cumpre, como os modos se relacionam e o que fazer se uma rota não for viável**. Ter texto, áudio e vídeo na mesma tela não demonstra, por si só, integração multimodal ou acessibilidade.

O modelo diferencia modo de interação, recurso digital, dispositivo e responsável. Um smartphone não é uma modalidade; vídeo pode reunir representações visuais e sonoras; participação de diferentes pessoas não substitui a explicação da relação entre os modos.

## Como funciona, sem LLM

1. O contexto é organizado em conceitos representados na base e conferido pela pessoa usuária.
2. Consultas recuperam conhecimentos pertinentes e articulações documentadas.
3. O motor verifica condições de aplicação, restrições, recursos e fundamentação.
4. Critérios e padrões elegíveis orientam a composição das configurações modais.
5. A orientação apresenta funções, recursos, responsáveis, alternativas, limites e o caminho até as fontes.

**Encontrar conhecimento não significa autorizar seu uso.** Ausência de informações ou de sustentação pode produzir perguntas, condições pendentes ou suspensão da decisão.

O AMADO executa Python no navegador por Pyodide, com RDF e consultas SPARQL. Não há servidor de decisões nem chamada a modelo de linguagem. A ontologia não gera prosa sozinha: o compositor emprega padrões e formulações previamente documentados. A narrativa livre também tem cobertura limitada e exige confirmação.

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

> MELO, Natacsha Ordones Raposo de. MADO — Ontologia do Arcabouço Multimodal para Acessibilidade Digital: ontologia e instrumento AMADO. Versão 1.3.0-rc1. Repositório do projeto.

Não há DOI exigido para consultar ou compreender este trabalho. Referências bibliográficas, autores de terceiros e perspectivas participantes conservam sua própria atribuição.

## Disponibilização

Não foi concedida licença aberta de reutilização nesta etapa. A disponibilização permite examinar a pesquisa; não deve ser interpretada como licença MIT, autorização geral para redistribuir os materiais ou transferência de direitos de terceiros. Dependências mantêm suas próprias licenças. [Condições e materiais omitidos](docs/direitos-e-privacidade.md).

[Consulte os componentes de terceiros e suas licenças](THIRD_PARTY.md), incluindo o runtime Pyodide, Python e os pacotes distribuídos.
