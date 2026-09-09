# CRUD de Usuário (Backend) — Sprint 1

## O que foi feito
Implementação do CRUD de usuários no backend, usando **FastAPI** + **Supabase** como client de banco. PR #4 (`feature/crud-usuario`).

## Arquitetura em camadas
O backend segue um padrão de camadas, cada pasta com uma responsabilidade única:

- `core/` — conexão/configuração de infraestrutura (client do Supabase).
- `schemas/` — "contratos" dos dados: o que a API aceita receber e o que ela devolve (validação automática via Pydantic).
- `services/` — regra de negócio: verificações, criptografia de senha, decisões de erro. É quem fala com o banco.
- `routers/` — as URLs da API. Só recebem a requisição e delegam pro `service`.

## Endpoints disponíveis
| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/usuarios/` | Cria um usuário novo |
| `GET` | `/usuarios/{id}` | Busca um usuário por ID |
| `PATCH` | `/usuarios/{id}` | Atualiza campos parciais de um usuário |

Ainda **não implementado**: exclusão (`DELETE`) e listagem de usuários.

## Regras de negócio já implementadas
- Não permite dois usuários com o mesmo e-mail (erro 400).
- Senha nunca é salva em texto puro — é criptografada com `bcrypt` (lib `passlib`) antes de ir pro banco.
- A resposta da API nunca expõe a senha/hash do usuário, mesmo que o banco retorne esse campo.
- Atualização parcial (PATCH) só aceita nome, email e telefone — ainda não permite trocar senha por essa rota.

## Para falar com o professor
- Já existe separação clara de camadas (facilita manutenção e troca futura de banco de dados).
- Segurança básica de senha (hash com bcrypt) já está no lugar desde o início.
- Falta (próximos passos): autenticação/login (tabela `Sessao` já existe no banco, mas rota de login ainda não foi criada), rota de exclusão de usuário, e testes automatizados.
