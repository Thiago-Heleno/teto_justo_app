# Instruções para agentes de IA

Aplicam-se a todo o repositório.

## Escopo

- Entregue a menor alteração clara e completa para o pedido atual (_mínima_).
- Reaproveite soluções e padrões que o projeto já tem antes de criar estruturas, camadas, dependências ou configurações.
- Preserve o código e as alterações existentes que não fazem parte da tarefa.
- Escreva a lógica sem depender do banco de dados; a mudança fica no backend.
- Mantenha fora do código: abstrações prematuras, comentários que repetem o código, arquivos sem uso e funcionalidades não pedidas.

## Testes e validação

- Teste comportamento observável e relevante, um teste por comportamento. Testes tautológicos e testes feitos só para subir a cobertura ficam de fora.
- Nomeie cada teste pelo que ele de fato exercita: um teste com banco falso é teste de unidade, não de integração.
- Valide em proporção ao risco da mudança e relate apenas o que foi executado, com o resultado real.

## Secrets

Mantenha tokens, senhas, chaves e valores de `.env` fora de código, testes, logs e documentação. Use o nome da variável (como em `.env.example`).

## Documentação

- Use caminhos relativos à raiz do repositório ou exemplos genéricos. Caminhos absolutos da máquina e nomes de pastas pessoais ficam de fora.
- Em comandos com caminho relativo, indique a pasta de partida.

## Resumo de implementação importante

Para uma implementação importante (ajustes pequenos não entram), escreva ou atualize `contexto/sprint_N/<nome_curto>.md`, com N da sprint da tarefa. Exemplos de nome: `testes_sessao.md`, `autenticacao.md`.

- Atualize o resumo existente da mesma funcionalidade em vez de criar outro.
- Registre só fatos: objetivo; arquivos e comportamentos alterados; decisões técnicas; validações realmente executadas com resultado; limitações, riscos e pendências reais.
- Escreva o resumo como registro de decisões, com informação nova e sem dados sensíveis.
- Pergunte ao usuário a sprint quando os arquivos e o pedido não a revelam.
