# Verificação, evidências e limites

**Versão alvo: MADO 1.4.0-rc1.** Consulte o índice `web/evidence/report.json` e seus relatórios vinculados. Ele aceita apenas entradas e código correspondentes aos hashes atuais. Relatórios herdados de 1.3 não comprovam esta evolução.

Além das verificações anteriores, `tests/test_contributions.py` examina a contribuição documental e `tests/test_execution_evidence.py` testa a fidelidade da explicação ao que o motor executou. `tests/traceability-browser.mjs` executa as duas apresentações e os mesmos casos estruturados no navegador. `evidence/parity-report.json` compara o conteúdo produzido em Python local e Pyodide.

A conferência documental pode permanecer **no registro preservado**, **parcial** ou **pendente**. Nem consistência OWL nem sucesso na consulta elevam esse estado. Esta entrega não substitui a conferência do documento original indisponível.

## Perguntas diferentes exigem evidências diferentes

| Camada | Pergunta | Evidência esperada |
| --- | --- | --- |
| Processamento | Os arquivos RDF/OWL podem ser lidos? | Resultado do parser e arquivos de entrada. |
| Perfil OWL 2 DL | A formalização respeita o perfil declarado? | Relatório da ferramenta de perfil. |
| Consistência | Há contradições ou classes insatisfatíveis indevidas? | Reasoner, versão, resultado e lista de classes. |
| Integridade | Os dados têm os vínculos e valores exigidos? | Relatório SHACL, incluindo testes de ausência de campos. |
| Questões de competência | As consultas respondem às perguntas previstas? | Entrada, consulta, resultado esperado e obtido. |
| Composição | A orientação respeita condições e fundamentação? | Casos positivos, negativos, incompletos e adversos. |
| Articulação | Relacionar conhecimentos acrescentou algo observável? | Comparação controlada com e sem expansão. |
| Navegador | A variante pública conserva a semântica da execução? | Comparação nativa/navegador e registro de diferenças. |
| Acessibilidade da interface | As pessoas conseguem acessar e operar os fluxos testados? | Inspeção automatizada e testes humanos delimitados. |
| Adequação percebida | A saída faz sentido para o contexto examinado? | Julgamento humano documentado na versão avaliada. |

Uma execução sem erro não implica aprovação de todas essas camadas. Da mesma forma, satisfação com a orientação não prova correção OWL, aprendizagem ou generalização.

## Oito perguntas orientadoras

1. O contexto está representado e suas informações ausentes são reconhecidas?
2. Quais conhecimentos são pertinentes e por quais correspondências?
3. Quais fontes, trechos, perspectivas e articulações os sustentam?
4. Quais critérios são fundamentados naquele emprego?
5. Quais decisões, resultados e limites anteriores são pertinentes?
6. Qual decisão pode ser composta para o contexto?
7. Qual é a cadeia completa e exata de rastreabilidade?
8. Quando o conhecimento ou a informação é insuficiente?

As consultas versionadas em `queries/` são a especificação executável. A aprovação deve considerar conteúdo esperado, não apenas a existência de linhas no resultado.

## Testes que fazem diferença

- **Apoio exato:** CA02 não pode receber um conhecimento apenas porque ambos aparecem na mesma configuração.
- **Ausência:** remover uma configuração ou origem obrigatória precisa ser detectado.
- **Incompatibilidade:** uma relação de complementação não pode anular uma restrição de aplicação.
- **Recursos:** confirmar, não informar e impedir um recurso precisam produzir estados coerentes.
- **Novo arranjo:** testar uma combinação não cadastrada como cenário completo, sem acrescentar conteúdo para aprová-la.
- **Interpretação separada:** testar o contexto estruturado independentemente da capacidade de interpretar sua narrativa.
- **Articulação:** comparar conhecimentos e funções efetivamente empregados, não somente o volume recuperado.
- **Privacidade:** não conservar narrativas, orientações ou avaliações após limpar ou encerrar o caso.

## O que não pode ser concluído

Este demonstrador não prova que as orientações melhoram resultados educacionais, que funcionam para qualquer pessoa, que qualquer narrativa é compreendida, ou que a interface satisfaz integralmente um padrão de acessibilidade.

A revisão especializada anterior pertence à sua versão e ao procedimento registrado. Não é uma avaliação automática das modificações deste repositório. Não houve uma nova avaliação humana apenas porque o código foi atualizado.

## Como conferir sem usar a interface

Leia as classes e propriedades no Turtle e abra a distribuição RDF/XML no Protégé. Confira o identificador de versão antes de executar um reasoner. A seleção do reasoner e o estado de execução devem ser acompanhados do relatório técnico; uma captura de tela é evidência complementar.

Examine SHACL e consultas separadamente: um reasoner opera sob semântica OWL e não deve ser usado como substituto da detecção operacional de informações ausentes.

Guarde versão, hash, ferramenta, entrada e resultado ao reproduzir uma execução. Sem esses elementos, resultados de versões diferentes podem ser confundidos.

## Histórico da apresentação 1.3 — 07/10/2026

As medições e relatórios abaixo pertencem à origem preservada; não são testes desta versão. O índice atual acima separa a nova evidência.

A página inicial foi simplificada; foram acrescentados ajustes de leitura, retorno ao topo, navegação entre AMADO e MADO e metadados de descoberta. Essa revisão não modifica o motor, a base, as consultas ou os arquivos da ontologia. A identidade desses artefatos é conferida pelos hashes do manifesto.

`evidence/site-presentation-report.json` registra os testes específicos de conteúdo, teclado, contraste, ampliação, largura reduzida, links e metadados. A regressão do AMADO permanece em `browser-report.json`; um teste público somente é considerado atual quando seus arquivos correspondem ao manifesto publicado. Enquanto isso, o relatório consolidado identifica a verificação pública como pendente e mantém o resultado anterior como histórico, sem apresentá-lo como teste da nova interface.

Os controles de leitura não substituem uma avaliação com pessoas usuárias ou leitores de tela. A preparação para busca também não equivale a indexação confirmada: veja [o procedimento de Search Console](indexacao-google.md).

### Documentação técnica: sequência UML e compactação

A revisão seguinte preserva `bbd1df9` no histórico e substitui os cartões escalonados por um diagrama de sequência UML: pessoa, interface, motor e base são linhas de vida; mensagens e retornos mostram a consulta; o fragmento `alt` distingue orientação e insuficiência. A preparação prévia do conhecimento permanece separada da execução. A notação segue a [UML 2.5.1](https://www.omg.org/spec/UML/2.5.1), sem representar medições reais de duração.

A página passa a se chamar **Documentação técnica**, usa a largura disponível e recolhe explicações complementares. Em uma janela de 1280 × 900 px, com texto em 100% e detalhes fechados, a altura da página passou de 4687 para 3085 px; a figura, de aproximadamente 1459 para 693 px. Esses números descrevem o layout testado, não tempo de leitura ou ganho de usabilidade medido com participantes.

O SVG mantém texto selecionável e escala com a ampliação. Em telas estreitas, somente o diagrama tem rolagem horizontal; a opção **Ler a sequência em texto** oferece o mesmo percurso em HTML, com ordem de leitura linear. Foram conferidos teclado, foco, ampliação de 200% e ausência de rolagem horizontal da página em 320 px. Não houve teste humano com leitor de tela nesta revisão.

`tests/documentation-layout.mjs` reproduz a medição atual; a variável `MADO_LAYOUT_REF=bbd1df9` mede a versão anterior diretamente do Git. `site-presentation-report.json` registra os testes da apresentação. `navigation-delta-report.json` registra a comparação de conteúdo e a navegação atual nas duas visões do AMADO: seus HTML mudam apenas o rótulo do link para a documentação. Motor, base, consultas, ontologia e arquivos operacionais permanecem idênticos. O teste de navegação não executa o motor e não conta execuções funcionais anteriores como novas; essas evidências conservam a identificação histórica.
