# Instruções para agentes de IA

Estas instruções se aplicam a todo o repositório.

## Qualidade e escopo

- Implemente somente o que for necessário para atender ao pedido atual.
- Evite "AI slop": código genérico, abstrações prematuras, comentários que apenas repetem o código, arquivos sem uso, testes tautológicos e funcionalidades não solicitadas.
- Antes de criar uma estrutura, verifique se o projeto já possui uma solução ou padrão reutilizável.
- Prefira a menor alteração clara e completa. Não adicione camadas, dependências ou configurações sem necessidade concreta.
- Teste comportamento observável e relevante. Não crie testes apenas para aumentar a quantidade ou a cobertura.
- Classifique os testes com precisão: não chame um teste com banco falso de integração real.
- Execute validações proporcionais ao risco da mudança. Nunca declare que algo foi executado ou aprovado se não foi.
- Preserve o código e as alterações existentes que não fazem parte da tarefa.
- Nunca registre secrets, tokens, senhas ou valores de `.env` em código, testes, logs ou documentação.

## Resumo obrigatório por sprint

- Ao finalizar cada sessão de trabalho que altere o repositório, crie ou atualize um arquivo Markdown em `contexto/sprint_N/`, usando a sprint correspondente à tarefa.
- Use um nome curto e descritivo, como `testes_sessao.md` ou `autenticacao.md`.
- Se já existir um resumo para a mesma funcionalidade, atualize-o em vez de criar outro arquivo duplicado.
- O resumo deve registrar apenas fatos relevantes:
  - objetivo da tarefa;
  - arquivos e comportamentos alterados;
  - decisões técnicas importantes;
  - testes ou validações realmente executados e seus resultados;
  - limitações, riscos ou pendências reais.
- Não transforme o resumo em diário de execução, não repita detalhes óbvios e não inclua informações sensíveis.
- Se a sprint não puder ser determinada pelos arquivos ou pelo pedido, confirme com o usuário antes de criar o resumo.
