# Contrato da casa — Task 207 (Sprint 3)

## Objetivo e autorização

O backend concentra a escolha da casa após o login: lista somente as casas do
usuário autenticado, permite entrar por convite e sair de uma casa. A entrega
não cria nem aplica migration ou altera manualmente o banco. Todas as rotas usam
`Authorization: Bearer <sessao>`; sem sessão válida, retornam `401`.

O proprietário é `casa.fk_usuario_id`, definido pela sessão ao criar a casa.
Para exibir controles de administração, o frontend compara esse campo de
`CasaResposta` com o campo `id` da resposta de `GET /usuarios/eu`. O backend
impõe a permissão em cada ação. O proprietário pode acessar a casa mesmo se
uma casa antiga não tiver seu vínculo em `pertencer`; novas casas já criam esse
vínculo ativo com `score` zero.

## Rotas e respostas

| Método e rota | Entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- |
| `POST /casas/` | `CasaCriar`: `nome`, `endereco`, `foto` Base64 opcional, `timezone` IANA opcional | `201 CasaResposta`; cria a casa e vincula o proprietário | `400` foto inválida |
| `GET /casas/?inicio=0&limite=100` | Paginação após o filtro por propriedade ou vínculo ativo do usuário da sessão | `200 CasaResposta[]`, ordenada de forma estável, sem duplicatas; `[]` quando não houver casas | — |
| `GET /casas/{id}` | UUID da casa | `200 CasaResposta` para proprietário ou morador ativo | `403` sem acesso; `404` casa inexistente |
| `PATCH /casas/{id}` | Campos parciais de `CasaAtualizar`: `nome`, `endereco`, `foto`, `timezone` | `200 CasaResposta`; só proprietário | `400` foto inválida ou nenhum campo aplicável; `403` sem cargo; `404` casa inexistente |
| `DELETE /casas/{id}` | UUID da casa | `200 true`; só proprietário | `403` sem cargo; `404` casa inexistente; `409` há dados vinculados |
| `GET /casas/{id}/moradores` | UUID da casa | `200 MoradorResposta[]` para proprietário ou morador ativo | `403` sem acesso; `404` casa inexistente |
| `POST /casas/{id}/convites` | Sem corpo; só proprietário | `200 {"convite": string, "expira_em": datetime}` | `403` sem cargo; `404` casa inexistente; `503` segredo indisponível |
| `POST /casas/entrar` | `{"convite": string}` | `200 CasaResposta`; vínculo ativo é idempotente e vínculo inativo é reativado sem zerar `score` | `400` convite inválido ou expirado; `404` casa removida; `409` vínculo alterado simultaneamente (tentar novamente); `503` segredo indisponível |
| `DELETE /casas/{id}/sair` | UUID da casa; inativa somente o vínculo do usuário da sessão | `204` sem corpo; preserva saldo e histórico | `404` casa ou vínculo ausente/inativo; `409` proprietário ou tarefas abertas |

`CasaResposta` conserva `id`, `nome`, `endereco`, `foto`, `fk_usuario_id` e
`timezone`. `MoradorResposta` conserva `id`, `nome`, `email`, `telefone`,
`foto` e `score`; lista apenas quem possui vínculo ativo em `pertencer`.
UUID inválido na rota ou payload incompatível com o schema retorna `422`.
Para `PATCH`, campos `null` são ignorados; `null` não remove uma foto existente.

Sair marca `pertencer.ativo = false`, sem excluir o vínculo, o saldo ou os
eventos de pontos. Um morador com histórico pode sair; tarefas `pendente` ou
`atrasada` atribuídas a ele na casa precisam ser reatribuídas antes. Enquanto
inativo, não aparece na lista de casas ou de moradores e perde acesso como
morador. Um novo convite reativa o mesmo vínculo e recupera seu saldo.

## Convites e configuração

O convite é compartilhável e reutilizável até expirar em 24 horas. O backend
assina versão, ID da casa, ID do proprietário emissor e expiração com
HMAC-SHA-256. Na entrada, confere a assinatura, o prazo e se o emissor ainda é
proprietário. Não é possível entrar somente com o UUID da casa. Não há uso
único nem revogação individual de convites.

Defina `CASA_CONVITE_SECRET` com ao menos 32 bytes aleatórios no ambiente de
todas as instâncias do backend. Ausência ou valor inadequado devolve `503`
somente nas rotas de emitir e aceitar convites. A rotação do segredo invalida
todos os convites anteriores; seu valor não deve ser incluído no frontend,
documentação ou logs. A configuração está descrita no `README.md` e em
`.env.example`.

## Dependência de implantação

A PR #99 já adicionou `docs/migrations/27.sql`, que cria
`pertencer.ativo` e preserva o histórico de pontos ao impedir exclusão física
do vínculo. O backend da main e este contrato dependem dessa coluna. A
aplicação da migration em qualquer banco não foi verificada nesta Task 207;
antes da implantação, o responsável pelo ambiente deve confirmar seu estado
e seguir a revisão em `contexto/sprint_2/revisao_casa_pertencer.md`.

## Verificação

O contrato foi conferido no OpenAPI gerado, incluindo os schemas de convite,
entrada e erro e os status das rotas de casa. A suíte sem os seis arquivos de
integração que escrevem no Supabase passou com `333 passed` (um aviso de
depreciação do Starlette). O Ruff passou nos arquivos Python alterados e
`git diff --check` não encontrou erros. Nenhum teste foi executado contra o
Supabase real.
