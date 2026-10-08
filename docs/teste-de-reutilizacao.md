# Uma combinação que não estava cadastrada como cenário completo

Este é um teste técnico sintético da **1.3.0-rc1**, não um novo caso observado com participante. Foi executado diretamente com conceitos controlados, para separar a capacidade de composição da interpretação de uma narrativa.

## Entrada e controle

A entrada reuniu, no mesmo fluxo digital, **compreender o conteúdo de uma página e produzir/revisar mensagens sobre ele**, com condições de acesso não visual, teclado, leitor de tela, entrada por voz e revisão. Foram reutilizados conceitos e participações já representados. O contexto recebeu um identificador novo; nenhuma regra, configuração, fonte ou formulação foi adicionada para aprovar esse teste.

O script `scripts/run_regression.py` registra a entrada e confere que os hashes da base não mudaram. Confira o objeto `combinacao_nao_cadastrada` em `evidence/regression-report.json`.

## O que a articulação acrescentou

| Recuperação isolada | Recuperação com articulações |
| --- | --- |
| K10, K18, K27 e K29 recuperados | Os anteriores mais K41, K42 e K43 recuperados |
| Um padrão elegível: acesso a conteúdo web equivalente | Dois padrões elegíveis: acesso equivalente e comunicação multiformato |
| Duas funções cobertas | Quatro funções cobertas |
| Seleção do modo pela condição e feedback ainda não cobertos | Essas duas funções passam a estar cobertas pelo segundo padrão |

**Recuperação não é uso.** A decisão final empregou K10 e K42 no acesso à página, e K41 e K42 na comunicação. K43 foi recuperado, mas não foi incorporado automaticamente à decisão. Foram mobilizadas as articulações `ART-REF-03` e `ART-REF-05`.

As aplicações dos critérios também são específicas:

- No acesso à página: CA01 foi sustentado por K10/K42; CA02 e CA74, por K42.
- Na comunicação: CA23 e CA74 foram sustentados por K42; CA88, por K41.

Cada aplicação contém seus próprios registros de origem e sua justificativa. Não se associa todo critério a todo conhecimento da configuração.

## Mudança controlada

Ao marcar a entrada por voz como impedida, mantendo a tarefa de leitura e seus recursos, o padrão de comunicação deixou de ser elegível; o padrão de acesso à página permaneceu. Não foi apresentada uma resposta histórica inteira com um identificador novo.

Esse resultado demonstra sensibilidade às condições registradas, **não** que a base saiba recompor qualquer alternativa. Embora o padrão descreva teclado como alternativa, esta implementação não transforma automaticamente essa descrição em outro padrão operacional elegível. Isso é um limite concreto para evolução: explicitar requisitos alternativos de entrada e verificá-los, em vez de supor capacidade a partir de um texto.

## Conclusão delimitada

Foi demonstrada reutilização composicional de padrões existentes em uma combinação não cadastrada como cenário completo, com alteração diante de um impedimento e contribuição observável das articulações. Não foi demonstrada invenção automática de um novo princípio, cobertura de toda tarefa nem compreensão irrestrita de uma narrativa. A nova combinação foi estruturada deliberadamente; o reconhecimento textual tem testes e limites próprios.

Relatórios: `evidence/regression-report.json`, `evidence/native-cases.json` e `evidence/parity-report.json`. O último compara navegador e Python local, distinguindo identificadores temporários da semântica produzida.
