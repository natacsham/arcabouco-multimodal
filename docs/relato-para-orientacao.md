# Do relato à orientação: correção do aproveitamento da base

Esta revisão do AMADO parte de `8373e5f19666b510991f3f29b63d11c43c37dadf` e trabalha em `fix/narrative-to-actions`. A versão da base permanece MADO 1.5.0-rc1. Não altera a ontologia da tese, não cria outra matriz e não cadastra os relatos de teste como cenários do instrumento.

## O problema observado

Os 67 testes selecionados da entrada e composição existentes passaram no estado inicial. Entretanto, três relatos novos chegaram sem orientação. A inspeção distinguiu erros de interpretação, incompatibilidade entre identificadores dos módulos e limites reais do repertório.

- “Preciso preencher” não identificava a pessoa que realiza a tarefa, ao contrário de algumas construções iniciadas por “eu”.
- Produzir uma mensagem não era reconhecido como produção; revisar o texto não bastava para recuperar o percurso de produção e revisão já representado.
- Formas como “não consigo” e “não consegue” podiam receber tratamentos diferentes.
- Um recurso mencionado em uma intenção podia ser tratado como proposto, mesmo quando sua disponibilidade era declarada em outro trecho.
- O apoio à escolha de entrada de um formulário podia ser apresentado como completo sem cobrir as outras ações relatadas.

## Como se chega ao resultado

1. **Relato:** a interpretação determinística identifica ações e condições. Conserva o texto de origem e não deduz habilidade de um diagnóstico.
2. **Decomposição:** cada informação pertence a uma pessoa e a uma situação. A disponibilidade de um dispositivo não confirma sua compatibilidade nem o desempenho individual.
3. **Confirmação:** a pessoa corrige ou confirma o entendimento. O desconhecido permanece desconhecido; não vira aprovação para produzir uma resposta.
4. **Base consultada:** `data/knowledge-base.json` reúne conhecimentos, matriz funcional, contribuições, articulações e contratos das operações. A representação RDF e o piloto em `experimental/v2` são consultados com seus próprios fundamentos. Não há leitura de normas na internet durante o atendimento.
5. **Funções e condições:** o compositor relaciona necessidades confirmadas às funções representadas, confere recursos e fatos situados e conserva lacunas que não possuem operação.
6. **Combinação:** uma relação registrada precisa autorizar a passagem entre operações. No percurso de ditado e revisão, a fala produz um rascunho textual e a apresentação visual permite conferi-lo e corrigi-lo. A sequência utiliza o mesmo conteúdo; não se afirma complementaridade CARE apenas porque há fala e texto.
7. **Explicação:** o resultado apresenta ações, relação entre elas, fundamentos usados, condições pendentes e aquilo que não foi coberto. Cobrir as funções representadas não demonstra que toda a atividade humana está resolvida.

## O que esta correção não faz

- Não acrescenta respostas específicas de Matemática, História ou outro assunto.
- Não transforma referências bibliográficas ou afirmações pendentes em fundamento autorizado.
- Não cria automaticamente uma operação que ainda não está representada.
- Não apresenta uma execução sintética como avaliação da especialista, aprendizagem ou comprovação de acessibilidade.

## Verificação reproduzível

Os casos de instruções orais, formulário por teclado e mensagem por ditado ficam somente nos testes. Relatos originais e complementações sintéticas são separados. A repetição usa a mesma base; retirar recurso ou relação altera apenas a cópia em memória do teste.

### Resultado dos três relatos

| Relato de teste | Resultado após esclarecimentos sintéticos | Limite que permanece |
|---|---|---|
| Apresentação cujas instruções orais não podem ser retomadas | A observação agora mobiliza MF-04-G2 e a função de manter informação recuperável, para o grupo correto. | Os contratos existentes oferecem possibilidades condicionais de áudio/retorno háptico, não uma solução textual autorizada para este relato. A disponibilidade desses recursos e sua adequação não foram presumidas. |
| Preencher, revisar e enviar formulário por teclado | Apoio parcial à conferência da forma de entrada. | Não há cobertura demonstrada dos campos, tratamento dos erros, revisão e envio do formulário inteiro. O sistema não pede informações para esconder essa falta de operação. |
| Produzir mensagem por ditado e conferir o rascunho visualmente | Sequência conectada **capturar fala → revisar texto**, com o mesmo rascunho e relação `ProductionThenReview`. | A matriz também requer conferir a escolha da entrada; a equivalência entre essa função ampla e as operações do piloto não está documentada. Por isso o relato inteiro não recebe aprovação de cobertura completa. |

No terceiro teste, a entrada mobiliza `KInput`/`ArtInput`, apoiados nos registros de CARE e WCAG 2.1.1; a revisão mobiliza `KReview`/`ArtReview`, com MMI Requirements e WCAG 3.3.6. As referências, localizações e aplicações exatas aparecem no [relatório](../evidence/narrative-to-actions-report.json). O compositor não releu esses documentos durante a consulta nem realizou a síntese intelectual original.

Retirar o reconhecimento de fala elimina a captura e conserva apenas a revisão possível. Retirar a relação de produção–revisão, em memória, conserva operações isoladas, mas elimina a sequência. Isso demonstra dependência operacional da relação registrada, não eficácia educacional.

**Conclusão:** esta revisão corrige a ligação entre relato, matriz funcional e operações existentes, além de impedir declarações excessivas de cobertura. Não fecha, sozinha, a lacuna de abrangência do repertório. Para fechá-la, será necessário conferir nos conhecimentos já existentes as aplicações para retomada textual e a relação entre seleção da entrada e produção/revisão, antes de autorizar novos vínculos operacionais. Não basta acrescentar outra referência ou mudar uma mensagem de insuficiência.

### Reproduzir

Na revisão `AMADO-web-1.5.0-rc1-intake1`, passaram 301 testes Python e 52 verificações de navegador, incluindo equivalência entre execução local e navegador dos três relatos. A verificação SHACL encontrou zero violações e conservou 65 avisos documentais. Esses resultados verificam os contratos e os limites descritos acima; não significam três orientações completas nem avaliação humana. Os hashes e resultados detalhados estão nos relatórios de [verificação técnica](../evidence/technical-1.5-report.json) e [navegador](../evidence/situated-browser.json).

```sh
python -B scripts/check_narrative_to_actions.py --output evidence/narrative-to-actions-report.json
python -B -m unittest discover -s tests -p 'test_narrative_intake_regression.py'
python -B -m unittest discover -s tests -p 'test_composer_bridge_regression.py'
python -B experimental/v2/verify_situated.py --output experimental/v2/evidence/situated-report.json
python -B scripts/verify_public.py --report evidence/technical-1.5-report.json --reasoner-report evidence/reasoner-1.5-report.json
python -B scripts/build_web.py
node tests/situated-browser.mjs
```

O teste de navegador aceita `AMADO_CHROMIUM` e `AMADO_PYTHON` para instalações existentes. Não baixa navegadores. Reproduz os mesmos três relatos e esclarecimentos e compara os resultados com a execução Python, sem salvar casos de visitantes. Os relatórios identificam hashes, resultados e limites. A evidência anterior de OWL 2 DL/HermiT só é reutilizada quando o arquivo da ontologia tem exatamente o mesmo hash; isso não é uma nova execução do reasoner.
