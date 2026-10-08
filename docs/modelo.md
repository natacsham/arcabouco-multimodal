# Modelo e camadas de execução

## Seis classes centrais

| Classe | Significado | Distinção importante |
| --- | --- | --- |
| `Fonte` | Registro ou artefato efetivamente utilizado para fundamentar conhecimento. | Bibliografia apenas citada não comprova análise direta. |
| `ConhecimentoMultimodalArticulado` | Compreensão resultante de relações documentadas entre conteúdos. | Não é automaticamente um trecho, resumo, norma ou decisão. |
| `CriterioDeDecisaoMultimodal` | Direcionamento, condição, cuidado ou restrição empregado para orientar uma decisão multimodal. | Não determina uma resposta sem contexto; não representa todo critério de acessibilidade existente. |
| `ContextoDeInteracaoDigital` | Caracterização situada de tarefa, objetivo, participantes, condições, barreiras, necessidades e recursos pertinentes. | Não presume informação ausente nem um perfil completo por diagnóstico. |
| `DecisaoDeAcessibilidadeMultimodal` | Emprego situado de conhecimentos e critérios em configurações de interação. | É apresentada como orientação; não é efeito observado no mundo. |
| `Resultado` | Resultado documentado relacionado à aplicação ou avaliação. | Resultado esperado não deve ser apresentado como observado. |

## Elementos auxiliares

- **Estudo e Artefato:** distinguem a investigação de seus produtos. Uma publicação é um registro de uma investigação, não seu sinônimo.
- **TrechoDocumental e ReferenciaBibliografica:** permitem localizar a sustentação e distinguir conteúdo analisado de bibliografia citada.
- **Perspectiva:** registra de onde uma descrição ou interpretação é produzida; não é sinônimo de pessoa, papel ou diagnóstico.
- **ParticipacaoNoContexto:** representa papéis e características relevantes de participação. Não é uma classe clínica de pessoa.
- **ArticulacaoDocumentada:** explicita entradas, produto, tipo de relação, fontes, confirmação, condições e limites da articulação.
- **ConfiguracaoModalDaDecisao:** liga função, modo, recurso, responsável, condições, alternativa e fundamentação.
- **AplicacaoDeCriterio:** preserva, para uma configuração e um critério específicos, os conhecimentos de apoio, origens e justificativa correspondentes.
- **ContribuicaoNaArticulacao:** liga uma contribuição individual ao trecho localizado, à operação de articulação e ao conhecimento produzido ou refinado. Registra conteúdo próprio, justificativa, papel e grau de conferência; a fonte é recuperada pelo trecho.

Estratégia, Evidência e Recomendação não são retomadas como classes centrais autônomas. A palavra “orientação” nomeia a apresentação da decisão no AMADO, não uma segunda ontologia.

## Por que acrescentar AplicacaoDeCriterio?

Uma configuração pode mobilizar vários conhecimentos e critérios. Duas listas independentes não dizem qual conhecimento fundamenta qual critério naquele uso.

Por exemplo, se uma configuração possui K17, K38 e K43 e aplica CA02, isso não autoriza afirmar três pares de fundamentação. Quando o registro prevê CA02 apoiado em K38 e K43, a consulta deve preservar exatamente esse vínculo.

O elemento auxiliar torna essa associação examinável. Ele não transforma justificativa documental em prova automática da qualidade de uma decisão.

## Qual camada faz o quê?

Na 1.4.0-rc1, `execution_evidence` registra em memória as correspondências e verificações efetivamente executadas. `execution_trace.py` deriva uma única projeção para as duas leituras, o de/para e o grafo. A função requerida pelo contexto é independente da função oferecida pelo padrão: a segunda não cria retrospectivamente a primeira.

As verificações distinguem **satisfeita**, **não satisfeita**, **pendente** e **não executada**. Condições escritas em prosa não são promovidas a testes computacionais. A cobertura parcial e as alternativas apenas descritas permanecem explícitas.

| Camada | Responsabilidade | O que não faz sozinha |
| --- | --- | --- |
| Documentação e curadoria | Analisar fontes, construir articulações e registrar condições e confirmação. | Não é executada autonomamente pelo instrumento. |
| RDF/OWL | Representar recursos, relações e axiomas. | Não interpreta livremente narrativas nem redige uma orientação. |
| Reasoner OWL | Examinar consistência e inferências sob os axiomas declarados. | Não julga pertinência humana nem integridade completa do formulário. |
| SHACL | Verificar restrições de integridade estabelecidas para os dados. | Não comprova que a fonte foi corretamente interpretada. |
| SPARQL | Consultar contexto, conhecimentos, articulações e proveniência. | Recuperação não autoriza automaticamente aplicação. |
| Motor determinístico | Verificar elegibilidade e compor configurações a partir de padrões documentados. | Não descobre novos princípios nem possui cobertura irrestrita. |
| Interface AMADO | Coletar confirmação e apresentar orientação e fundamentação. | Clareza visual não equivale a validade científica. |

## Estados que precisam permanecer diferentes

**Recuperado** significa encontrado por uma relação pertinente. **Aplicável** exige condições satisfeitas e ausência de impedimento. **Condicional** exige confirmação adicional. **Excluído** indica incompatibilidade ou fundamentação inadequada para aquele uso.

Não informado e explicitamente indisponível também são estados diferentes. Um recurso desconhecido não deve ser tratado como confirmado, nem a ausência de um termo no texto deve virar uma proibição inventada.

O grafo resultante e a apresentação pública devem conservar a condição e o limite da aplicação, inclusive quando isso tornar a orientação menos abrangente.
