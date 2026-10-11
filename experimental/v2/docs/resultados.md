# Resultados do piloto V2

Verificação executada em 10/10/2026. Todos os casos são sintéticos; não são registros de uma sessão com especialista.

## Resultado central

Com o motor, as quatro capacidades, as duas tarefas e a regra de sequência inalterados entre as duas execuções, uma extensão de 25 triplas habilitou a revisão por leitura em voz. Na alpha2, a base inicial tem 366 triplas e a base com extensão tem 391, incluindo o esquema. Duas condições de disponibilidade do conteúdo foram acrescentadas em relação à alpha1, que permanece no histórico.

| Condições confirmadas | Sem extensão | Com extensão |
|---|---|---|
| Fala viável e revisão visual viável | Fala → texto visual | Mesmo percurso continua viável |
| Teclado viável, revisão visual impedida, áudio e correção viáveis | Insuficiência | Teclado → revisão por leitura em voz |
| Todas as entradas e revisões viáveis | 2 percursos | 4 percursos |
| Caso teclado–áudio com saída de áudio impedida | Insuficiência | Insuficiência |
| Caso teclado–áudio sem confirmação da correção | Insuficiência | 1 candidata pendente, nenhuma pronta |

Retirar a extensão devolveu o resultado de insuficiência no caso teclado–áudio. Acrescentar somente uma referência bibliográfica não habilitou a composição. Não há par completo teclado–áudio cadastrado como cenário ou configuração no motor: as etapas foram ligadas pela função e pelo rascunho textual compartilhado.

## Como os conhecimentos participaram

1. `KInput` fundamentou a escrita como entrada operável para produzir um rascunho, com apoio nas contribuições CARE/teclado e com o antecedente K41 mantido como registro legado.
2. `KAudioReview` fundamentou a apresentação desse rascunho por leitura em voz, relacionando independência entre entrada/saída aos requisitos de conferência, controle e correção. Esse é o incremento habilitado pela extensão.
3. `KReview` fundamentou a ligação entre produzir e revisar o mesmo conteúdo, não apenas a presença simultânea de escrita e áudio.
4. O motor confrontou recursos e condições com cada capacidade e com a relação. Áudio impedido ou correção desconhecida alteraram o resultado.

A síntese analítica dos conhecimentos foi registrada previamente. A execução verificou registros e condições; não releu publicações, não descobriu a articulação e não observou a pessoa realizar a tarefa.

## Verificações executadas

- **71/71 testes integrados da alpha2:** 38 do compositor original, 9 de resultados parciais/condicionais e 24 da ponte com os registros reais. Incluem composição, ablação, bibliografia isolada, recursos impedidos, condições ausentes, transições incompatíveis, integridade documental e determinismo.
- **SHACL:** conformidade na base e na extensão; seis mutações negativas rejeitadas.
- **SPARQL:** consultas de fundamentos e relações com os resultados esperados: 9/11 linhas de contribuição às aplicações antes/depois da extensão e uma relação funcional. Não são 11 conhecimentos distintos.
- **OWL 2 DL e HermiT:** perfil e consistência aprovados para o arquivo combinado cujo hash consta no relatório. Isso não comprova adequação em uso.
- **Oito execuções sintéticas:** resultados correspondentes ao esperado, registrados em `verification.json`.
- **Motor público preservado:** sua suíte `python -B -m unittest discover -s tests -p test_engine.py` foi executada separadamente, com 17/17 testes aprovados. A execução emitiu avisos de depreciação do analisador SPARQL existente; nenhum erro de teste.

Os arquivos do motor, ontologia, consultas e base anteriores foram conferidos por hash antes/depois da verificação. As alterações de interface preexistentes ficaram fora desta entrega; não houve substituição do site.

## O que esta evidência permite afirmar

O piloto demonstra **recombinação de capacidades já representadas, autorizada por conhecimento e relações documentadas**, com explicação e bloqueios examináveis. É um avanço em relação à seleção exclusiva de configurações completas por padrões.

O experimento foi construído deliberadamente para comparar uma capacidade sem fundamento autorizado com a mesma capacidade após esse fundamento ser acrescentado. Portanto, não demonstra capacidade de descobrir novas operações ao ler qualquer diretriz, nem prova que quatro opções sejam melhores que duas.

Não foram realizados novos testes com participantes, avaliação da interface V2, comparação com aprendizagem ou validação clínica. A revisão semântica pela autora e a integração ao AMADO público continuam etapas separadas.

## Evidências reproduzíveis

- [Relatório da verificação](../evidence/verification.json)
- [Rastreabilidade completa do caso teclado–áudio](../evidence/novel-case-trace.json)
- [Relatório OWL/HermiT](../evidence/reasoner-report.json)
- [Questões e limites do piloto](../project/competency-questions.csv)
- [Arquivos e instruções](../README.md)

## Reutilização dos registros reais da pesquisa na alpha2

A ponte lê K28, K29 e K41, seus trechos e fontes, e CA38 com sua origem pertinente. Esses registros não são promovidos a conferência dos documentos originais. As aplicações operacionais propostas mantêm a distinção entre antecedentes da trajetória e fundamentos primários do piloto.

O grafo projetado tem **665 triplas**, passa em SHACL e nas três consultas de fundamentação, relações e trajetória. Quatro alterações inválidas do grafo foram rejeitadas. OWL 2 DL e HermiT foram executados separadamente para esse grafo, com o hash registrado em `trajectory-reasoner-report.json`.

| Condição sintética testada | Resultado verificado |
|---|---|
| Escrita viável, voz impedida, revisão auditiva viável | Escrita → revisão do mesmo conteúdo por leitura em voz |
| Mesmo caso, sem aplicação fundamentada da revisão auditiva | Apoio parcial à escrita, sem proposta completa |
| Áudio impedido e revisão visual confirmada | Escrita → revisão visual |
| Esforço da escrita não informado | Candidata condicional e pergunta sobre a viabilidade dessa entrada |
| Correção impossível | Apoio parcial à produção do rascunho, sem alegar revisão resolvida |
| Entrada por teclado impossível | Possibilidade parcial de revisão, dependente de rascunho ainda não produzido |

Um teste adicional removeu os contextos, decisões, configurações completas e cenários preparados de uma **cópia temporária da base**. A composição continuou a mesma. Isso demonstra independência desses registros prontos neste recorte; não demonstra independência das quatro capacidades, das condições e da relação previamente modeladas.

A auditoria independente encontrou duas falhas e motivou regressões: faltava verificar a existência de conteúdo na tarefa de revisão; e os apoios parciais/condicionais não carregavam todos os seus registros de proveniência. Ambas foram corrigidas. A informação ausente passa a gerar uma condição pendente, e a rastreabilidade fica separada por proposta completa, candidata ou segmento parcial.

Não foi implementado o envio da mensagem nem seu retorno de status. A orientação desta ponte cobre produção e revisão, não toda a comunicação digital. A versão pública e a tese não foram modificadas.

- [Evidências da ponte e seis execuções](../evidence/trajectory-report.json)
- [Verificação lógica da ponte](../evidence/trajectory-reasoner-report.json)
- [Explicação da relação com a trajetória](reutilizacao-da-trajetoria.md)
