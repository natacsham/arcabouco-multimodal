# Fundamentação documental da articulação

Esta revisão pertence ao repositório independente **Arcabouço Multimodal**, versão `1.4.0-rc1`. Não modifica a MADO `1.3.0-rc1` publicada nem reescreve a avaliação da tese. O acréscimo torna inspecionável **qual parcela de cada registro foi empregada numa articulação**; não transforma uma referência bibliográfica em prova de toda a decisão.

## Três percursos diferentes

1. **Trajetória:** quais estudos, artefatos e personas antecederam e informaram outros trabalhos. Uma ligação histórica não prova, por si, a adequação de uma configuração.
2. **Fundamentação:** qual conteúdo de um trecho contribui, qual operação analítica o relaciona a outros conteúdos, que compreensão é proposta e quais limites permanecem.
3. **Execução:** diante de condições confirmadas, quais conhecimentos e articulações foram recuperados, qual aplicação de critério os mobilizou e qual configuração foi composta. A seleção computacional não realiza novamente a síntese intelectual das publicações.

As seis classes centrais permanecem. `ContribuicaoNaArticulacao` é um registro auxiliar qualificado entre **uma articulação, seu conhecimento resultante e um trecho**. A fonte é obtida exclusivamente pelo trecho, evitando uma lista independente que possa divergir dele.

```text
Trecho ─ trechoDeFonte → Fonte
   ↑ contribuicaoDoTrecho
Contribuição ─ contribuicaoNaArticulacao → Articulação
   └ contribuicaoParaConhecimento → Conhecimento resultante

Aplicação de critério ─ aplicacaoMobilizaContribuicao → Contribuição
   ├ criterioAplicado → Critério
   ├ origemDaAplicacao → Origem documental do critério
   ├ conhecimentoDaAplicacao → Conhecimento selecionado
   └ aplicacaoNaConfiguracao → Configuração da decisão
```

`statement` descreve a contribuição em paráfrase; `contribution_role` informa seu papel; `justification` delimita o emprego e o que o trecho **não** demonstra. Em cada articulação, `operation_explanation` e `added_understanding` distinguem a operação da compreensão acrescentada. `authorship` e `reconstruction_origin` registram a origem desta explicitação retrospectiva, sem atribuí-la automaticamente às publicações antigas ou a uma nova aprovação da autora.

## O que foi efetivamente conferido

Foram introduzidas **26 contribuições**, relativas a **11 conhecimentos (K35–K45)** e **nove articulações**. Todas estão como `CONFERIDA_NO_REGISTRO`, não como `CONFERIDA_NO_DOCUMENTO`.

A conferência de 08/10/2026 utilizou os registros preservados da base RC4. Os PDFs originais não estavam disponíveis nos caminhos consultados; portanto, não houve reconferência de paginação, contexto integral ou fidelidade da extração ao original. O arquivo documental de origem foi identificado pelo SHA-256 `ca2ac9142e44e5198c6fe916a8a25a8a02c4e473be4c87511aab29bf2e3afbe1`. Ele permanece fora desta distribuição pública. Os textos públicos das contribuições são paráfrases analíticas, não transcrições dos documentos.

| Estado | Significado | O que não significa |
|---|---|---|
| `CONFERIDA_NO_DOCUMENTO` | Contribuição conferida no documento identificado | Validação empírica de toda a decisão |
| `CONFERIDA_NO_REGISTRO` | Conferência no registro de extração preservado | Nova leitura do documento original |
| `PENDENTE` | Ligação ou conteúdo ainda não conferido | Autorização de emprego pela aplicação de critério |

O responsável registrado é a assistência computacional que realizou esta conferência. A data é civil (`YYYY-MM-DD`); nenhum horário foi inventado. Os estados históricos de curadoria das articulações foram preservados como histórico; não substituem o nível desta nova conferência.

## Piloto: CA02, K38 e K43

No padrão `PAD-ORGANIZAR-CONTEUDO-PERSISTENTE`, a aplicação de **CA02** relaciona explicitamente **K38 e K43** às origens **ORI-0012, ORI-0013 e ORI-0014**. Essas origens são itens de MMI e WCAG preservados na extração dos critérios. Elas sustentam a aplicação do critério; não são automaticamente promovidas a fontes de cada conhecimento.

| Registro da contribuição | Parcela empregada | Operação e fronteira |
|---|---|---|
| K38 / TD-EV13 | Preservação da informação numa representação descritiva acessível | Oferece um princípio de preservação de significado, não um procedimento completo de autoria |
| K38 / TD-EV34 | Organização de formatos e mediação na persona | Relaciona formatos a funções de organização; unidade persistente é reconstrução posterior |
| K38 / TD-EV29 | Revisão, confirmação e feedback no redesenho de mensagens | A função pode informar outra tarefa; não autoriza copiar o fluxo de mensagens |
| K38 / TD-EV42 | Contextualização da persona em tarefa e fluxo do SIGAA | Apoia delimitar a tarefa; não demonstra efeito de uma nova atividade educacional |
| K43 / TD-EV34 e TD-EV36 | Organização de formatos, tecnologias assistivas e condições das personas | Contribui para discutir coordenação de modalidades, sem provar uma ordem universal |
| K43 / TD-RC3-REF-09 e TD-RC3-REF-10 | Contextualização educacional e relação entre perfil, tarefa e recursos | Informa aplicação situada; não comprova causalmente redução de sobrecarga ou aprendizagem |

**ART-TRF-04** articula as parcelas de K38 para propor conteúdo estruturado, persistente, revisável e com autoria preservada. **ART-REF-03** distingue a preservação de significado (K42) da coordenação dos formatos (K43). A decisão de estruturar determinada tarefa em blocos continua sendo uma proposta situada cuja adequação precisa ser observada.

Assim, o percurso do piloto é: **condição identificada → função requerida → conhecimentos selecionados → contribuições delimitadas e operação analítica → aplicação de CA02 com suas próprias origens → configuração**. Não é uma dedução OWL de que um trecho normativo determina a solução inteira.

CA02 não recebeu uma ligação global indiscriminada a esses conhecimentos. Sua associação permanece na **aplicação situada**, dentro da configuração. A consulta CQ3 agora expõe a contribuição exata para o par articulação–conhecimento e para o trecho cuja fonte é consultada.

## Correção e pendências mantidas

- **K43:** F07 foi retirada de `fonte_ids` e de `derivadoDe`, pois nenhum dos trechos registrados de K43 provinha dessa fonte. Não foi removida de outros conhecimentos que possuem seu próprio trecho de F07. Um vínculo futuro exige extração específica.
- **ART-REF-03:** foram explicitados TD-EV36, TD-RC3-REF-10 e TD-ORI-0014, já presentes entre os trechos dos conhecimentos resultantes. Isso qualifica ligações existentes; não representa uma nova extração original.
- **K36:** a acessibilidade dos formatos encontra apoio nos registros, mas duração curta, perguntas de retomada e uso para contraste/processo incluem decisões de projeto que requerem avaliação própria.
- **K37:** os registros conferidos contextualizam formatos e necessidades; não fundamentam diretamente as mecânicas propostas para jogo, ordenação ou efeito de aprendizagem. Sua revisão de fundamentação permanece `PENDENTE`.
- **K35, K38–K45:** parcelas foram documentadas, mas a revisão é `PARCIAL`; condições de transferência, formulações novas e avaliação de efeito não são tratadas como resolvidas.

Portanto, **ter uma contribuição conferida não torna o conhecimento integralmente comprovado nem a decisão completa**. O estado documental e as pendências são distintos da cobertura funcional calculada pelo executor. Texto livre de condição ou limite permanece explicação documental, não regra executada, salvo quando há uma condição controlada implementada e identificada como tal.

## Exportação e controles

Na raiz do repositório:

```powershell
python -B scripts/build_traceability_rdf.py
python -B scripts/build_traceability_rdf.py --check
python -B -m unittest discover -s tests -p test_contributions.py
```

O exportador lê somente `data/knowledge-base.json`, o grafo público existente e `ontology/main.ttl`. Substitui as declarações pela versão canônica, projeta as ligações curadas, remove vínculos obsoletos e grava Turtle e RDF/XML. Não depende dos documentos privados nem executa o antigo gerador da distribuição. A serialização ordenada torna a repetição verificável por bytes; o Turtle gerado usa o subconjunto N-Triples, enquanto `main.ttl` permanece a especificação legível.

Os controles impedem contribuição sem trecho, fonte divergente, conhecimento que não seja produto da articulação, justificativa vazia, estado desconhecido e aplicação que tente usar contribuição de outro conhecimento ou de articulação não mobilizada. Contribuições pendentes podem permanecer na base, mas não ser ligadas a uma aplicação como fundamento conferido. Decisões `GERADA_PARCIAL` mantêm os requisitos estruturais de configurações e fundamentos; a aprovação SHACL não as promove a decisões completas.

Os testes são sintéticos e verificam esse contrato. OWL 2 DL, HermiT, SHACL da base completa e testes do executor são relatados separadamente em `evidence/`. Nenhum desses resultados substitui a conferência dos documentos originais, a revisão autoral da síntese ou a avaliação de uso.
