# Executar e verificar esta versão

Os exemplos e relatórios de regressão são **testes técnicos sintéticos**. Não são logs da sessão da especialista.

## Abrir o AMADO localmente

Com Python 3.12 ou posterior, na pasta do repositório:

```text
python -m http.server 8767 --directory web --bind 127.0.0.1
```

Abra `http://127.0.0.1:8767/`. O Python do navegador e a base são distribuídos junto com a página; o servidor acima só entrega arquivos. Aguarde o indicador de carregamento. Selecione um exemplo, confira as informações, confirme o contexto e construa a orientação. O botão de limpar também interrompe operações pendentes.

O caso não é salvo. Recarregar ou fechar a aba descarta a entrada e a orientação. Os arquivos estáticos podem ser mantidos no cache do navegador; eles não contêm o caso digitado. A hospedagem pode manter seus próprios registros de acesso aos arquivos públicos.

## Verificar o motor e a estrutura

```text
python -m pip install -r requirements.txt
python scripts/verify_public.py
python scripts/run_regression.py
python scripts/build_web.py
```

`verify_public.py` executa os testes Python e SHACL, confere o hash da verificação formal registrada e informa falhas. Essa conferência de hash não é uma nova execução do HermiT.

Para repetir perfil e reasoner, use Java 11+ e ROBOT 1.9.10 obtidos de suas distribuições oficiais:

```text
python scripts/verify_reasoner.py --robot CAMINHO/robot.jar --java CAMINHO/java
```

Consulte `--help` para opções. O relatório inclui ferramenta, comandos, hash e resultados. Os caminhos privados são separados da evidência pública. Não é necessário instalar o Protégé para reproduzir os testes; `ontology/mado.owl` também pode ser aberto nele para inspeção.

## Navegador

Os testes usam Playwright e um navegador Chromium. `tests/browser.mjs` contém o percurso de teclado, exemplos, alterações, descarte e reflow. Os relatórios informam o navegador utilizado e o alcance da inspeção. NVDA e VoiceOver continuam pendentes; esses testes não certificam conformidade integral.

## Reconstrução dos dados públicos

O repositório já contém a projeção pública. `scripts/prepare_public_data.py` permite reconstruí-la a partir da base documental autorizada que utilizei na pesquisa; essa base privada não é necessária para executar a demonstração. O script não altera a origem. Citações não autorizadas, avaliações individuais e caminhos locais não fazem parte da distribuição pública.

Não promova um resultado do AMADO automaticamente a conhecimento da ontologia. Uma incorporação exige revisão da fonte, contexto, resultado observado, limites e decisão de curadoria em outra versão.
