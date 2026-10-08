# Explicação do conhecimento e de seu emprego

O site distingue a síntese intelectual realizada na pesquisa da seleção e composição executadas pelo AMADO. A explicação pública não participa da seleção de conhecimentos nem modifica a decisão.

## Duas leituras por escolha

1. **Como este conhecimento foi construído:** contribuição documentada de cada fonte, operação de articulação, entendimento registrado, confirmação e limites.
2. **Por que foi usado aqui:** condições do caso, função necessária, apoio situado do critério, configuração, alternativa e verificações executadas.

Uma contribuição **conferida no registro da base** não significa que o documento original foi novamente examinado. Campos ausentes são apresentados como lacunas. IDs permitem a conferência técnica, mas não substituem o conteúdo nem a localização documental.

## Uma origem para as apresentações

`web/explanation.js` apresenta `result.explanation` e `result.execution_evidence`. É compartilhado pelas duas visões do AMADO e pelo exemplo preparado da Home. Não gera texto com modelo de linguagem, não cria relações e não modifica a base.

O exemplo da Home é uma projeção de uma execução preparada, produzida pela construção do pacote em `web/assets/explanation-pilot.json`. Não é uma nova validação humana. O arquivo é carregado ao abrir o bloco de fundamentos, sem iniciar Python ou o motor de decisões na Home.

As relações exibidas em tabela vêm de `explanation.graph`. As descrições de configurações vêm de `explanation.configurations`, ligadas por `component_id`; as verificações são resolvidas por `check_ids`. A presença conjunta de registros não é convertida em relação causal.

## Estados e limites

- **Orientação construída:** houve composição conforme o estado retornado pelo motor.
- **Orientação parcial:** existe uma saída, mas persistem funções requeridas sem cobertura declarada pelos padrões selecionados.
- **Decisão suspensa:** não há uma decisão sustentada para apresentar.
- **Não verificado pelo motor:** a condição está documentada, mas sua confirmação não foi executada.

Cobertura de funções declaradas, consistência técnica e verificações de composição não equivalem a sucesso observado, melhoria educacional ou acessibilidade integral. A adequação em uso requer avaliação própria.

## Organização e acessibilidade

São utilizados controles nativos `details`/`summary`, texto selecionável, tabelas com cabeçalhos e divulgação progressiva. O usuário pode explorar uma escolha de cada vez; alternar a leitura não gera uma nova decisão. Permanecem necessários testes de teclado, foco, ampliação e tecnologias assistivas. A implementação não declara conformidade integral de acessibilidade.
