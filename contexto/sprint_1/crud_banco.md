# Banco de Dados (Supabase/Postgres) — Sprint 1

## O que foi feito
Modelagem e criação das tabelas do banco de dados no Supabase (Postgres), via migrations SQL versionadas em `docs/migrations/`.

## Diagramas
- `docs/diagrama_ER.png` — Diagrama Entidade-Relacionamento.
- `docs/diagrama_Lógico.png` — Diagrama Lógico.

## Migrations aplicadas
1. **`01.sql`** — criação das tabelas principais:
   - `Usuario`, `Casa`, `Tarefa`, `Sessao` (entidades principais)
   - `Pertencer` (usuário ↔ casa, com pontuação/score) e `Atribuida` (usuário ↔ tarefa) — tabelas de relacionamento (N:N)
   - Chaves estrangeiras entre elas, com regras de exclusão (`ON DELETE CASCADE`/`RESTRICT`/`SET NULL`) definindo o que acontece quando um registro pai é apagado.
2. **`02.sql`** — migração dos IDs de `INT` para `UUID` (usando `gen_random_uuid()`). Motivo: UUID evita IDs previsíveis/sequenciais (mais seguro) e é o padrão mais comum ao usar Supabase.
3. **`03.sql`** — ajuste pontual: coluna `telefone` da tabela `Casa` alterada para `varchar`.

## Estrutura principal do banco
- **Usuario**: dados de login/perfil (nome, email, `senha_hash`, telefone, foto, tipo de usuário).
- **Casa**: representa uma residência/grupo, vinculada a um usuário "dono".
- **Tarefa**: tarefas domésticas, com pontuação, prazos e status, vinculadas a uma casa e a um usuário.
- **Sessao**: controle de sessões de login (token, expiração).
- **Pertencer**: quais usuários pertencem a quais casas, com uma pontuação (`Score`) por usuário/casa.
- **Atribuida**: quais tarefas foram atribuídas a quais usuários.

## Para falar com o professor
- O modelo de dados já reflete o domínio do app (casas, tarefas, pontuação/gamificação, múltiplos usuários por casa).
- Uso de UUID como chave primária é uma decisão de segurança consciente, documentada na própria migration.
- Falta (próximos passos): políticas de Row Level Security (RLS) do Supabase ainda não foram configuradas para essas tabelas.
