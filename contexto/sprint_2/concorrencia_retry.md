# Concorrência sem funções no banco: compare-and-swap com retry

Este documento registra a decisão de arquitetura para a migração das funções
PL/pgSQL (`registrar_conclusao_tarefa`, `criar_rotatividade`,
`registrar_ocorrencia_rotativa`, `excluir_tarefa_sem_credito`,
`excluir_vinculo_sem_credito`) para o backend Python, e o padrão de
concorrência que substitui `SELECT ... FOR UPDATE` nelas.

**Status em 2026-09-28:** `registrar_conclusao_tarefa` foi migrada (1 de 5) —
ver `_creditar_e_finalizar`/`_creditar_pertencer`/`_finalizar_estado_tarefa`
em [services/tarefa.py](../../src/backend/services/tarefa.py). A implementação
real revelou um caso de corrida que a decisão original não previu — ver
"Lição aprendida" abaixo. As outras quatro funções continuam no banco,
pendentes.

## Objetivo

Registrar por que e como a lógica hoje presa em funções do Supabase vai para
o backend, sem depender de nenhum comportamento escondido em PL/pgSQL — nem
cálculo de regra de negócio, nem controle de concorrência.

## Contexto

A decisão nasceu no desenho do ECH-159 (reabertura de tarefa com REVERSAL,
sessão de 27/09): a equipe decidiu que a reabertura deveria ser feita em
Python, sem nova função PL/pgSQL, mesmo isso quebrando o padrão usado até
então (as cinco funções acima, todas aplicadas ao Supabase real em 27/09).
Esta sessão generaliza essa decisão: nenhuma função nova vai para o banco
daqui pra frente, e as cinco existentes serão migradas para o backend, uma
por vez.

Motivo: manter toda a lógica de negócio (regras, validações, controle de
concorrência) visível e testável em Python, sem duas fontes de verdade
(SQL e código) para o mesmo comportamento.

## O padrão de hoje: `SELECT ... FOR UPDATE`

As cinco funções usam `FOR UPDATE` pra travar a linha (`tarefa`, `casa`,
`pertencer`, `atribuida`) durante a transação, garantindo que duas chamadas
concorrentes não leiam e escrevam em cima do mesmo dado inconsistente.
Isso só existe porque a função roda inteira dentro de uma única transação
Postgres, controlada pelo próprio banco.

## Por que não dá pra replicar isso direto no backend

O backend fala com o Supabase via `create_client`
([core/database.py:15](../../src/backend/core/database.py)), o cliente
PostgREST — cada `.table(...)`/`.rpc(...)` é sua própria requisição HTTP e
sua própria transação. Não existe como abrir uma transação Postgres e
mantê-la aberta entre múltiplas chamadas desse client. Logo, `FOR UPDATE`
não é uma opção no backend sem trocar de cliente de banco (fora de escopo
por ora).

## O padrão que substitui: compare-and-swap (CAS)

Em vez de travar a linha antes de ler, o backend lê o estado atual, calcula
a mudança, e escreve de volta com um `UPDATE` condicional: o `WHERE` da
escrita exige que a linha ainda esteja exatamente como foi lida. Se alguém
escreveu por cima entre a leitura e a escrita, a condição não bate, zero
linhas são afetadas, e o backend sabe que precisa decidir o que fazer.

Esse padrão já existe no projeto, em
[`ServicoTarefa._sincronizar_estado_por_atraso`](../../src/backend/services/tarefa.py):

```python
resposta = (
    self.supabase.table("tarefa")
    .update({"estado_atual": "nao_feito"})
    .eq("id", str(tarefa["id"]))
    .in_("estado_atual", ["pendente", "atrasada"])
    .eq("data_fim", tarefa["data_fim"])
    .eq("atraso_maximo", tarefa["atraso_maximo"])
    .execute()
)
```

O `.eq()`/`.in_()` reproduz exatamente a checagem de "os dados ainda são os
mesmos que eu li" que as funções SQL fazem hoje comparando `NEW`/`OLD`
manualmente.

## Duas variantes: aceitar a falha vs. retry de verdade

`_sincronizar_estado_por_atraso` **não** tenta de novo se o CAS falhar — só
busca a linha atual e aceita o que estiver lá (`resposta.data[0] if
resposta.data else self._buscar_tarefa_bruta(...)`). Isso é seguro porque a
operação é idempotente: não importa quem venceu a corrida, o resultado
observável é o mesmo (a tarefa está `nao_feito` de qualquer forma).

Isso **não é suficiente** para as cinco funções que creditam pontos, criam
rodízio ou excluem vínculo — perder a corrida ali significa que os dados
usados no cálculo/validação (dificuldade, atraso, versão do rodízio,
existência de tarefas abertas) podem ter mudado, e aceitar cegamente o
estado atual quebraria a invariante (crédito duplicado, rodízio
inconsistente). Para essas, o padrão precisa de **retry de verdade**:

1. Ler o estado atual e validar as pré-condições (mesmas checagens que a
   função SQL já faz hoje: responsável correto, sem crédito duplicado,
   dados não mudaram desde o cálculo, etc.).
2. Calcular a escrita.
3. Tentar o `UPDATE`/`INSERT` condicional.
4. Se zero linhas afetadas (ou falha de unicidade), voltar ao passo 1 com
   os dados frescos, até um limite de tentativas.
5. Esgotado o limite, retornar `409` para o chamador — o mesmo contrato de
   erro que as funções SQL já usam hoje (`ERRCODE = 'PT409'`), então o
   comportamento observado pelo frontend não muda.

Na implementação real de `registrar_conclusao_tarefa` apareceu uma terceira
variante, nem "aceita a falha" nem "retry de verdade": o `UPDATE` que marca
a tarefa como `finalizado` (`_finalizar_estado_tarefa`) **não tenta de
novo** — mas também não trata a falha como sucesso. Zero linhas afetadas ali
vira `409` direto. Faz sentido porque, numa retomada solo sem concorrência,
a tarefa continua no estado que eu deixei e o `UPDATE` teria sucesso de
primeira; só se chega em zero linhas quando existe uma corrida de verdade
entre duas chamadas — e nesse caso `409` para uma delas é o comportamento
correto, igual a função SQL original sempre teve.

### Lição aprendida: o corredor mais rápido pode não ser o dono da operação

O primeiro desenho de `_creditar_e_finalizar` usava `ja_creditado` (quem
venceu o `INSERT` em `score_event`) para decidir o que fazer quando o
`UPDATE` da tarefa não achava linha — supondo que "se o insert foi meu,
ninguém mais pôde ter finalizado antes de mim". Essa suposição é falsa:
quem **perde** a corrida do `INSERT` (`ja_creditado = True`) tem **menos
passos pela frente**, porque pula o crédito em `pertencer` — então pode
chegar no `UPDATE` da tarefa antes de quem realmente tem o crédito. Isso
fazia o dono legítimo do crédito (que só chega depois, com o `UPDATE` já
"perdido") cair num `500` tratado como "nunca deveria acontecer".

Achado pelo teste de integração real `test_conclusoes_simultaneas_creditam_uma_unica_vez`
(duas requisições HTTP concorrentes de verdade) — nenhum teste unitário com
mock pegou isso, porque a ordem de chegada entre dois branches diferentes do
mesmo método não é algo que um mock sequencial reproduz. A correção: não
usar "quem venceu o insert" pra decidir o resultado do `UPDATE` da tarefa —
o único sinal confiável é o próprio resultado desse `UPDATE`.

## Limitação: sem transação real entre escritas múltiplas

`registrar_conclusao_tarefa` faz várias escritas relacionadas (marcar
tarefa, inserir `score_event`, incrementar `pertencer.score`) dentro de uma
única transação Postgres. Sem `FOR UPDATE` nem transação entre chamadas do
PostgREST, cada escrita é atômica sozinha, mas a sequência toda não é.
A estratégia pra não deixar o sistema inconsistente se cair no meio do
caminho:

- Ordenar as escritas de forma que uma falha no meio deixe o sistema em um
  estado **recuperável por retry**, não inconsistente — a escrita que torna
  a operação visível como concluída (`tarefa.estado_atual = 'finalizado'`)
  deve ser a última, depois que o crédito já foi gravado.
- Usar a unicidade já existente (`score_event` como guarda contra crédito
  duplicado) como proteção extra: antes de repetir uma escrita, o backend
  reconfere se ela já aconteceu, em vez de assumir que o retry é sempre
  seguro repetir do zero.

## Ordem de migração recomendada

Uma função por vez, começando por `registrar_conclusao_tarefa` — é o
caminho mais crítico (já em produção, testado) e valida o padrão de CAS +
retry antes de replicar pras outras quatro (`criar_rotatividade`,
`registrar_ocorrencia_rotativa`, `excluir_tarefa_sem_credito`,
`excluir_vinculo_sem_credito`), que ainda não têm uso real no backend.

**Status:** `registrar_conclusao_tarefa` concluída (2026-09-28). As outras
quatro continuam no banco (`docs/migrations/19.sql`, `21.sql`, `22.sql`),
sem uso real no backend ainda — próximas da fila, uma de cada vez, seguindo
o mesmo padrão validado aqui (inclusive a lição da corrida acima).

## Pendências e riscos

- `criar_rotatividade`, `registrar_ocorrencia_rotativa`,
  `excluir_tarefa_sem_credito` e `excluir_vinculo_sem_credito` continuam
  como funções no banco — migração pendente, uma por vez.
- `score_event.tipo` (`credito`/`reversal`) e o índice único parcial por
  tipo já foram aplicados no Supabase real via `docs/migrations/24.sql` —
  a pendência de schema que este documento citava antes já está resolvida.
- Decisão tomada em 2026-09-28: `registrar_conclusao_tarefa` grava um único
  evento em `score_event` com o valor já descontado (mesmo comportamento da
  função SQL que substituiu), não dois eventos separados (`credito` +
  `late_penalty`). Um teste órfão que esperava o split (herdado de uma
  `25.sql` nunca aplicada) foi atualizado para refletir isso. Se o time
  quiser essa granularidade de volta — por exemplo pro ECH-158 (histórico
  de eventos) — é uma decisão de produto a ser tomada separadamente, não um
  efeito colateral desta migração.
- `_creditar_pertencer` continua vulnerável, em teoria, a esgotar as 5
  tentativas de CAS sob concorrência muito alta — não observado nos testes
  reais até agora, aceitável dado o volume baixo esperado do projeto.
- Sem o lock de linha do Postgres, um volume real de conflitos concorrentes
  mais alto que o esperado pode exigir algo mais robusto que retry simples
  (fila, lock distribuído) — aceitável por ora dado o volume baixo esperado
  do projeto.
