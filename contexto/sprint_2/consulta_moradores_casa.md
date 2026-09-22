# Consulta de moradores da casa

## Objetivo

Adicionar `GET /casas/{id_casa}/moradores` (ECH-144) para listar os usuários
vinculados a uma casa específica, com o score de cada um — desbloqueia telas
que precisam escolher responsáveis reais por casa.

## Alterações

- Novo schema `MoradorResposta` em `schemas/casa.py` (`id`, `nome`, `email`,
  `telefone`, `foto`, `score`).
- Novo método `ServicoCasa.listar_moradores` em `services/casa.py`: confirma
  que a casa existe (404 caso contrário), busca os vínculos em `pertencer`
  filtrados por `fk_casa_id`, busca os dados dos usuários correspondentes com
  `.in_("id", ...)` e junta cada usuário com o seu `score`.
- Nova rota `GET /casas/{id_casa}/moradores` em `routers/casa.py`, protegida
  por autenticação (mesmo nível de `buscar_casa`: qualquer usuário logado
  pode consultar, não só quem já mora na casa).
- Decisão de modelagem: a lista reflete só quem tem vínculo em `pertencer`.
  O administrador da casa (`casa.fk_usuario_id`) é um papel separado e só
  aparece na lista se também tiver vínculo próprio em `pertencer` — mesmo
  padrão já usado em `garantir_responsaveis_da_casa`
  (`services/autorizacao.py`).

## Validação

- 3 testes unitários novos em `test_servico_casa_unitario.py` (moradores com
  score, casa inexistente → 404, casa sem vínculos → lista vazia).
- Suíte de `ServicoCasa`: 20/20 testes passando. Suíte completa do backend
  (exceto integração): 93 testes unitários passando, sem regressões.
- `ruff check` sem erros.
- Testes de integração não executados (dependem de credenciais do Supabase).
