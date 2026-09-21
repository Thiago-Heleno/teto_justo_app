# Penalidade de pontuação proporcional ao atraso máximo — Sprint 2

## Objetivo

Fazer a perda de pontuação por atraso ser proporcional ao `atraso_maximo` de
cada tarefa (não mais uma taxa fixa por `tipo_de_penalidade`), e marcar a
tarefa automaticamente como `nao_feito` quando o atraso atinge esse limite,
sem crédito de pontos.

Exemplo motivador: `atraso_maximo = 5` → perda de 20% por dia de atraso
(1º dia: -20%, 2º: -40%, 3º: -60%, 4º: -80%, 5º: -100% e a tarefa vira
`nao_feito`).

## Decisões tomadas

- **Gatilho da transição para `nao_feito`**: não existe nenhum job/cron no
  projeto hoje. A transição é feita pelo backend, de forma preguiçosa
  ("lazy"), sempre que a tarefa é consultada (`GET /tarefas/{id}`,
  `GET /tarefas/`, `GET /tarefas/casa/{id_casa}`). Se ninguém consultar a
  tarefa, seu `estado_atual` no banco pode continuar `atrasada` mesmo depois
  do atraso máximo — mas a pontuação, calculada pelo trigger de finalização
  com base em `NOW()`, já é `0` de qualquer forma nesse caso.
- **`atraso_maximo` obrigatório**: passou a ser campo obrigatório em
  `TarefaCriar`, como `peso`, já que antes não existia na API nem tinha
  restrição no banco.
- **`tipo_de_penalidade` substituído e removido**: a taxa diária de desconto
  do trigger de pontuação deixou de ser fixa por `tipo_de_penalidade`
  (10/20/30/40%/dia) e passou a ser `100% / atraso_maximo`, variável por
  tarefa. Como a coluna ficou sem nenhum uso (nunca havia sido exposta na
  API) e competia conceitualmente com a nova regra por tarefa, ela foi
  removida do banco em `docs/migrations/11.sql`.

## Alterações

- `docs/migrations/10.sql`: nova migration que
  - torna `tarefa.atraso_maximo` `NOT NULL` com `CHECK (atraso_maximo > 0)`;
  - substitui `fn_tarefa_finalizada_credita_pontos` para calcular
    `taxa_diaria := 100.0 / NEW.atraso_maximo` em vez de usar
    `tipo_de_penalidade`. O restante da função (cálculo de `dias_atraso`,
    `GREATEST(0, ...)`, crédito em `score_event`/`pertencer.score`) não
    mudou — ver [credito_pontos_tarefa.md](credito_pontos_tarefa.md).
- `docs/migrations/11.sql`: remove a coluna `tipo_de_penalidade` e a
  constraint `CK_Tarefa_tipo_de_penalidade`, já sem uso após a migration
  anterior.
- `schemas/tarefa.py`: `atraso_maximo: int = Field(gt=0)` obrigatório em
  `TarefaCriar`; opcional (`Optional[int]`, também `gt=0`) em
  `TarefaAtualizar`; obrigatório em `TarefaResposta`.
- `services/tarefa.py`:
  - novo método `_sincronizar_estado_por_atraso`: se a tarefa não está em
    estado final (`finalizado` ou `nao_feito`), calcula `dias_atraso` da
    mesma forma que o trigger SQL (`FLOOR` da diferença em dias entre agora
    e `data_fim`, piso em `0`) e, se `dias_atraso >= atraso_maximo`, atualiza
    `estado_atual` para `nao_feito` no banco antes de responder.
  - `_montar_resposta` chama essa sincronização antes de montar a resposta,
    cobrindo `buscar_tarefa`, `listar_tarefas`, `listar_tarefas_por_casa` e o
    fim de `atualizar_tarefa` (que chama `buscar_tarefa` para devolver o
    estado atualizado).

## Validação

- Testes unitários novos em `test_servico_tarefa_unitario.py`: tarefa
  expirada vira `nao_feito` ao ser buscada; tarefa dentro do `atraso_maximo`
  não muda de estado; tarefa já `finalizado`/`nao_feito` não é
  ressincronizada mesmo com atraso enorme.
- Teste de integração novo em `test_tarefas_integracao.py`
  (`test_tarefa_expirada_vira_nao_feito_ao_ser_consultada`): cria uma tarefa
  com `data_fim` 10 dias no passado e `atraso_maximo = 2`, consulta por
  `GET` e confirma `estado_atual == "nao_feito"`. Não executado localmente
  (depende de Supabase de testes).
- Suíte unitária completa (excluindo integração): 82 testes aprovados.
- A fórmula de desconto em si (`100 / atraso_maximo` por dia) só existe no
  trigger SQL — não foi replicada em Python, então não há teste unitário
  Python para o valor exato de pontos creditados; isso depende de validação
  contra um Supabase real.

## Atualização — 21/09/2026: `pontuacao` obrigatória

A pendência abaixo foi resolvida: `peso` (`dificuldade`) serve apenas para
dividir o trabalho entre responsáveis e **não** determina `pontuacao` — são
conceitos independentes, cada um exposto e obrigatório na API.

- `docs/migrations/12.sql`: `tarefa.pontuacao` passou a `NOT NULL` (mantendo
  a constraint já existente `CK_Tarefa_pontuacao CHECK (pontuacao IN (10,
  20, 30, 40))`).
- `schemas/tarefa.py`: novo tipo `PontuacaoTarefa = Literal[10, 20, 30, 40]`;
  `pontuacao` obrigatório em `TarefaCriar` e `TarefaResposta`, opcional em
  `TarefaAtualizar`.
- `services/tarefa.py`: `_montar_resposta` inclui `"pontuacao":
  tarefa["pontuacao"]` (sem tradução de nome, a coluna já se chama
  `pontuacao` na API e no banco).
- Testes unitários e de integração atualizados com `pontuacao` em todos os
  payloads de criação de tarefa.

## Pendência

- Nenhuma trava impede finalizar manualmente (`PATCH estado_atual=finalizado`)
  uma tarefa cujo atraso já ultrapassou `atraso_maximo`; o resultado é
  simplesmente `0` pontos creditados, não um erro. Não foi pedido bloquear
  essa transição.
- A transição para `nao_feito` só acontece quando alguém consulta a tarefa.
  Uma listagem no app (tela de tarefas) já cobre a maioria dos casos reais,
  mas não há garantia de que o estado no banco reflita a realidade sem
  nenhuma consulta prévia.
- Testes de integração não executados neste ambiente (sem credenciais de
  Supabase de teste); validar antes do merge.
