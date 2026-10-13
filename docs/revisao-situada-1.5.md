# Revisão situada — MADO 1.5.0-rc1 / compositor 2.0.0-alpha3

Revisão candidata com verificação técnica concluída em 13/10/2026. Base anterior preservada: `ebfcb75ab3a584128cc804270e73851db1d5e837`. Alterações restritas a `arcabouco-multimodal`; o repositório externo MADO e os arquivos da tese não foram editados.

## O que está sendo corrigido

| Ruptura | Correção verificável |
| --- | --- |
| Característica ou tarefa transferida entre pessoas | Afirmações com sujeito, situação, trecho e revisão; contextos separados |
| Diagnóstico usado como habilidade | Condição relatada separada da dificuldade observada e dos requisitos documentados |
| Pergunta dependente de padrão já encontrado | Esclarecimento funcional anterior à seleção, até três por rodada |
| Referência confundida com autorização | Afirmações operacionais delimitadas, apoio pareado fonte–trecho e escopo |
| Padrão completo como única unidade | Operações derivadas dos contratos dos padrões existentes |
| Várias mídias chamadas de combinação | Relações executáveis com finalidade, informação e condições próprias |
| Ausência de resposta culpando a pessoa | Lacunas distintas: interpretação, contexto, fundamento, operação, incompatibilidade ou limite de busca |

## Fonte, articulação e aplicação são coisas diferentes

A base pública não contém uma cópia de todas as normas ou publicações. Conserva identificadores, referências, localizações, paráfrases permitidas e o estado de conferência. O AMADO consulta esses registros já preparados, sem buscar documentos durante o atendimento.

Uma contribuição delimitada pode ser conferida no registro preservado, sem leitura atual do documento original. A operação analítica que relaciona contribuições não foi descoberta pelo programa. A aplicação executada verifica se uma parcela dessa compreensão pode apoiar uma função no contexto confirmado. As três etapas não são intercambiáveis.

Uma afirmação pendente não se torna válida porque existem fonte, trecho e critério. Uma fonte adicional isolada não habilita uma orientação. Uma nova proposta de operacionalização não é avaliação humana nem evidência de benefício educacional.

## Cobertura não é autorização

Os **onze contratos dos padrões existentes** delimitam ações e apoios; não significam onze composições completas nem onze recomendações sempre disponíveis. O mesmo executor reutiliza capacidades e a relação de produção/revisão já registradas no RDF experimental, sem outra matriz de respostas.

- `PAD-PAPEIS-TURNOS-AUTORIA` permanece **somente na auditoria**: a caracterização dos participantes não possui aplicação de critério admissível que autorize essa operação.
- A alegação de consolidação da aprendizagem por jogo (`K37`) continua pendente. A parcela operacional de uma atividade interativa já escolhida limita-se a feedback acessível e conferência; não recomenda jogo para uma condição cognitiva nem afirma benefício educacional.
- As relações dos PAD são internas às respectivas operações. A ligação documentada entre produzir e revisar um rascunho não autoriza encadear arbitrariamente quaisquer PAD.

## Exemplo integral efetivamente executado

O [relatório situado](../experimental/v2/evidence/situated-report.json), consultado nesta revisão em 13/10/2026, conserva entrada, ações, fontes, verificações e variantes. O caso `SYN-NOVEL-COLLAB-908` é **inteiramente sintético**: não reconstrói uma sessão, pessoa real ou declaração da especialista.

### Contexto e condições

A situação `draft-notes` é preparar e conferir notas para um encontro comunitário. A e B recebem separadamente a tarefa registrada `TaskCreateReviewedText`: produzir e revisar uma contribuição digital. O assunto do encontro não seleciona uma resposta.

| Entrada sintética confirmada | Pessoa A — `p-voice` | Pessoa B — `p-keyboard` |
| --- | --- | --- |
| Produção | Fala operável e reconhecimento utilizável; teclado não operável | Teclado operável; entrada por fala não utilizável |
| Conferência | Texto visual perceptível; revisão por fala indisponível | Revisão por fala utilizável; texto visual não perceptível |
| Recursos declarados | Microfone, reconhecimento de fala, texto editável e apresentação visual | Teclado, texto editável, síntese de fala e saída de áudio |
| Controles | Correção e conclusão sob controle da pessoa | Correção, pausa, repetição e conclusão sob controle da pessoa |

O ensaio também declara conteúdo disponível, comunicação em contexto de aprendizagem, compatibilidade e esforço aceitáveis da entrada utilizada e possibilidade de conferir o significado. São valores fornecidos ao teste, não habilidades deduzidas de diagnósticos. Todos os valores, inclusive negativos das rotas não escolhidas, estão em `fixtures.complete`.

### Fonte → contribuição → articulação

| Fonte e localização registradas | Contribuição delimitada | Articulação e conhecimento resultante |
| --- | --- | --- |
| [CARE, Coutaz et al. (1995)](https://danielsalber.com/publications/interact1995.pdf), pp. 2–5, seções 3–4; [WCAG 2.1.1 — Keyboard](https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html), critério e intenção | `CInputCARE`: alternativas funcionais precisam de verificação individual. `CInputKeyboard`: a interface de teclado precisa ser operável; esse requisito não fundamenta entrada por voz. | `ArtInput` relaciona alternativa funcional e operação situada, produzindo `KInput`: gerar um rascunho por uma entrada utilizável. A aplicação usa o critério analítico `CriterionInput`. |
| [W3C MMI Requirements (2003)](https://www.w3.org/TR/2003/NOTE-mmi-reqs-20030108/), interações multimodais, §1.6 e §4.6; [WCAG 3.3.6 — Error Prevention (All)](https://www.w3.org/WAI/WCAG22/Understanding/error-prevention-all.html), critério e intenção | `CReviewMMI`: entrada, saída e coordenação são distinguíveis. `CReviewWCAG`: revisão/correção antes de concluir é uma alternativa de prevenção de erros. | `ArtReview` relaciona essas parcelas, produzindo `KReview`: ligar a produção do rascunho à conferência perceptível e corrigível. A aplicação usa `CriterionReview`. |
| As mesmas fontes MMI e WCAG de revisão | `CAudioMMI` e `CAudioReview`: escolher a entrada não determina a saída, e a revisão não precisa ser visual. | `ArtAudioReview` produz `KAudioReview`: revisar o mesmo rascunho por fala sintetizada, sob condições próprias de escuta, controle e correção. |

A WCAG 3.3.6 é AAA e oferece alternativas. O piloto escolhe revisão/correção como decisão de projeto delimitada, não como obrigação universal de modalidade ou prova de conformidade. Apoios legados conservam `LEGACY_RECORD_ONLY`; não são promovidos a leitura do original. As articulações são anteriores à execução: o programa não sintetiza novamente as publicações durante a consulta.

### Função → operações → relação → ação

**Antes da seleção**, a tarefa confirmada exige `Expression` — produzir um rascunho — e `Review` — conferir e poder corrigi-lo — para cada pessoa. Essa derivação vem de `TaskCreateReviewedText → requiresFunction`, não da escolha prévia de uma modalidade. As fontes fundamentam a estratégia; a tarefa informa as funções necessárias.

O executor confere as aplicações exatas `GroundSpeech`, `GroundKeyboard`, `GroundTextReview` e `GroundAudioReview`, suas articulações e condições. A relação `ProductionThenReview` liga a saída `TextDraft` da produção à entrada `TextDraft` da revisão, com correção e controle de conclusão disponíveis.

| Pessoa | Sequência admissível | Ação retornada |
| --- | --- | --- |
| A | `CaptureSpeech → ReviewText` | Registrar por fala, mantendo o texto reconhecido editável; apresentar esse rascunho em texto legível para conferir e corrigir antes de concluir. |
| B | `CaptureKeyboard → ReviewSpeech` | Registrar por teclado operável; ler o mesmo rascunho em voz, com pausa e repetição sob controle da pessoa, permitindo correção antes de concluir. |

O significado a preservar é o do **mesmo rascunho**, não qualquer conteúdo com igual tipo técnico. `CanVerifyMeaning` é uma condição declarada, não uma medição automática de compreensão. A relação é `SEQUENTIAL_REVIEW`: **não é automaticamente complementaridade CARE**.

O resultado contém duas sequências individuais admissíveis, não uma sequência colaborativa entre A e B ou alternativas intercambiáveis para qualquer pessoa. Permanece `PROPOSED_NOT_EVALUATED`: as ações não foram executadas com participantes.

O relatório também executa as tarefas principais `TAR-PRODUZIR-CONTEUDO-MULTIMODAL` e `TAR-REVISAR-E-CONFIRMAR`, atribuídas à mesma pessoa/situação, com confirmação de que tratam do mesmo rascunho textual editável. Esse refinamento técnico condicionado reutiliza a tarefa RDF. Não declara equivalência ontológica dos conceitos amplos; “comunicar” ou o nome de uma disciplina não ativa essa ligação.

### O que mudou ao retirar algo

| Alteração controlada | Resultado registrado | O que permite concluir |
| --- | --- | --- |
| Nenhuma | Duas sequências individuais completas no escopo declarado | As condições do ensaio permitem as operações e sua ligação. |
| Áudio utilizável de B passa a desconhecido | B fica condicional; a sequência individual de A é preservada | Desconhecimento não é disponibilidade nem impedimento confirmado. |
| `AudioUsable=false` somente para B | Não há composição completa para o conjunto; A mantém sua sequência e B conserva somente o registro por teclado | Foi negada a condição situada de uso do áudio, não retirado equipamento do arquivo. A capacidade de A não foi transferida a B. |
| Retirada em memória de `ProductionThenReview` como regra | Nenhuma sequência completa; operações isoladas permanecem como segmentos | Operações disponíveis não autorizam sua ligação. |
| Retirada em memória da operação analítica de `ArtReview`, mantendo fontes e contribuições | Nenhuma sequência completa; subsistem segmentos com seus próprios apoios | A articulação exige sua operação registrada; uma lista de fontes não a substitui. |

As duas últimas intervenções são **ablações técnicas**, não estudos de efeito humano. O relatório registra hashes antes/depois, igualdade dos arquivos protegidos e preservação do contexto original. As ablações alteram somente cópias em memória. A busca deste exemplo terminou sem atingir o limite; quando interrompida, o motor informa a limitação, sem concluir que uma solução não existiria.

## Limites que permanecem

Esta execução não demonstra compreensão equivalente entre formatos, fidelidade real do reconhecimento de fala, acessibilidade integral, coordenação entre participantes ou aprendizagem. Também não demonstra compreensão geral de narrativas: sujeito ambíguo, linguagem não reconhecida e tarefa insuficientemente delimitada precisam permanecer visíveis.

Uma correção de diagnóstico não autoriza inferir nova dificuldade. “Alguns estudantes” não significa todo o grupo nem informa sua quantidade. Pessoas e episódios não compartilham automaticamente requisitos, recursos ou respostas. O episódio prioritário limita a geração, sem apagar os demais registros.

## A explicação também chega ao RDF

`build_context_graph(situated_result=resultado)` exporta as funções que a execução situada realmente derivou. A CQ-010 recupera participante, episódio, tarefa, função e condição, sem cruzar dados de outras pessoas. Um vínculo de escopo com a tarefa não é apresentado como prova de que ela originou a necessidade: os dois casos possuem estados distintos.

O exportador exige o mesmo contexto confirmado e a mesma revisão utilizados na composição. Resultados de outro caso, anteriores à correção, sem confirmação ou com requisito reatribuído a outra pessoa são rejeitados. O caminho legado continua disponível apenas para compatibilidade. Essa exportação em memória não acrescenta automaticamente casos à base pública.

## Reprodução técnica

Na raiz deste repositório:

```powershell
python -B experimental/v2/verify_situated.py --output experimental/v2/evidence/situated-report.json
python -B -m unittest discover -s tests -p "test_situated_composition.py"
python -B -m unittest discover -s tests -p "test_*.py"
python -B -m unittest discover -s experimental/v2/tests -p "test_*.py"
node tests/intake.mjs
node tests/review-input.mjs
node tests/situated-output.mjs
python -B scripts/build_traceability_rdf.py --check
python -B scripts/check_bundle.py
```

HermiT/OWL 2 DL usa o verificador existente, com Java e ROBOT instalados. Uma alteração do RDF exige nova execução e hash correspondente; um resultado antigo não aprova a base nova. SHACL, consultas, execução local, navegador e leitura assistiva são verificações distintas.

O exemplo vem de `collaborative_unknown_context` no teste. O JSON conserva a entrada integral, todas as verificações, ações, fundamentos, lacunas e variantes; os quadros acima explicam esses registros.

## Verificações da entrega

| Verificação | Resultado e escopo |
| --- | --- |
| Suíte principal | 273 testes passaram; inclui os 25 testes situados, interpretação, autorização, composição, correções e exportação. As contagens não devem ser somadas entre si. |
| Compositor anterior | 75 testes de regressão passaram; não substituem a verificação situada. |
| Navegador | 49 verificações passaram, incluindo duas comparações Python–worker, interpretação, correção, apresentação, teclado, foco, contraste e refluxo. |
| Endereço público | 33 verificações passaram após publicação; 38 arquivos da aplicação e quatro downloads coincidiram com os hashes conferidos localmente. Sem erros de JavaScript ou envio dos casos a serviços externos no percurso testado. |
| RDF e consultas | 16.925 triplas; consultas CQ-001 a CQ-010 executadas. A CQ-010 também foi testada com exportação situada positiva e vínculos exatos entre participante, situação, tarefa, função e condição. |
| SHACL | Sem violações; 65 avisos documentais históricos preservados, sem promovê-los a fundamentação conferida. |
| OWL 2 DL e HermiT | Aprovados para os grafos registrados nos relatórios e seus respectivos hashes. |
| Transferência e ablações | Duas sequências individuais no caso sintético; alterações de condição ou fundamentação afetam somente os percursos dependentes. Arquivos da base e do motor permaneceram iguais durante o ensaio. |

Relatórios: [verificação técnica](../evidence/technical-1.5-report.json), [navegador](../evidence/situated-browser.json), [composição situada](../experimental/v2/evidence/situated-report.json), [HermiT](../evidence/reasoner-1.5-report.json) e [manifesto de publicação](../web/amado/manifest.json). O manifesto vincula os arquivos públicos aos bytes efetivamente conferidos.

## Estado de entrega

Implementação concluída na branch `feat/amado-situated-composition` e publicada no site existente pelo commit `c0ec3c400e0c32408e005daf03e2345029312401`, com [verificação e implantação aprovadas](https://github.com/natacsham/arcabouco-multimodal/actions/runs/38351144785). O [teste público sintético](../evidence/situated-public-smoke.json) confirmou os mesmos arquivos e downloads. Ele mantém a data e o commit efetivamente observados; atualizações posteriores deste relatório não representam outra sessão.

O exemplo preparado conserva quatro operações condicionais, não uma solução completa. O relato sintético do teste público permaneceu sem composição e recebeu três esclarecimentos. O ensaio de recombinação completa é o caso sintético detalhado acima, com suas condições explicitamente confirmadas. Não se equiparam esses resultados nem se afirma resolução geral de narrativas.

Resultados técnicos não representam reconferência autoral de todas as interpretações, teste com participantes nem prova de aprendizagem. Houve inspeção visual e verificações automatizadas de teclado, foco, contraste e ampliação. Não houve teste com leitor de tela real, avaliação da precisão do ditado nem declaração de conformidade integral com WCAG.
