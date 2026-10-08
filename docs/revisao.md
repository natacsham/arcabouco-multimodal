# Revisão 1.3.0-rc1

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
