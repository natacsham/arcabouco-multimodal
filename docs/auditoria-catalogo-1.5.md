# Auditoria do catálogo situado — 1.5.0-rc1

Data: 2026-10-13. Escopo: base pública preservada, vocabulário, projeção RDF e contratos operacionais. Esta migração não realizou nova leitura dos documentos originais, avaliação com pessoas nem demonstração de benefício educacional.

## Inventário e decisão documental

Foram examinados os 45 conhecimentos, as 11 linhas da matriz funcional existente e os 11 padrões ativos, sem criar outra matriz. Os 32 componentes históricos, os enunciados e os estados de curadoria anteriores foram preservados. A camada nova contém 85 afirmações: 42 `DOCUMENTED_OPERATIONAL_CLAIM`, distribuídas por 22 conhecimentos; 36 `PROPOSED_OPERATIONALIZATION`, exclusivas da auditoria; e 7 `NOT_ELIGIBLE`.

Os 22 conhecimentos com alguma parcela documentada são K02, K07, K10, K11, K14, K17, K19, K26, K28, K29, K30, K34, K35, K36, K38, K39, K40, K41, K42, K43, K44 e K45. Isso não aprova integralmente esses conhecimentos. Por exemplo, a conclusão histórica de K38 continua proposta; uma contribuição delimitada de TD-EV29/F08 pode sustentar somente o escopo que descreve. A disponibilidade de identificadores de fonte, trecho e critério, isoladamente, não torna uma afirmação elegível.

Cada parcela operacional declara enunciado, funções, fontes, trechos, contribuição ou base de revisão, escopo, limites e proveniência. A conferência herdada de um registro não foi reclassificada como leitura atual do original. O validador verifica a identidade efetiva do par: trecho existente, sua fonte real, pertencimento ao conhecimento e igualdade entre os índices e o apoio pareado. Reutilizar uma contribuição conferida exige o mesmo enunciado e trecho, sem atribuí-la a outro conhecimento.

Existem 19 fontes e 26 contribuições registradas. Os endereços públicos existentes e suas localizações foram preservados; fontes sem endereço permanecem sem endereço, não com um link inventado. F07, F11 e F12 receberam reconciliação documental pendente explícita. Essa pendência impede ampliar seu suporte, mas não apaga outros apoios delimitados já conferidos no registro. A conferência documental original anterior de trechos WCAG permanece identificada como anterior, não como trabalho desta migração.

## Matriz existente: descrição não equivale a regra

As listas documentais históricas continuam disponíveis. `inference_contract` delimita separadamente o apoio consumível; sinais funcionais não são diagnósticos. Uma exigência de projeto não comprova que uma pessoa consiga operar determinado modo ou recurso.

| Linha | Escopo operacional delimitado | Base principal |
| --- | --- | --- |
| MF-01 | Acesso e significado de conteúdo não textual | K42/TD-ORI-0001; parcela K10 |
| MF-02 | Examinar a entrada perante o movimento e o dispositivo informados | K41/C-K41-02 |
| MF-03 | Expressão por alternativas, sem presumir capacidade oral | parcela K29/TD-EV30 |
| MF-04 | Organização ou recuperação, em dois grupos de sinais independentes | K43/C-K43-02; K40/C-K40-01 |
| MF-05 | Desconforto e possível necessidade de ajuste; ainda não autoriza função | K20 histórico, proposto |
| MF-06 | Caracterizar condições pertinentes à tarefa | K35/C-K35-01; K34 |
| MF-07 | Verificar operação do recurso; desconhecimento não é incapacidade | K39/C-K39-02; K41/C-K41-02 |
| MF-08 | Caracterizar diversidade relatada, sem propagar para cada membro | K34; K45/C-K45-01 |
| MF-09 | Caracterizar mediação contextual | parcela K11; K35/C-K35-01 |
| MF-10 | Verificar disponibilidade e condições ambientais concretas | K40/C-K40-02; K41/C-K41-01 |
| MF-11 | Acesso à informação audiovisual pertinente | K42/TD-ORI-0148 |

MF-05 foi auditada, não artificialmente habilitada. Cobertura dos 11 registros não significa cobertura de todas as dificuldades ou de todas as tarefas. MF-04 não transfere automaticamente a exigência de recuperar informação para todo relato de atenção, nem o inverso.

## Migração dos 11 padrões ativos

Cada padrão conserva seu identificador e ação histórica, mas ganha ação operacional delimitada, entradas, saídas, representações, recursos, responsabilidades a confirmar, condições, limites e afirmações exatas. A reutilização em tarefa nova requer testemunho funcional e condições situadas; não depende apenas de pertencer à tarefa histórica.

| Padrão | Parcela operacional preservada |
| --- | --- |
| ORGANIZAR-CONTEUDO-PERSISTENTE | Organização entre formatos; sem efeito causal de redução de sobrecarga |
| EXPRESSAO-AUTORAL-FALA-AUDIO | Expressão alternativa e representação acessível do áudio |
| REPRESENTACAO-VISUAL-EXPLICADA | Relação entre informação visual e descrição correspondente |
| VIDEO-PROCESSO | Acesso ao vídeo já pertinente; sem duração ou método pedagógico impostos |
| JOGO-CONSOLIDACAO-FEEDBACK | Feedback e revisão de atividade já escolhida; sem escolher jogo ou afirmar eficácia |
| PAPEIS-TURNOS-AUTORIA | Caracterizar responsabilidades; sem fixar papel da professora ou turnos gerais |
| REVISAO-CONFIRMACAO | Feedback e possibilidade de revisão |
| ORIENTACAO-AUDIO-RECUPERAVEL | Recuperar orientação; sem impor telefone específico |
| RETORNO-HAPTICO-RUIDO | Examinar retorno alternativo nas condições registradas |
| CONTEUDO-WEB-EQUIVALENTE | Significado e acesso a conteúdo web |
| COMUNICACAO-MULTIFORMATO | Seleção situada da entrada e revisão; sem exigir todos os dispositivos |

Há seis relações explicitadas, todas internas à respectiva operação (`WITHIN_OPERATION`). Elas declaram unidade de significado, representações, preservação, condições de suficiência, temporalidade e apoio. Não foi inventada relação entre operações independentes para produzir uma configuração aparentemente completa. A insuficiência desse encadeamento deve aparecer como lacuna de integração.

K37 não possui afirmação autorizadora: a consolidação da aprendizagem por jogo continua pendente. O identificador histórico do padrão não muda esse limite. K27 também não ganhou autorização por aproximação: organização só pode recorrer a parcelas específicas de outros registros quando o contexto as sustenta.

## Tipagem, modelo e verificações

As 30 características existentes distinguem condição relatada, observação funcional, necessidade, composição de grupo, experiência e outros tipos sem alterar seus identificadores históricos. Formas de representação, canal, método de entrada e atividade composta ficam separados: teclado e toque são métodos; jogo não é tratado como modalidade elementar. `MOD-TOQUE`, antes referenciado sem declaração, foi declarado. O contrato semântico do catálogo não se confunde com o campo `kind` do intake situado versão 1.0.

Foram introduzidas somente duas classes auxiliares: `AfirmacaoOperacionalDocumentada`, para preservar a unidade de autorização, e `FuncaoRequeridaSituada`, para ligar função, tarefa, contexto e eventual participação. As CQ9 e CQ10 acrescentam consultas sobre essas unidades; não substituem as oito questões históricas. SHACL verifica os pares documentais e o pertencimento da participação ao contexto ou episódio pai. Propostas e pendências continuam estados documentais válidos, sem se tornarem fundamento operacional.

Verificação executada nesta etapa: os 11 testes de `tests/test_situated_catalogue.py` passaram, incluindo troca indevida de fonte/trecho, origem de critério cruzada, tentativa de autorizar afirmação pendente, preservação de K37, separação de MF-04 e consulta dos pares exatos. A projeção pública passou SHACL com zero violações e 65 avisos históricos de qualidade, preservados e não convertidos em aprovação semântica. O teste negativo de fonte incorreta falha mesmo quando esses avisos são permitidos.

A exportação inicial desta migração contém 16.925 triplas e 26 contribuições; sua reprodução com `--check` passou. As regressões de contribuições (26 testes) e ontologia (39 testes) também passaram. Esses resultados são verificações técnicas de consistência e rastreabilidade, não validação humana da orientação. O relatório integral da execução do sistema é mantido separadamente; nenhum total de teste não executado é atribuído a esta auditoria.

## Correção após revisão semântica dos contratos

A última revisão encontrou dois defeitos que os pares de identificadores, isoladamente, não detectavam: a operação háptica podia passar com a saída de áudio impedida; e afirmações normativas específicas eram ligadas a critérios de outro conteúdo por pertencerem ao mesmo conhecimento K42. As associações dos 11 contratos e de suas seis relações foram então conferidas individualmente.

As 37 associações anteriores permanecem em `claim_support_audit`, sem autorização operacional. Os 22 apoios atuais distinguem seis cláusulas normativas com o mesmo trecho da origem, sete aplicações analíticas delimitadas conferidas no registro e nove contribuições contextuais sem atribuição de critério. Legendas sustentam o critério de legendas; audiodescrição sustenta o de audiodescrição. Recuperação de orientação não foi equiparada a áudio ao vivo. Na comunicação multiformato, o fundamento de feedback pertence à parcela específica de K28, não ao registro de compatibilidade de entrada de K41. Cada aplicação analítica informa `CONFERIDO_NO_REGISTRO`, a origem única pertinente e a ausência de nova conferência do original.

A operação PAPEIS-TURNOS-AUTORIA conserva seu apoio contextual, mas fica somente na auditoria: identificar participantes não sustenta, por si, CA74, relativo à clareza textual. Nenhuma afirmação foi ampliada ou promovida para manter uma operação habilitada. Os 42 registros elegíveis permanecem iguais; há 34 combinações distintas de enunciado e conjunto de trechos, portanto 42 não significa 42 evidências independentes.

O retorno háptico passou a exigir também `REC-SAIDA-AUDIO` e uma confirmação situada própria: a mesma orientação deve permanecer disponível e a pessoa deve conseguir acionar sua repetição. Ter saída de áudio não comprova retenção nem controle. As regressões confirmam: áudio impedido exclui a operação; recuperação desconhecida deixa-a condicional; recuperação negada a exclui; recuperação confirmada permite continuar as verificações.

O conjunto específico passou de 11 para 16 testes, cobrindo também os vínculos normativos indevidos na operação e na relação. RDF/OWL foram regenerados e `--check` passou; o hash Turtle permaneceu `a1598943c6698c67f679e5299c73e0c1465da47d3044e227393b5659c5a87f85`, pois esses ajustes pertencem aos contratos JSON, sem alterar as afirmações projetadas. A qualificação dos 11 padrões não significa que todos produzam uma rota modal completamente selecionada: os contratos distinguem opções de representação de seleção efetiva, e lacunas de integração permanecem explícitas.
