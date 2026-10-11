# Composição por funções no AMADO

O endereço de uso continua sendo o AMADO do **arcabouco-multimodal**. O repositório MADO anterior não recebe estas alterações.

## O que foi conectado

A seção **Combinar formas de escrever e revisar**, disponível nas duas apresentações, usa o compositor 2.0.0-alpha2. Ele examina capacidades separadas de entrada e revisão, suas condições e uma relação documentada entre elas. Não procura o identificador de um cenário completo nem copia uma orientação pronta para o par escolhido.

A composição ainda tem um recorte: produzir e revisar uma contribuição digital em contexto de aprendizagem, ou revisar texto já disponível. Os casos de outras tarefas continuam usando o mecanismo anterior. Não há conversão silenciosa de qualquer narrativa para estas duas tarefas.

## Como experimentar

1. Abra a seção de composição no AMADO e escolha a tarefa.
2. Informe as condições e recursos: **sim**, **não** ou **a confirmar**. O exemplo sintético apenas ajuda a conhecer os campos; suas premissas não são fatos de uma pessoa real.
3. Confira as informações e peça a composição.
4. Veja as etapas propostas e abra os fundamentos junto de cada etapa.
5. Altere uma condição, confirme novamente e compare. Por exemplo: impedir a saída de áudio inviabiliza a revisão por leitura em voz; não inviabiliza automaticamente a entrada por teclado.

**Completa** significa que há um percurso fundamentado para as funções representadas. **Condicional** exige informação adicional. **Parcial** preserva etapas sustentadas sem afirmar que resolvem a tarefa inteira. Uma etapa intermediária pode depender de conteúdo ainda não produzido. As opções não são classificadas da melhor para a pior.

Esta tela planeja uma forma de interação. Não executa um editor, reconhecimento de fala, leitura do rascunho, envio de conteúdo ou avaliação da aprendizagem.

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
