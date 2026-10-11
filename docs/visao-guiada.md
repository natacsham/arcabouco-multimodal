# Percurso de perguntas e leitura do AMADO

## Entrada atual — 1.4.0-rc2

`web/amado/index.html` e `web/amado/guiado.html` compartilham a entrada simplificada,
implementada em `simple-flow.js` com projeções de perguntas em `intake.mjs`.
A apresentação completa anterior permanece em `completo.html` e
`completo-guiado.html`; todos consultam os mesmos motores e a mesma base.

1. **Descrever o desafio:** texto ou ditado; exemplos opcionais.
2. **Completar uma informação por vez:** atividade e participante aparecem junto
   da pergunta. O indicador informa a posição e o total previsto, ajustado conforme
   as respostas. A pessoa pode responder que não sabe ou seguir sem as demais informações.
3. **Confirmar:** rever o caso e autorizar a geração da orientação.
4. **Ler o resultado:** ação, combinação modal e condição de uso em cartões;
   cuidados, alternativas, acompanhamento e fundamentos sob demanda.

### Correção da repetição — 11/10/2026

Na revisão `46e318a`, foi reproduzido o seguinte percurso sintético: narrativa
sobre uma turma, tarefa `TAR-ORGANIZAR-CONTEUDO-DIGITAL` e seleção somente de
`BAR-CONTEUDO-SEM-ESTRUTURA-PERSISTENTE`. O motor retornava requisitos de outros
padrões; a interface reapresentava `barreira_ou_necessidade` porque filtrava apenas
perguntas puladas, não as respondidas. O percurso anterior de teste não cobria essa
seleção isolada.

A interface agora registra perguntas respondidas e campos complementares já
tratados, somente em memória. Isso encerra o passo do diálogo, **não aprova os
requisitos restantes**. Opções não marcadas permanecem desconhecidas. A resposta
textual “não sei” não é salva como apoio positivo. Completar lacunas depois do
resultado exige uma ação explícita da pessoa.

O campo de comunicação complementar aparece uma vez por participante. “Jogo”
não é uma resposta à pergunta sobre como alguém percebe o conteúdo; foi retirado
somente dessas opções pessoais. Continua na base e como recurso em configurações
para as quais é pertinente. Vídeo também permanece disponível.

### Resultado e preservação

Cada cartão projeta as etapas e configurações já devolvidas pelo motor. O resumo
não altera os conhecimentos, critérios, alternativas ou estados. Condições de uso
ficam visíveis; explicações extensas ficam recolhidas. O compositor apresenta
separadamente suas opções completas, parciais e pendentes, sem ocultar uma categoria
quando outra existe. Suspensão real não é apresentada como apoio parcial.

`tests/simple-flow-browser.mjs` verifica o percurso e a equivalência decisória
com execução nativa; `tests/public-smoke.mjs` confere o endereço publicado.
Consultar os respectivos relatórios em `evidence/` para resultados, hashes e
limites. São verificações sintéticas, não avaliação com participantes ou
declaração de conformidade integral WCAG. Ontologia, base e regras não foram
alteradas nesta correção da interface.

## Histórico: apresentações completas

Na apresentação original, `web/amado/index.html` era a visão completa e
`web/amado/guiado.html` oferecia um percurso em três etapas. Essas páginas
foram preservadas em `completo.html` e `completo-guiado.html`:

1. Começar pelo caso: adaptação pública da pesquisa, exemplo sintético ou narrativa.
2. Conferir as informações: revisar as condições e confirmar explicitamente.
3. Explorar a orientação: modos, funções, recursos, condições e fundamentos.

As duas apresentações completas importam o mesmo `app.js`, cliente, Worker, motor, base e consultas.
`guided.js` somente organiza a leitura do DOM produzido pelo aplicativo: não chama
o motor, não cria textos decisórios, não confirma campos e não salva o caso.
Alterações nos dados continuam invalidando a decisão pelo comportamento original.
Voltar a uma etapa mantém o caso temporário; mudar de apresentação abre outro
documento e descarta o caso anterior. Não há migração nem armazenamento entre visões.

## Informação preservada

Cada configuração recolhida mantém título, modos, função e situação dos recursos.
Ao abrir, apresenta os mesmos textos sobre complementaridade, ações, condições,
alternativas e acompanhamento. Informações ausentes, suspensão, resultado esperado
e seu limite permanecem separados da fundamentação técnica.

Os controles existentes conservam seus identificadores para usar o mesmo código.
Os passos são botões em uma navegação, não novas abas ARIA do aplicativo. Os links
“Visão atual” e “Visão guiada” são navegação entre páginas. Ajustes de leitura,
limpeza, mensagens de erro e interrupção de fala continuam disponíveis.

## Verificação

Na **1.4.0-rc1**, ambas as apresentações usam também `explanation.js`, com as leituras de construção e aplicação derivadas do mesmo retorno do motor. A comparação mostra os apoios acrescentados por articulação, inclusive quando a configuração já era selecionada sem essa expansão. Os testes atuais são `tests/traceability-browser.mjs` e `tests/compare_browser.mjs`; seus resultados são vinculados no índice `web/evidence/report.json`. Consultar [verificação e limites](verificacao.md).

## Histórico: criação da visão guiada na 1.3

Os testes, commits e declarações de preservação abaixo descrevem a apresentação **1.3**, no repositório de origem. Não demonstram que o motor ou a base permaneceram inalterados na evolução 1.4, nem constituem seus resultados atuais.

`tests/guided.mjs` verifica o novo percurso e a equivalência do conteúdo com a visão
atual. `tests/site-presentation.mjs` cobre apresentação e navegação do site.
`tests/browser.mjs` mantém a regressão da visão atual. Os relatórios identificam
arquivos e execução local ou pública. Isso não constitui teste com participantes,
prova de aprendizagem ou declaração de conformidade integral de acessibilidade.

Nenhuma classe, relação, critério, conhecimento ou regra de decisão foi alterado
para criar esta apresentação. A versão da tese permanece separada.

## Histórico: revisão editorial e de leitura da 1.3

A revisão aprovada em 7 de outubro de 2026 mantém os dois percursos e ajusta a
tipografia de ambos. O tamanho original usa a preferência-base do navegador
(normalmente 16 px); o controle de leitura continua permitindo ampliação até
200%. Modalidades, recursos, disponibilidade e condições essenciais não são
tratados como notas pequenas. Títulos usam unidades relativas e parágrafos da
orientação deixam de receber negrito contínuo.

A Home apresenta o objetivo e um exemplo de aplicação, sem limitar a MADO aos
formatos usados nesse exemplo. A documentação técnica acrescenta uma sequência
em HTML, distinguindo o conhecimento previamente registrado da confirmação,
consulta e composição realizadas no AMADO. O diagrama descreve o funcionamento;
não é uma execução do motor nem uma nova evidência de eficácia.

O commit `9445c51` preserva a apresentação anterior a esta revisão. Motor, base,
consultas e conteúdo das decisões permanecem inalterados. As verificações de
layout e leitura desta revisão são registradas separadamente das evidências da
tese e não constituem avaliação com participantes.
