# Duas apresentações do mesmo AMADO

A visão atual continua em `web/amado/index.html`. A visão guiada, em
`web/amado/guiado.html`, oferece um percurso em três etapas:

1. Começar pelo caso: adaptação pública da pesquisa, exemplo sintético ou narrativa.
2. Conferir as informações: revisar as condições e confirmar explicitamente.
3. Explorar a orientação: modos, funções, recursos, condições e fundamentos.

As duas páginas importam o mesmo `app.js`, cliente, Worker, motor, base e consultas.
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

`tests/guided.mjs` verifica o novo percurso e a equivalência do conteúdo com a visão
atual. `tests/site-presentation.mjs` cobre apresentação e navegação do site.
`tests/browser.mjs` mantém a regressão da visão atual. Os relatórios identificam
arquivos e execução local ou pública. Isso não constitui teste com participantes,
prova de aprendizagem ou declaração de conformidade integral de acessibilidade.

Nenhuma classe, relação, critério, conhecimento ou regra de decisão foi alterado
para criar esta apresentação. A versão da tese permanece separada.

## Revisão editorial e de leitura

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
