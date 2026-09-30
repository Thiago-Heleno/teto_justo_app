# Concorrência sem funções no banco: compare-and-swap com retry

> **Atualização de 30/09/2026:** a conclusão de tarefas voltou a usar a RPC
> transacional `registrar_conclusao_tarefa` em `docs/migrations/26.sql`.
> A sequência de escritas em Python descrita abaixo fica como histórico da
> decisão anterior: ela permitia gravações parciais se a conexão caísse entre
> o evento, o saldo e a finalização. As demais operações descritas aqui não
> foram alteradas. A migration 26 ainda precisa ser aplicada aos bancos de
> teste e produção antes de usar o backend atualizado.

Este documento registra a decisão de arquitetura para a migração das funções
PL/pgSQL (`registrar_conclusao_tarefa`, `criar_rotatividade`,
`registrar_ocorrencia_rotativa`, `excluir_tarefa_sem_credito`,
`excluir_vinculo_sem_credito`) para o backend Python, e o padrão de
concorrência que substitui `SELECT ... FOR UPDATE` nelas.

**Status em 2026-09-29:** `registrar_conclusao_tarefa`, `excluir_tarefa_sem_credito`
e `excluir_vinculo_sem_credito` migradas (3 de 5) — ver `_creditar_e_finalizar`/
`_creditar_pertencer`/`_finalizar_estado_tarefa` e `excluir_tarefa` em
[services/tarefa.py](../../src/backend/services/tarefa.py), e `deletar_pertencer`
em [services/pertencer.py](../../src/backend/services/pertencer.py). A
implementação da primeira revelou um caso de corrida que a decisão original
não previu — ver "Lição aprendida" abaixo. As duas últimas, mais simples,
não precisaram de CAS nem retry — ver a seção dedicada a elas mais abaixo.
`criar_rotatividade` e `registrar_ocorrencia_rotativa` continuam no banco,
sem migração prevista até o rodízio de tarefas ser de fato implementado no
backend (hoje nenhuma das duas tem chamador).

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

**Status:** `registrar_conclusao_tarefa`, `excluir_tarefa_sem_credito` e
`excluir_vinculo_sem_credito` concluídas (2026-09-28/29). Só sobram
`criar_rotatividade` e `registrar_ocorrencia_rotativa` no banco
(`docs/migrations/19.sql`, `21.sql`) — sem chamador no backend hoje, então
não há mais nada pra "migrar" de verdade até o rodízio de tarefas virar
feature de verdade (é aí que essas duas ganham uso real e sentido de
migrar).

## Migração de `excluir_tarefa_sem_credito` e `excluir_vinculo_sem_credito` (2026-09-29)

Essas duas são mais simples que `registrar_conclusao_tarefa` porque nenhuma
credita ou acumula valor — são exclusões condicionais, sem disputa de
"quem chega primeiro". Nenhuma precisou de CAS nem de retry.

**`excluir_tarefa_sem_credito` → `ServicoTarefa.excluir_tarefa`**

A proteção contra apagar uma tarefa com crédito já vem do próprio schema:
`score_event.fk_tarefa_id` é `ON DELETE RESTRICT` para `tarefa`. O Postgres
recusa sozinho um `DELETE` que deixaria um `score_event` órfão (erro
`23503`) — não precisa de leitura prévia + CAS pra essa parte, só tentar o
`DELETE` e capturar o `23503`, como o backend já fazia pro `PT409` da
função SQL.

Achado bônus: a função SQL fazia um `DELETE FROM atribuida` manual antes de
apagar a tarefa, mas `Atribuida.fk_Tarefa_id` já é `ON DELETE CASCADE`
(`docs/migrations/05.sql:19-23`) — esse delete manual sempre foi redundante.
A versão em Python usa só um `DELETE` na tabela `tarefa`.

Achado de paridade: a checagem em Python de "não pode excluir" só olhava
`estado_atual == 'finalizado'`; a função SQL também bloqueava tarefas de
rodízio (`rotatividade_id IS NOT NULL`), condição que nunca tinha sido
portada. Adicionada agora, mesmo inalcançável hoje (rodízio não está ligado
ao backend), pra não regredir quando/se for.

**`excluir_vinculo_sem_credito` → `ServicoPertencer.deletar_pertencer`**

Diferente da anterior, aqui **não existe FK nenhuma** protegendo as
checagens de negócio (histórico de pontos em `score_event`, tarefas
abertas em `atribuida`/`tarefa`) — nenhuma das duas referencia `pertencer`
diretamente. A checagem em Python é a única linha de defesa, sem rede de
segurança do banco por trás; aceitável porque o risco é uma janela de
corrida estreita (outra requisição inserindo um evento/tarefa no exato
meio da checagem), do mesmo nível de risco já aceito em outros pontos
deste documento.

A busca de "tarefas abertas" usa duas consultas separadas (`atribuida` →
lista de `fk_tarefa_id`, depois `tarefa` filtrada por esses IDs) em vez de
um JOIN — o projeto não usa embed/join do PostgREST em nenhum lugar ainda,
então manteve o padrão já estabelecido no resto do código.

## Pendências e riscos

- `criar_rotatividade` e `registrar_ocorrencia_rotativa` continuam como
  funções no banco — sem chamador no backend, então sem migração pendente
  de verdade até o rodízio de tarefas ser implementado.
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
