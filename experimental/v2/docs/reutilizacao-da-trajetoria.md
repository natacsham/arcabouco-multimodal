# Da trajetória da pesquisa à composição de uma orientação

Esta evolução usa registros de `data/knowledge-base.json`, sem alterar a base pública. O artigo sobre critérios de acessibilidade em artefatos educacionais não é reduzido à plataforma EAD em que ocorreu a aplicação: seu conteúdo reaproveitável está na organização da interação, nas condições funcionais, nos critérios e nas alternativas de acesso.

## O que faltava operacionalizar

O padrão público `PAD-COMUNICACAO-MULTIFORMATO` reúne voz, teclado e leitura em voz como requisitos simultâneos. Sua instrução também exige voz. Por isso, não bastava mudar o teste de disponibilidade de “todos” para “qualquer um”: a orientação continuaria indicando um recurso impedido.

A evolução separa **produzir um rascunho** de **revisar esse mesmo conteúdo**. Cada etapa examina as formas de interação registradas para cumpri-la. As combinações são propostas de projeto; não são operações de acessibilidade implementadas no aplicativo de mensagens da pessoa.

## O que a base da tese acrescenta

| Registro preservado | Contribuição examinada | Consequência na proposta experimental |
|---|---|---|
| K28 — coordenação da comunicação | Rótulos, entrada, foco, identificação de erros, confirmação e retorno formam uma sequência, não itens independentes. Registros TD-EV29 e TD-EV30, F08. | Produção e revisão precisam compartilhar um conteúdo editável e uma forma de correção. A presente execução não cobre envio nem retorno de envio. |
| K29 — alternativas de entrada e percepção | Formas diferentes podem participar da comunicação desde que cada alternativa mantenha acessibilidade própria. Mesmos registros documentais de F08. | Impedir fala como entrada não impede automaticamente áudio como saída; cada caminho tem suas próprias condições. |
| K41 — viabilidade situada da entrada | Movimento, compatibilidade, esforço/desempenho e confirmação perceptível condicionam a operação. Registros do estudo de entrada alternativa e do estudo de orientação em mobilidade. | A presença de teclado ou reconhecimento de fala não basta: a viabilidade do canal para a tarefa precisa ser confirmada. |
| CA38 — operação por teclado | O catálogo preserva a exigência de operação por interface de teclado. | Fundamenta a operação por teclado, não prova que qualquer pessoa consiga usá-lo ou que o esforço seja aceitável. |

K28 e K29 continuam candidatos reconstruídos a revisar. K41 mantém sua conferência documental parcial. A ponte não promove esses estados para “original conferido”. Os trechos primários de interação multimodal e revisão já consultados no piloto são apoios separados. As novas aplicações são **sínteses operacionais assistidas propostas para este experimento**, não resultados antigos atribuídos retrospectivamente aos artigos.

K38 e K43 não são utilizados como atalho para ampliar qualquer tarefa: suas condições de aplicação à produção e organização de recursos precisam ser respeitadas. Também não foram empregados critérios de legenda de vídeo para fundamentar áudio isolado.

## Onde está a base consultada

- **Registros da pesquisa:** `data/knowledge-base.json` — fontes, trechos, conhecimentos, critérios e origens.
- **Correspondências propostas:** `experimental/v2/trajectory-bindings.json` — qual parcela desses registros fundamenta cada capacidade e quais condições ela exige. Não contém casos completos nem respostas por identificação de cenário.
- **Projeção executável:** `experimental/v2/trajectory.py` — lê os registros, verifica os vínculos e constrói o grafo em memória. Não há uma segunda cópia editada manualmente dos enunciados.
- **Composição:** `experimental/v2/composer.py` — confronta esse grafo com condições confirmadas e monta percursos permitidos.

Os hashes identificam os arquivos efetivamente lidos. O resultado permite seguir capacidade → aplicação exata → síntese operacional → registro da pesquisa → trecho → fonte, distinguindo a interpretação proposta da informação preservada.

## Como aproveitar o que existe sem inventar uma solução

O resultado mantém dois níveis: a compatibilidade com o contrato anterior (`status`) e a apresentação mais precisa (`proposal_status`).

- **Completa:** existe uma composição para todas as funções da tarefa representada, sob as condições informadas. Isso não significa que a atividade foi realizada.
- **Condicional:** existe um percurso candidato, mas faltam confirmações. A saída identifica as perguntas que o impedem de se tornar uma proposta completa.
- **Parcial:** há etapas sustentadas, mas não um percurso completo. A saída informa o que é aproveitável e o que não está coberto, sem ligar etapas incompatíveis.
- **Sem proposta:** nenhuma etapa ou percurso sustentado pode ser indicado com os registros e impedimentos presentes.

“Tentar as possibilidades da base” significa examinar caminhos fundamentados, não ignorar incompatibilidades, deduzir capacidade por diagnóstico ou escolher a alternativa mais favorável à tese. A ordem da lista não é um ranking de qualidade.

## Limites deste avanço

O recorte executável permanece produção/revisão de contribuição digital, agora conectado a uma parte identificada da trajetória. Ainda não é a migração das 45 unidades da base nem a leitura automática de diretrizes. Um acionador disponível, por exemplo, não é tratado como entrada pronta sem representar e conferir sua operação.

A interface pública continua preservada. A avaliação desta evolução é técnica, com casos sintéticos estruturados; não constitui nova avaliação com participante nem comprovação de benefício educacional.

As execuções e os resultados estão em `../evidence/trajectory-report.json`. O relatório distingue impedimento, desconhecimento, cobertura parcial e mudança efetiva de composição.

Para experimentar, `examples/learning-contribution.json` representa uma situação **sintética**: produzir uma contribuição curta em atividade de aprendizagem, com escrita viável e revisão por áudio, sem entrada por voz nem revisão visual utilizáveis. Os valores são premissas do teste, não características deduzidas de um diagnóstico. Alterar `KeyboardEffortAcceptable` para `null` testa a necessidade de confirmação; mudar a saída de áudio para impedida obriga reexaminar as alternativas.
