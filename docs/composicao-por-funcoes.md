# Composição por funções no AMADO

O endereço de uso continua sendo o AMADO do **arcabouco-multimodal**. O repositório MADO anterior não recebe estas alterações.

## O que foi conectado

O campo **Qual é o seu desafio de acessibilidade hoje?** é a entrada comum do AMADO. O compositor examina funções representadas, suas capacidades, condições e relações documentadas. Não procura o identificador de um cenário completo nem copia uma orientação pronta para o par escolhido. Os contratos de aplicação vêm dos registros versionados, não de uma lista de casos em Python.

A entrada comum encaminha escrita com revisão e revisão de texto ao compositor por funções. Preparação e acesso a conteúdo educacional, assim como as demais tarefas, seguem o motor existente, conforme os padrões contemplados pela base. O assunto da aula não é chave de seleção. Reconhecer uma tarefa não garante que todas as funções necessárias possuam capacidade implementada.

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

Os documentos de origem ficam ligados por URL, edição e localização aos registros existentes. A curadoria consulta esses documentos **antes da publicação**, conserva a contribuição extraída e registra seu limite. O [catálogo e percurso da extração](https://natacsham.github.io/arcabouco-multimodal/ontologia/#fontes) não é um acervo de PDFs nem uma segunda base decisória.

## Um desafio com pessoas diferentes

“Ensinar um conteúdo complexo de Matemática a uma turma com dois estudantes surdos e um estudante cego” propõe uma tarefa de aprendizagem com participantes distintos. O intérprete não procura uma aula de Matemática cadastrada e não deduz Libras, leitura textual ou leitor de tela por diagnóstico.

O relato inicial exige confirmar a atividade digital, recursos e formas de acesso de cada grupo. Se a tarefa identificada for ampla demais, o AMADO pergunta qual atividade operacional está envolvida, usando os conceitos existentes. Necessidades, papéis de preparação e operação dos recursos são perguntados quando exigidos pelos padrões pertinentes. Uma resposta sobre leitor de tela é ligada apenas ao participante correspondente; não é copiada para os estudantes surdos. Recursos compartilhados, como um editor disponível à professora, são diferentes de capacidades pessoais.

Na rota de acesso a uma página digital, após as confirmações, o motor existente reutiliza `PAD-CONTEUDO-WEB-EQUIVALENTE`, com K10, K42, ART-REF-03 e aplicações de CA01, CA02 e CA74. Não é uma nova regra para Matemática. A articulação acrescenta nove vínculos exatos de fundamentação nessa escolha; não acrescenta outra configuração. O compositor por funções e esse motor são camadas distintas, disponíveis na mesma interface.

Quando não houver relação ou capacidade operacional para toda a tarefa, conserva o apoio parcial e informa o que continua sem cobertura. Isso não significa que as fontes não contenham conhecimento útil: pode faltar sua ligação operacional verificada ao padrão. Uma pergunta pessoal ou documental pendente impede alegar cobertura completa, mas não apaga automaticamente uma parte fundamentada. Retirar uma condição nuclear, como a operação do leitor de tela nessa rota, bloqueia a configuração afetada. Não se apresenta esse apoio ao acesso como prova de ensino da notação matemática, atendimento por Libras ou melhoria da aprendizagem.

Uma resposta pendente não precisa inutilizar uma rota já sustentada: os controles distinguem escolha pronta, alternativa condicional e segmento parcial. A revisão apenas adapta interpretação, correspondências e contratos existentes; não acrescenta um texto pronto específico para Matemática.

## Como conferir o fundamento

O percurso é **condição informada → verificação → capacidade para uma função → aplicação de critério e conhecimento → articulação e contribuições → trecho localizado e fonte**. A ligação entre entrada e revisão também possui fundamentação própria, sobre o mesmo rascunho.

K41 acrescenta verificações de esforço, compatibilidade e percepção do resultado da entrada. K28 e K29 contribuem para coordenar produção e revisão e separar a forma de entrada da apresentação usada para conferir o conteúdo. O artigo é empregado por esses conhecimentos; o nome da plataforma educacional em que ocorreu sua aplicação não define o alcance da contribuição.

Os registros reconstruídos ou documentalmente parciais conservam seus estados. A aplicação operacional é uma proposta analítica, não uma nova leitura integral dos artigos nem validação pela especialista. Sequência de entrada e revisão não é rotulada automaticamente como complementaridade CARE.

## Reprodução e limites

As verificações do módulo estão em `experimental/v2/evidence/`. A integração no navegador possui testes próprios, separados dos testes da versão da tese. A paridade compara a execução local e a execução real no navegador; não substitui avaliação com pessoas.

Não há cadastro, gravação do caso ou histórico. Limpar, atualizar ou fechar descarta as informações. Os campos desconhecidos não são completados por diagnóstico e as etapas pendentes não são apresentadas como aprovadas.

`web/amado/intake.mjs` converte sinais explícitos do relato em propostas de contexto. Recursos presentes não provam capacidade funcional; diagnósticos não completam condições. A síntese fica disponível para conferência, e só o contexto confirmado chega ao motor.
