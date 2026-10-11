# Executar e verificar esta versão

Os exemplos e relatórios de regressão são **testes técnicos sintéticos**. Não são logs da sessão da especialista.

## Abrir o AMADO localmente

Com Python 3.12 ou posterior, na pasta do repositório:

```text
python -m http.server 8767 --directory web --bind 127.0.0.1
```

Abra `http://127.0.0.1:8767/`. O Python do navegador e a base são distribuídos junto com a página; o servidor acima só entrega arquivos. Aguarde o indicador de carregamento. Conte o problema ou abra um exemplo, complete as informações necessárias, confirme o desafio e gere a orientação. **Informar outro problema** limpa o caso atual; durante uma operação, aguarde sua conclusão.

O caso não é salvo. Recarregar ou fechar a aba descarta a entrada e a orientação. Os arquivos estáticos podem ser mantidos no cache do navegador; eles não contêm o caso digitado. A hospedagem pode manter seus próprios registros de acesso aos arquivos públicos.

## Verificar o motor e a estrutura

```text
python -m pip install -r requirements.txt
python scripts/build_traceability_rdf.py
```

`verify_public.py` executa os testes Python e SHACL, confere o hash da verificação formal registrada e informa falhas. Essa conferência de hash não é uma nova execução do HermiT.

Para repetir perfil e reasoner, use Java 11+ e ROBOT 1.9.10 obtidos de suas distribuições oficiais:

```text
python scripts/verify_reasoner.py --robot CAMINHO/robot.jar --java CAMINHO/java
```

Consulte `--help` para opções. O relatório inclui ferramenta, comandos, hash e resultados. Os caminhos privados são separados da evidência pública. Não é necessário instalar o Protégé para reproduzir os testes; `ontology/mado.owl` também pode ser aberto nele para inspeção.

Após atualizar o relatório formal:

```text
python scripts/verify_public.py
python scripts/run_regression.py
python scripts/build_pilot.py
python scripts/build_web.py
python scripts/check_bundle.py
```

O piloto é uma projeção de uma execução técnica preparada, não uma sessão humana. Seu conteúdo não é escrito separadamente da base. A revisão documental continua necessária: o gerador não transforma registros pendentes em fontes conferidas.

## Navegador

A entrada simples atende aos dois motores. Tarefas de escrita e revisão explicitamente reconhecidas em contexto de aprendizagem são encaminhadas ao módulo `experimental/v2`. Condições desconhecidas precisam ser conferidas; recursos disponíveis não autorizam inferir capacidades. [Escopo e percurso dos dados](composicao-por-funcoes.md).

Verificação da apresentação simples:

```text
node tests/intake.mjs
node tests/simple-flow-browser.mjs
```

O segundo teste executa os motores reais por Pyodide, confere paridade com Python, confirmação e correção do caso, perguntas por informações ausentes, falha e recuperação do carregamento, descarte, teclado e reflow. O reconhecimento de voz é simulado somente para conferir os controles e a preservação do texto; não mede a precisão do ditado nem testa um microfone real. `SIMPLE_PUBLIC_URL=https://natacsham.github.io/arcabouco-multimodal/` executa o mesmo teste no endereço público e produz `simple-flow-public.json`.

Para verificar separadamente esse módulo:

```text
python -B experimental/v2/verify_trajectory.py --output experimental/v2/evidence/trajectory-report.json
python -B experimental/v2/verify.py
python -B -m unittest discover -s tests -p test_composition_bridge.py
node tests/composition-browser.mjs
```

Os testes usam Playwright e Chromium. Configure `AMADO_NODE_MODULES` com a pasta que contém Playwright e `AMADO_CHROMIUM` com o executável do navegador. Execute:

```text
node tests/traceability-browser.mjs
node tests/compare_browser.mjs
python scripts/audit_distribution.py
python scripts/publish_traceability.py
```

Os testes anteriores foram realizados na apresentação detalhada preservada. Seus relatórios só são reutilizados quando os hashes do motor, do pacote e dos arquivos da apresentação anterior continuam iguais. Eles não constituem uma nova avaliação da entrada simples. A comparação verifica a semântica nativa/navegador, não apenas o número de configurações. NVDA e VoiceOver continuam pendentes; estes testes não certificam conformidade integral.

`TRACE_PUBLIC_URL=https://natacsham.github.io/arcabouco-multimodal/` direciona os mesmos testes ao endereço publicado. Esse resultado é separado em `traceability-public.json`.

## Reconstrução dos dados públicos

O repositório já contém a projeção pública. Na 1.4, use `scripts/build_traceability_rdf.py`: os registros curados em `data/knowledge-base.json` e o esquema Turtle alimentam o RDF e a apresentação. `scripts/prepare_public_data.py` pertence ao processo de projeção 1.3 e não deve ser executado para substituir esta base curada. Citações não autorizadas, avaliações individuais e caminhos locais não fazem parte da distribuição pública.

Não promova um resultado do AMADO automaticamente a conhecimento da ontologia. Uma incorporação exige revisão da fonte, contexto, resultado observado, limites e decisão de curadoria em outra versão.
