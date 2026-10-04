# Consulta de moradores da casa

## Objetivo

Adicionar `GET /casas/{id_casa}/moradores` (ECH-144) para listar os usuários
vinculados a uma casa específica, com o score de cada um — desbloqueia telas
que precisam escolher responsáveis reais por casa.

## Alterações

- Novo schema `MoradorResposta` em `schemas/casa.py` (`id`, `nome`, `email`,
  `telefone`, `foto`, `score`).
- Novo método `ServicoCasa.listar_moradores` em `services/casa.py`: confirma
  que a casa existe (404 caso contrário), busca os vínculos ativos em
  `pertencer` filtrados por `fk_casa_id`, busca os usuários correspondentes com
  `.in_("id", ...)` e junta cada usuário com o seu `score`.
- Nova rota `GET /casas/{id_casa}/moradores` em `routers/casa.py`, protegida
  por autenticação e acesso à casa. Somente o proprietário ou um morador com
  vínculo ativo em `pertencer` pode consultar; outro usuário autenticado
  recebe `403` e casa inexistente retorna `404`.
- Decisão de modelagem: a lista reflete só quem tem vínculo ativo em
  `pertencer`. A saída inativa o vínculo e preserva saldo e histórico; a
  reentrada por convite reativa o mesmo vínculo sem zerar o `score`.
  A criação atual da casa insere seu proprietário (`casa.fk_usuario_id`) nesse
  vínculo com `score` zero, então ele aparece na lista. Casas antigas sem esse
  vínculo ainda permitem acesso ao proprietário, mas ele não aparece como
  morador até ter o vínculo; `garantir_responsaveis_da_casa` também o aceita
  como responsável pela propriedade.

O contrato vigente da casa está em `contexto/sprint_3/contrato_casa.md`.

## Validação

- 3 testes unitários novos em `test_servico_casa_unitario.py` (moradores com
  score, casa inexistente → 404, casa sem vínculos → lista vazia).
- Suíte de `ServicoCasa`: 20/20 testes passando. Suíte completa do backend
  (exceto integração): 93 testes unitários passando, sem regressões.
- `ruff check` sem erros.
- Testes de integração não executados (dependem de credenciais do Supabase).
