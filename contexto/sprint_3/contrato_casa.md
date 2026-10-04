# C1 — Contrato dos endpoints da casa

Revisão de `src/backend/routers/casa.py`, schemas e serviços. Todas as rotas
exigem `Authorization: Bearer <token>` (`401` sem sessão válida). UUID,
parâmetros de paginação ou payload inválidos retornam `422`.

| Método e rota | Entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- |
| `POST /casas/` | JSON `nome`, `endereco`, `foto` Base64 opcional, `timezone` IANA opcional (padrão `America/Sao_Paulo`). Proprietário vem da sessão. | `201 CasaResposta`; cria também o vínculo ativo do proprietário. | `400` foto Base64 inválida; `500` falha ao criar casa/vínculo. |
| `GET /casas/` | Query `inicio` (padrão 0, mínimo 0), `limite` (padrão 100, mínimo 1). | `200 CasaResposta[]` das casas próprias e com vínculo ativo; ordenada, sem duplicatas; `[]` se vazia. | — |
| `GET /casas/{id_casa}` | UUID no caminho. | `200 CasaResposta` para proprietário ou morador ativo. | `403` sem acesso; `404` casa inexistente. |
| `PATCH /casas/{id_casa}` | JSON parcial: `nome`, `endereco`, `foto`, `timezone`. `null` é ignorado. | `200 CasaResposta` atualizada; só proprietário. | `400` sem campo aplicável ou foto inválida; `403` não proprietário; `404` casa inexistente. |
| `DELETE /casas/{id_casa}` | UUID no caminho; só proprietário. | `200 true`. | `403` não proprietário; `404` casa inexistente; `409` dados vinculados impedem exclusão. |
| `GET /casas/{id_casa}/moradores` | UUID no caminho. | `200 MoradorResposta[]` de vínculos ativos: `id`, `nome`, `email`, `telefone`, `foto`, `score`. | `403` sem acesso; `404` casa inexistente. |
| `POST /casas/{id_casa}/convites` | UUID no caminho; sem corpo; só proprietário. | `200 {"convite", "expira_em"}`. | `403` não proprietário; `404` casa inexistente; `503` segredo de convite ausente/inválido. |
| `POST /casas/entrar` | JSON `{"convite": "…"}`; usuário é identificado pela sessão. | `200 CasaResposta`; vínculo ativo é idempotente, vínculo inativo é reativado preservando `score`. | `400` convite inválido/expirado; `404` casa removida; `409` conflito concorrente; `503` segredo indisponível. |
| `DELETE /casas/{id_casa}/sair` | UUID no caminho; sem corpo; sai somente o usuário da sessão. | `204` sem corpo; inativa o vínculo e preserva saldo/histórico. | `404` casa ou vínculo ausente/inativo; `409` proprietário ou tarefas abertas atribuídas ao morador. |

`CasaResposta` contém `id`, `nome`, `endereco`, `foto`, `fk_usuario_id` e
`timezone`; a foto é devolvida em Base64. O frontend identifica o administrador
comparando `fk_usuario_id` com `GET /usuarios/eu`. A API já tem as três rotas
citadas como lacunas na descrição da C1 (`GET /casas/`, `POST /casas/entrar` e
`DELETE /casas/{id_casa}/sair`); não falta criá-las. A entrada é por convite,
nunca apenas pelo UUID da casa.

Para as telas: o proprietário não pode sair; moradores com tarefas `pendente`
ou `atrasada` precisam reatribuí-las antes de sair. A autorização é aplicada
no backend. A emissão/aceitação de convite requer `CASA_CONVITE_SECRET` no
ambiente da API; convites expiram em 24 horas.
