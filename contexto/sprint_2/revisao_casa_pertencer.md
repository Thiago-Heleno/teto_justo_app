# Revisão de casa e pertencer

## Decisão para a C1

- O administrador é `casa.fk_usuario_id`; o morador comum tem vínculo ativo em
  `pertencer`. Não será criado cargo global ou uma nova tabela de cargos.
- O proprietário não pode sair da própria casa. Um morador pode sair mesmo com
  pontos: a saída marca `pertencer.ativo = false` e preserva `score`,
  `score_event` e atribuições de tarefas encerradas.
- Tarefas `pendente` ou `atrasada` atribuídas ao morador na casa devem ser
  reatribuídas antes da saída; a tentativa retorna `409`.
- Ao voltar, o mesmo vínculo é reativado, com o saldo anterior. A chave
  `(fk_usuario_id, fk_casa_id)` continua única.
- Entrada e reentrada exigem autorização do administrador. Uma futura rota de
  entrada pelo próprio usuário deve exigir convite ou aprovação; conhecer o
  UUID da casa não basta.
- Moradores inativos não aparecem na lista/placar/ranking, não recebem novas
  tarefas ou rodízios e não têm acesso como moradores. O administrador ainda
  pode consultar o saldo e o extrato históricos. A auditoria considera também
  os vínculos inativos.

A API atual de `pertencer` ainda exige administrador para POST e DELETE. A C1
deve definir o contrato das novas rotas de listar minhas casas, entrar e sair;
a C2 implementará autorização e rotas. A saída poderá ser iniciada pelo próprio
morador ou pelo administrador, respeitando as mesmas regras. A saída da C1
precisa usar as regras acima e devolver `409` para proprietário ou tarefa
aberta, `404` para vínculo inexistente/inativo. Entrada em vínculo ativo
continua `400`; reativação preserva o saldo; entrada sem autorização retorna
`403`. A C6 não adiciona
rotas nesta etapa.

## Modelo e migration

`docs/migrations/27.sql` está preparada e **não foi aplicada**. Ela adiciona
`pertencer.ativo BOOLEAN NOT NULL DEFAULT TRUE`, define `score DEFAULT 0` para
novos vínculos, cria índice parcial `(fk_casa_id, fk_usuario_id) WHERE ativo`
para listagem e índice `(fk_usuario_id, fk_casa_id)` em `score_event`. A FK
composta de eventos para `pertencer` impede exclusão física ou evento sem
vínculo, preservando o histórico após a inativação. A PK existente já atende
consultas pelo par usuário/casa.

Após comunicar a definição à C1, conferir as consultas abaixo, aplicar a
migration e só então implantar o backend alterado; ele consulta a coluna
`ativo` em todas as operações de moradia.

Antes de aplicar, conferir o histórico de migrations no ambiente alvo e
executar estas consultas de leitura:

```sql
SELECT e.fk_usuario_id, e.fk_casa_id, COUNT(*) AS eventos
FROM score_event AS e
LEFT JOIN pertencer AS p
  ON p.fk_usuario_id = e.fk_usuario_id AND p.fk_casa_id = e.fk_casa_id
WHERE p.fk_usuario_id IS NULL
GROUP BY e.fk_usuario_id, e.fk_casa_id;

SELECT c.id, c.fk_usuario_id
FROM casa AS c
LEFT JOIN pertencer AS p
  ON p.fk_usuario_id = c.fk_usuario_id AND p.fk_casa_id = c.id
WHERE c.fk_usuario_id IS NULL OR p.fk_usuario_id IS NULL;

SELECT COUNT(*) AS saldos_nulos,
       COUNT(*) FILTER (WHERE score < 0) AS saldos_negativos
FROM pertencer
WHERE score IS NULL OR score < 0;

SELECT a.fk_usuario_id, t.fk_casa_id, COUNT(*) AS tarefas_abertas
FROM atribuida AS a
JOIN tarefa AS t ON t.id = a.fk_tarefa_id
LEFT JOIN pertencer AS p
  ON p.fk_usuario_id = a.fk_usuario_id AND p.fk_casa_id = t.fk_casa_id
WHERE t.estado_atual IN ('pendente', 'atrasada')
  AND p.fk_usuario_id IS NULL
GROUP BY a.fk_usuario_id, t.fk_casa_id;
```

Eventos sem vínculo impedem a FK e exigem reconciliação caso a caso. Casas
sem proprietário/vínculo e tarefas abertas atribuídas a não moradores
também precisam de análise, sem correção automática nesta migration. `score`
continua nullable para não alterar dados legados sem uma reconciliação.

## Backend e limites

`ServicoPertencer` inativa o vínculo na saída, reativa na entrada e filtra
consultas comuns por `ativo`. Autorização, criação/conclusão/reabertura de
tarefas, escolha de participantes do rodízio e consultas do placar também
consideram esse estado. Atribuições encerradas e participações em rodízios
permanecem gravadas; ao reativar, o morador volta a ser elegível aos rodízios
em que já participava. Se um rodízio ficar sem participantes ativos, o job
retorna `409` até a configuração ser ajustada.

Arquivos alterados: serviços de vínculo, autorização, casa, tarefa, rodízio e
placar em `src/backend/services/`, além dos testes de vínculo, placar e
reabertura de tarefa em `src/backend/tests/`.

A checagem de tarefas abertas e a inativação usam requisições separadas ao
Supabase. Uma atribuição concorrente ainda pode atravessar essa janela; o
backend deve ser o único escritor dessas operações até existir transação
compartilhada. A migration não foi executada contra PostgreSQL/Supabase e os
dados reais não foram consultados. `py_compile` e `git diff --check` passaram.
Os testes não rodaram: o ambiente Python local não tem as dependências e a
instalação via `pip` não encontrou os pacotes no índice disponível.
