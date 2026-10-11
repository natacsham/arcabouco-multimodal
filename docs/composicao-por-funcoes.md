# Composição por funções no AMADO

O endereço de uso continua sendo o AMADO do **arcabouco-multimodal**. O repositório MADO anterior não recebe estas alterações.

## O que foi conectado

O campo **Conte o problema que você quer resolver** é a entrada comum do AMADO. Para tarefas de escrita ou revisão explicitamente reconhecidas em contexto de aprendizagem, a interface usa o compositor 2.0.0-alpha2. Ele examina capacidades separadas de entrada e revisão, suas condições e uma relação documentada entre elas. Não procura o identificador de um cenário completo nem copia uma orientação pronta para o par escolhido.

A composição ainda tem um recorte: produzir e revisar uma contribuição digital em contexto de aprendizagem, ou revisar texto já disponível. Os casos de outras tarefas continuam usando o mecanismo anterior. Não há conversão silenciosa de qualquer narrativa para estas duas tarefas.

## Como experimentar

1. Conte o desafio por texto ou ditado. Por exemplo: uma pessoa precisa escrever uma contribuição para uma atividade de aprendizagem e conferir o rascunho com leitura em voz.
2. Se faltar uma condição necessária, o AMADO pergunta. Responda o que souber; **não sei ainda** não é convertido em aprovação.
3. Confira **Este é o seu desafio?** e confirme antes de gerar a orientação.
4. Leia a orientação. Condições, alternativas e fundamentos permanecem disponíveis em blocos recolhidos.
5. Corrija o relato para comparar outra condição. A orientação anterior perde a confirmação e precisa ser construída novamente.

Os exemplos opcionais são preparados para demonstração, não fatos de uma pessoa real. A apresentação anterior, com campos detalhados e a seção de composição separada, permanece em `amado/completo.html` e `amado/completo-guiado.html`.

**Completa** significa que há um percurso fundamentado para as funções representadas. **Condicional** exige informação adicional. **Parcial** preserva etapas sustentadas sem afirmar que resolvem a tarefa inteira. Uma etapa intermediária pode depender de conteúdo ainda não produzido. As opções não são classificadas da melhor para a pior.

Esta tela planeja uma forma de interação. Não executa o editor nem a leitura do rascunho recomendados e não avalia a aprendizagem. O ditado do relato e a leitura em voz da orientação são controles da interface, distintos das capacidades propostas para a atividade.

## Onde está a base consultada

- `data/knowledge-base.json`: registros públicos da trajetória, inclusive conhecimentos, contribuições, fontes e origens de critérios.
- `experimental/v2/trajectory-bindings.json`: aplicações analíticas que explicitam o que K28, K29 e K41 acrescentam às condições das capacidades; CA38 é empregado especificamente na entrada por teclado.
- `experimental/v2/schema.ttl`, `base.ttl` e `extensions/audio-review.ttl`: funções, capacidades, condições, relações e fundamentos de interação multimodal.
- `experimental/v2/trajectory.py`: confere os registros por hash e projeta seus vínculos em RDF, sem alterar o conteúdo da base.
- `experimental/v2/composer.py`: examina as condições e combina etapas compatíveis.

O navegador carrega uma cópia verificada desses arquivos no pacote `web/amado/assets/base.zip`. Não consulta arquivos particulares, Google Drive, PDFs ou o GitHub durante a decisão. Atualizar um arquivo no repositório exige reconstruir, testar e publicar o pacote; uma referência nova sozinha não cria uma capacidade.

## Como conferir o fundamento

O percurso é **condição informada → verificação → capacidade para uma função → aplicação de critério e conhecimento → articulação e contribuições → trecho localizado e fonte**. A ligação entre entrada e revisão também possui fundamentação própria, sobre o mesmo rascunho.

K41 acrescenta verificações de esforço, compatibilidade e percepção do resultado da entrada. K28 e K29 contribuem para coordenar produção e revisão e separar a forma de entrada da apresentação usada para conferir o conteúdo. O artigo é empregado por esses conhecimentos; o nome da plataforma educacional em que ocorreu sua aplicação não define o alcance da contribuição.

Os registros reconstruídos ou documentalmente parciais conservam seus estados. A aplicação operacional é uma proposta analítica, não uma nova leitura integral dos artigos nem validação pela especialista. Sequência de entrada e revisão não é rotulada automaticamente como complementaridade CARE.

## Reprodução e limites

As verificações do módulo estão em `experimental/v2/evidence/`. A integração no navegador possui testes próprios, separados dos testes da versão da tese. A paridade compara a execução local e a execução real no navegador; não substitui avaliação com pessoas.

Não há cadastro, gravação do caso ou histórico. Limpar, atualizar ou fechar descarta as informações. Os campos desconhecidos não são completados por diagnóstico e as etapas pendentes não são apresentadas como aprovadas.

`web/amado/intake.mjs` converte sinais explícitos do relato em propostas de contexto. Recursos presentes não provam capacidade funcional; diagnósticos não completam condições. A síntese fica disponível para conferência, e só o contexto confirmado chega ao motor.
