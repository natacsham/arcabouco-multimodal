# Explicação do conhecimento e de seu emprego

O site distingue a síntese intelectual realizada na pesquisa da seleção e composição executadas pelo AMADO. A explicação pública não participa da seleção de conhecimentos nem modifica a decisão.

## Escolha e motivo juntos

O contexto é apresentado em quatro grupos: pessoas e participação; atividade e objetivo; dificuldades e apoio necessário; recursos e condições. A síntese usa informações registradas e não atribui uma característica a um participante quando essa associação não está disponível.

Cada configuração aparece uma única vez, com ação, função e motivo próximos. A primeira escolha fica aberta; as demais mantêm título, função, modos e estado visíveis. A orientação integral é uma leitura alternativa, e não outra lista de escolhas.

O percurso de cada escolha distingue:

1. **O que fazer:** ações e função das formas de interação registradas.
2. **Por que neste caso:** correspondências que recuperaram conhecimento; condições conferidas para a seleção; conhecimento empregado; aplicação exata do critério.
3. **Como esse conhecimento foi construído:** contribuição documentada de cada fonte, operação de articulação, entendimento registrado, confirmação e limites.
4. **Condições de aplicação:** recursos, alternativas, acompanhamento e informações ainda não verificadas.

Construção histórica, articulações efetivamente percorridas e relações não confirmadas permanecem separadas. O grafo local e seus registros textuais ficam disponíveis dentro da mesma escolha.

Uma contribuição **conferida no registro da base** não significa que o documento original foi novamente examinado. Campos ausentes são apresentados como lacunas. IDs permitem a conferência técnica, mas não substituem o conteúdo nem a localização documental.

## Uma origem para as apresentações

`web/explanation.js` apresenta `result.explanation` e `result.execution_evidence`. É compartilhado pelas duas visões do AMADO e pelo exemplo preparado da Home. Não gera texto com modelo de linguagem, não cria relações e não modifica a base.

O exemplo da Home é uma projeção de uma execução preparada, produzida pela construção do pacote em `web/assets/explanation-pilot.json`. Não é uma nova validação humana. O arquivo é carregado ao abrir o bloco de fundamentos, sem iniciar Python ou o motor de decisões na Home.

As relações exibidas em tabela vêm de `explanation.graph`. As descrições de configurações vêm de `explanation.configurations`, ligadas por `component_id`; as verificações são resolvidas por `check_ids`. A presença conjunta de registros não é convertida em relação causal.

`projectConfiguration` é uma projeção pura desses registros. Não acrescenta condições de seleção, não infere necessidades e não modifica a execução. Os papéis exigidos são mostrados pelas verificações existentes, mesmo quando não aparecem na lista de correspondências do contexto. Grupos com alternativas são identificados como tais; itens encontrados não são apresentados como uma conjunção obrigatória.

O objetivo textual pode descrever o caso sem ter sido semanticamente testado na seleção. Características utilizadas na recuperação também não são automaticamente requisitos de todas as escolhas.

## O efeito real da articulação

A comparação usa o resultado registrado em `articulation_comparison`, e não uma conclusão escrita pela interface:

- **Nova escolha acrescentada:** a configuração aparece na execução com articulações e não na execução isolada.
- **Fundamentação ampliada:** a configuração já existia, mas recebeu novos pares de critério, conhecimento e origem.
- **Sem diferença registrada:** a comparação foi executada, sem acréscimo registrado para essa escolha.
- **Comparação não executada:** não há dados suficientes de comparação; nenhum efeito é presumido.

No exemplo da organização de conteúdo persistente, K38 e K43 acrescentam apoio a CA02. A escolha já estava presente na execução isolada. Portanto, esse exemplo demonstra ampliação da fundamentação, não criação de uma configuração nova nem eficácia educacional.

## Estados e limites

- **Orientação construída:** houve composição conforme o estado retornado pelo motor.
- **Orientação parcial:** existe uma saída, mas persistem funções requeridas sem cobertura declarada pelos padrões selecionados.
- **Decisão suspensa:** não há uma decisão sustentada para apresentar.
- **Não verificado pelo motor:** a condição está documentada, mas sua confirmação não foi executada.

Cobertura de funções declaradas, consistência técnica e verificações de composição não equivalem a sucesso observado, melhoria educacional ou acessibilidade integral. A adequação em uso requer avaliação própria.

## Organização e acessibilidade

São utilizados controles nativos `details`/`summary`, texto selecionável, tabelas com cabeçalhos e divulgação progressiva. O usuário pode explorar uma escolha de cada vez; alternar a leitura não gera uma nova decisão. Permanecem necessários testes de teclado, foco, ampliação e tecnologias assistivas. A implementação não declara conformidade integral de acessibilidade.

Para revisar a compreensão, a pessoa deve conseguir localizar: a condição considerada; a contribuição do conhecimento; a função dos modos; o fundamento da escolha; e os limites de aplicação. Essa revisão de leitura é distinta dos testes de fidelidade do código e não é declarada como avaliação humana já realizada.
