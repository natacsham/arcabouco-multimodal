# Fundamentação do piloto de composição multimodal

Este piloto experimental trata de **produzir e revisar uma contribuição digital**. A hipótese técnica é que capacidades de entrada e de apresentação possam ser compostas por funções e condições, sem cadastrar uma orientação completa para cada cenário. Não é resultado de avaliação humana nem demonstração de melhoria de aprendizagem.

## O conhecimento que orienta a composição

São três trabalhos diferentes:

1. **Síntese analítica da pesquisa:** relacionar contribuições documentais, explicitar a compreensão resultante e seus limites.
2. **Representação:** registrar funções, capacidades, condições e relações com fontes localizadas.
3. **Execução:** verificar o contexto informado, encontrar capacidades compatíveis e compor um percurso. A execução não lê artigos nem descobre a síntese analítica.

O percurso do piloto é `capturar um rascunho → apresentar o rascunho para revisão`. Voz e teclado podem oferecer entradas alternativas; texto e síntese de voz podem oferecer apresentações distintas. Uma entrada não obriga a saída pela mesma modalidade. Cada capacidade depende de disponibilidade, possibilidade de uso e adequação à função.

## Fontes primárias consultadas nesta evolução

Consulta pontual em 10/10/2026. As paráfrases abaixo não substituem os documentos. São complementos externos desta evolução; não constituem evidência de que a versão da tese já empregava essas formalizações.

| Fonte e localização | Contribuição mobilizada | Limite preservado |
|---|---|---|
| Coutaz, Nigay, Salber, Blandford, May e Young (1995), *The CARE Properties*, seção 3, pp. 2–4 do PDF; seção 4, pp. 5–6. [Original](https://danielsalber.com/publications/interact1995.pdf) | CARE distingue alternativas que alcançam o mesmo objetivo de modalidades cuja combinação é necessária para alcançá-lo. | Equivalência funcional do sistema não assegura acesso, esforço ou preferência equivalentes para a pessoa. |
| W3C, *Multimodal Interaction Requirements*, Note de 08/01/2003, “Multimodal interactions”, §§ 1.6 e 4.6. [Versão](https://www.w3.org/TR/2003/NOTE-mmi-reqs-20030108/) | Separar entrada e saída, considerar o contexto e preservar a acessibilidade ao combinar modalidades. | É uma Note de requisitos para especificações; não certifica aplicações nem demonstra benefícios deste piloto. |
| W3C, *WCAG 2.2*, § 2.1.1, nível A. [Critério](https://www.w3.org/TR/WCAG22/#keyboard) | A funcionalidade deve poder ser operada por interface de teclado, ressalvada a exceção do critério. | Não demonstra que determinada pessoa consegue operar um teclado físico. |
| W3C, *WCAG 2.2*, § 3.3.6, nível AAA. [Critério](https://www.w3.org/TR/WCAG22/#error-prevention-all) | Na submissão de informação, prevê reversibilidade **ou** verificação e correção **ou** revisão, confirmação e correção antes de concluir. | O piloto escolhe a terceira possibilidade como decisão de projeto; não a atribui como obrigação AA universal. |

O § 3.3.3 trata de sugestões conhecidas para erros automaticamente detectados. O § 3.3.4 tem um escopo específico de submissões. Nenhum deles fundamenta, sozinho, revisão semântica automática de qualquer mensagem. [WCAG 2.2, assistência de entrada](https://www.w3.org/TR/WCAG22/#input-assistance)

## O que os registros anteriores acrescentam

Os registros abaixo foram conferidos na base pública [knowledge-base.json](../../../data/knowledge-base.json). Seus documentos originais **não foram relidos integralmente nesta implementação**. Preservam-se as localizações e os estados legados, inclusive quando um registro de trecho informa conferência anterior. Isso não promove toda a interpretação para “confirmada”. Os identificadores K desta tabela são os da MADO, não os da skill de multimodalidade.

| Registro MADO | Contribuição ao piloto | Origem registrada e limite |
|---|---|---|
| K10 | Uma saída tecnicamente compatível com leitor de tela ainda precisa representar a informação necessária à compreensão. | F03, WABlind; TD-EV12, TD-EV13, TD-EV14 e TD-EV16, pp. 1, 3 e 8. Estado `CANDIDATO_RECONSTRUIDO_A_REVISAR`. Não comprova a compreensão de uma nova mensagem por TTS. |
| K41 | A viabilidade de uma entrada depende de movimento/ação exigidos, compatibilidade, desempenho e confirmação perceptível. | F01 e F05; TD-RC3-REF-04, p. 8, e TD-RC3-REF-07, p. 5. Fundamentação `PARCIAL`. A viabilidade individual continua dependente da tarefa real. |
| K42 | A alternativa entre modos precisa preservar a informação relevante, não apenas oferecer outro formato. | F03, F06, F08 e referências normativas; trechos e origens registrados na base. Fundamentação `PARCIAL`. Uma apresentação por áudio não é automaticamente equivalente à visual. |
| K44 | Um retorno que orienta continuidade precisa ser perceptível e recuperável quando necessário. | F01 e referências normativas; TD-EV02, TD-RC3-REF-05 e TD-ORI-0414–0416. Fundamentação `PARCIAL`. Transferência da mobilidade para revisão de mensagem é interpretação situada, não resultado observado nesse novo domínio. |

## Qual articulação está sendo proposta

**Operação analítica:** relacionar a distinção entre objetivo funcional e modalidade, as condições de acesso aos mecanismos e a possibilidade de conferir a informação produzida.

**Compreensão resultante proposta:** uma contribuição digital não deve depender de uma associação fixa entre entrada e saída. É possível procurar uma entrada viável que produza um rascunho e, separadamente, uma apresentação viável que permita revisá-lo, mantendo o vínculo com o mesmo conteúdo. Disponibilidade técnica, acesso individual e preservação de significado precisam ser conferidos separadamente.

Isso não é uma conclusão literal de qualquer fonte isolada. É uma proposta de articulação da pesquisa, tornada explícita para inspeção e teste. O apoio das fontes primárias não remove as pendências dos conhecimentos legados.

## Relação multimodal: o que pode ser afirmado

- **Voz ou teclado para capturar o mesmo rascunho:** alternativas funcionais pretendidas, condicionadas a conseguirem realizar essa captura. Compatibilidade na especificação não confirma desempenho individual.
- **Captura seguida de revisão:** encadeamento de funções sobre o mesmo rascunho. A sequência, sozinha, não será rotulada como complementaridade CARE.
- **Texto ou TTS para revisão:** propostas de apresentação, dependentes do que precisa ser percebido. TTS não assegura acesso a pontuação, organização espacial ou outros elementos que a tarefa possa exigir.
- **Texto e áudio disponíveis:** não são automaticamente redundância, fusão ou complementaridade. A classificação exigiria explicitar o objetivo, a informação oferecida, a necessidade de cada modo e a organização temporal.

A recomendação é de projeto de uma interação. O piloto não executa reconhecimento de fala, reprodução TTS, edição ou envio da mensagem; não testa a pessoa nem os recursos reais.

## Como conferir a contribuição desta evolução

O teste relevante mantém o motor fixo e modifica somente conhecimento operacional conferido: uma nova capacidade compatível pode abrir outro percurso; retirar seu fundamento deve retirar ou rebaixar o percurso; uma referência apenas bibliográfica não deve habilitá-lo. Uma nova restrição pode reduzir soluções. Esses resultados verificam o uso computacional das relações representadas, não comprovam utilidade ou superioridade de uma modalidade.

Não se deve confundir número de combinações com qualidade. Uma saída defensável identifica o objetivo funcional, a contribuição de cada capacidade, a ligação documental, o que foi verificado, o que permanece proposto e por que uma alternativa foi descartada.
