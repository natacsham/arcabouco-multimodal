# Revisões do AMADO

A revisão atual é [MADO 1.5.0-rc1 — representação e composição situadas](revisao-situada-1.5.md). A auditoria do catálogo está em [auditoria-catalogo-1.5.md](auditoria-catalogo-1.5.md); a revisão independente do motor, em [revisao-compositor-1.5.md](revisao-compositor-1.5.md). O conteúdo abaixo conserva o histórico, não descreve o contrato atual.

## Histórico: 1.4.0-rc3 — usar a matriz existente e explicar ações

## Revisão do instrumento — intake1

`AMADO-web-1.4.0-rc3-intake1` corrige o entendimento do desafio antes de ampliar a apresentação dos resultados. Preserva a base, os padrões e a ontologia 1.4.0-rc3; modifica interpretação, seleção de esclarecimentos, edição e mensagens de execução. O manifesto identifica separadamente a revisão do instrumento.

- Síntese do entendimento antes das perguntas, sem converter automaticamente ensinar o uso de uma ferramenta em leitura de conteúdo.
- Reconhecimento de mediadores e participações plurais; relação de quem solicita separada de papéis e capacidades. Padrões escolares sem os papéis relatados não induzem a invenção desses papéis.
- Separação entre ambiente, material/aplicativo e equipamento, com perguntas contextualizadas e no máximo três na rodada inicial.
- Revisão efetiva de campos preenchidos e vazios; substituição e remoção de opções; nova confirmação após alterações.
- Progresso ligado à execução e à solicitação correta; referências e localizações dos apoios utilizados, sem fingir busca online nas normas.

Os relatórios registram os testes realmente executados. Reconhecimento limitado de narrativa e cobertura incompleta de tarefas permanecem limitações; não há nova avaliação com participantes. A revisão geral da saída, a unificação de Ouvir/Parar e a redução de caixas repetidas ficam fora desta entrega.

## Alterações desta revisão

- Consumo operacional da matriz funcional existente, com requisitos derivados separados dos fatos relatados e das capacidades individuais desconhecidas.
- Vínculos de MF-01/MF-02 e operacionalização auditiva MF-11 sobre origens já existentes, com limites documentais e de participante.
- Escolha de percursos pertinentes para esclarecimento, em vez da união de todas as exigências; primeira rodada de até três perguntas, refinamento opcional e desconhecidos não repetidos.
- Um cartão por configuração, com passos ligados ao texto de ação selecionado. Nenhuma modalidade é acrescentada apenas pelo título genérico do caso da entrevista.
- Apoios condicionais distinguem condição não confirmada de recurso impedido; não se apresentam como prontos nem como atendimento integral do grupo.
- Versionamento e regressão próprios. Nenhum arquivo do repositório MADO ou da tese é alterado.

Os relatórios em `evidence/` identificam quais verificações desta revisão foram executadas. Não há nova avaliação humana.

## Histórico da RC2

- Interpretação de acesso e comunicação de conteúdo por função, sem procurar o tema da aula como cenário cadastrado.
- Condições pessoais e respostas separadas por participante; nenhuma forma de comunicação inferida por diagnóstico.
- Requisitos funcionais derivados de conhecimentos compatíveis antes da seleção do padrão, com o vínculo que produziu a derivação.
- Contratos existentes de aplicação deslocados da lista fixa em Python para os registros versionados; nenhuma capacidade específica de Matemática acrescentada.
- Citações bibliográficas recuperadas, URLs estruturadas e seis origens normativas reconferidas em seções online. Não houve leitura integral de 156 referências nem download de PDFs.
- Catálogo, desenho documental e explicação do exemplo derivados da mesma base; relações históricas, pendentes e mobilizadas ficam distintas.

O resultado efetivo e os limites são registrados nos relatórios desta revisão. Uma composição parcial não comprova cobertura integral da turma, notação matemática ou resultado educacional. A versão da tese e o repositório MADO permanecem intactos.

### Correção do diálogo e da leitura — 11/10/2026

A revisão de interface preserva `46e318a` no histórico. Corrige a repetição de uma
pergunta já respondida quando o motor ainda devolve outros requisitos do mesmo
campo. A conclusão do passo do diálogo passa a ser registrada separadamente da
satisfação das condições; não é necessário marcar todas as opções para avançar.

As perguntas identificam atividade e participante, mostram progresso previsto e
têm opções clicáveis em toda a área. O complemento de comunicação não é perguntado
duas vezes. A geração tem um estado de espera visível e a leitura da orientação
separa ação, combinação modal, condição de uso e aprofundamento. Apoio parcial e
suspensão permanecem estados distintos. As opções completas, parciais e pendentes
do compositor são apresentadas em grupos próprios.

Motor, base, consultas, ontologia e versões da tese não foram alterados. A
identidade desses arquivos é conferida pelo manifesto. As evidências novas
pertencem ao diálogo e à projeção da saída, não a uma nova validação ontológica
ou humana. [Detalhes do percurso e testes](visao-guiada.md).

## Histórico: 1.4.0-rc1 — fundamentação examinável

O repositório independente parte do conteúdo público de `natacsham/MADO`, commit `d660b773ed08038a7a543205575a16fc22d2c1c2`. A importação é o commit raiz deste novo histórico; não altera a origem nem a tese.

Esta evolução acrescenta `ContribuicaoNaArticulacao`, corrige a atribuição direta não sustentada de F07 a K43 e distingue trajetória, construção analítica e aplicação. O executor registra correspondências, entradas utilizadas, verificações, exclusões e cobertura parcial em `execution_evidence`, sem armazenar casos.

Não foram acrescentados novos padrões de recomendação. A apresentação compartilha a mesma projeção do motor e conserva contribuições parciais ou pendentes. A inspeção dos registros existentes não deve ser apresentada como leitura de todos os documentos originais.

Consulte [fundamentação documental](fundamentacao-documental.md), [explicação pública](explicacao-publica.md) e [verificação](verificacao.md). Os resultados efetivos da versão são os vinculados em `web/evidence/report.json`.

## Histórico preservado: revisão 1.3.0-rc1

Esta revisão sucede a versão usada na tese. Ela não substitui retroativamente seus arquivos, telas ou avaliações. A primeira referência técnica inspecionada para esta evolução foi o pacote local RC4-UI3-DEMO-FIX2; a prova anterior de execução no navegador não incluía todas as suas correções.

## Matriz de problemas, correções e verificação

| Problema identificado | Correção desta revisão | Como verificar | Impacto e limite |
| --- | --- | --- | --- |
| Critérios e conhecimentos compartilhavam uma configuração, mas uma consulta podia combiná-los indiscriminadamente. | Registrar `AplicacaoDeCriterio` com apoio, origem e justificativa específicos. | Comparar os pares do catálogo com os retornados em RDF; CA02 no padrão de organização não deve ganhar apoios além de K38/K43. | Corrige precisão da rastreabilidade, não comprova qualidade pedagógica. |
| Recuperação e aplicabilidade podiam ser interpretadas como equivalentes. | Verificar condições e impedimentos após recuperação direta ou por articulação. | Casos incompatíveis devem ficar excluídos ou suspensos, com motivo; não podem sustentar uma configuração. | Pode reduzir saídas antes aceitas permissivamente. Isso deve ser registrado, não ocultado. |
| Integridade podia ser verificada somente quando determinados campos já existiam. | Alvos e restrições SHACL que detectem ausência de configuração ou fundamentação. | Remover deliberadamente vínculo obrigatório em cópia de teste e exigir violação. | Integridade estrutural não substitui conferência documental. |
| A prova web estava atrás da versão local. | Adaptar o motor e a interface atualizados para execução no navegador. | Comparar decisões e rastreabilidade nativas e no navegador, normalizando somente diferenças irrelevantes de ordenação. | Não usar aprovação antiga como aprovação da nova versão. |
| O instrumento local registrava sessões e exportações. | Retirar persistência e manter apenas o caso atual em memória na variante pública. | Inspecionar armazenamento, tráfego e arquivos virtuais; atualizar e abrir outra aba. | O provedor da página ainda pode manter registros técnicos de acesso. |
| O pacote de trabalho continha registros e textos que não devem ser redistribuídos integralmente. | Gerar distribuição pública por lista de materiais autorizados. | Examinar o resultado da distribuição, não apenas os arquivos exibidos na interface. | Alguns trechos serão apenas localizáveis pela referência original. |
| Documentação técnica tornava difícil compreender a contribuição. | Explicar um caso, funções modais e limites antes das classes e consultas. | Conferir correspondência do exemplo com a base e navegação por teclado e leitura. | Uma explicação didática não é evidência adicional de eficácia. |

## Preservação científica

- A tese V21 e a MADO 1.2.0-RC4 não são editadas por esta entrega.
- Resultados anteriores mantêm a identificação de sua versão.
- A revisão possui relatório e manifesto próprios.
- Material da especialista não é convertido silenciosamente em regra nem apresentado como nova sessão.
- Suspensão e redução de cobertura decorrentes de regras mais rigorosas devem constar dos resultados.

## Situação das evidências

Esta matriz descreve o compromisso da revisão. O resultado de cada execução deve ser consultado em `evidence/`. A existência da linha de teste acima não significa que ela passou. Resultados com leitor de tela, avaliação humana e desempenho em dispositivos diferentes somente podem ser afirmados quando efetivamente registrados.
