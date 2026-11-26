# Backend do gráfico de desempenho — Sprint 5

## Objetivo

Fornecer séries de pontuação para comparar os moradores ativos da casa nas
janelas de semana, mês e semestre, recalculadas a cada consulta.

## Contrato e períodos

`GET /casas/{id_casa}/desempenho?periodo=semanal`

Exige a sessão já usada pelas rotas da casa. Moradores ativos e o dono da casa
podem consultar; sem sessão retorna `401`, sem acesso `403` e casa inexistente
`404`. Período inválido retorna `422`.

As três janelas solicitadas foram mantidas. Seguem o calendário no fuso da
casa, em continuidade com o placar existente; não são janelas móveis:

| `periodo` | Início | Fim dos dados |
| --- | --- | --- |
| `semanal` (padrão) | Domingo da semana atual | Instante da consulta |
| `mensal` | Dia 1 do mês atual | Instante da consulta |
| `semestral` | 1º de janeiro ou 1º de julho do semestre atual | Instante da consulta |

A resposta contém:

- `casa_id`, `fuso_horario` e `periodo`.
- `data_inicio`: primeiro dia incluído; `data_fim`: amanhã, primeiro dia
  excluído, ambos no fuso da casa.
- `atualizado_em`: instante de corte em UTC. Eventos posteriores são excluídos,
  inclusive quando pertencem ao dia de hoje.
- `moradores`: lista ordenada por nome, com desempate pelo identificador.
  Cada item traz `usuario_id`, `nome`, `total` e `serie`.
- `serie`: um ponto por dia, do início da janela até hoje, em ordem cronológica.
  Cada ponto traz `data`, `pontos` (movimentação líquida do dia) e `acumulado`
  (soma desde o início da janela). O último acumulado corresponde ao `total`.

Todos os moradores têm o mesmo eixo de datas. Dias sem movimentação têm zero
pontos e preservam o acumulado anterior. Moradores sem eventos têm série
zerada; casa sem moradores ativos retorna lista vazia. O semestre tem no
máximo 184 pontos por morador. Fuso ausente ou inválido usa UTC, como no placar.

## Arquivos e decisões

- `src/backend/services/placar.py`: adiciona `obter_desempenho`, reutilizando a
  configuração da casa, a leitura paginada de vínculos e eventos e a conversão
  de meia-noite local para UTC. Agrupamento e acumulado são calculados em Python.
- `src/backend/schemas/score.py`: define os três períodos e o contrato tipado
  da resposta, também publicado no OpenAPI em `/docs`.
- `src/backend/routers/casa.py`: expõe a rota com a autorização existente e
  `Cache-Control: no-store`.
- `src/backend/tests/test_desempenho_unitario.py`: cobre períodos, fronteiras
  de datas, fuso, horário de verão, paginação, moradores, zeros e recálculo.
- `src/backend/tests/test_consultas_score_router_unitario.py`: cobre o contrato
  HTTP, autorização, validação dos períodos e atualização entre consultas.

O histórico `score_event` é a fonte dos pontos: créditos somam, estornos
subtraem e eventos fora da casa ou de moradores inativos não entram na série.
O acumulado reinicia na janela; não incorpora o saldo anterior de `pertencer`.
Nenhuma tabela, migration, trigger, dependência de produção ou regra de
pontuação foi alterada.

## Atualização e integração com o frontend

Não há cache de resultados: a próxima consulta reflete os créditos e estornos
já persistidos. Uma conclusão atrasada usa o crédito com o desconto calculado
pelo fluxo existente. Marcar uma tarefa como `atrasada` ou `nao_feito` não
movimenta pontos pelas regras atuais, portanto essa mudança isolada mantém
os valores do gráfico. Reabrir uma tarefa gera estorno, refletido no dia dele.

O frontend deve consultar novamente após mudanças nas tarefas, ao trocar o
período e ao retomar a tela. Para acompanhar alterações feitas por outros
moradores enquanto a tela fica aberta, precisa de consultas periódicas ou
outro mecanismo de atualização. Esta entrega fica no backend: não conecta a
tela ao endpoint nem implementa push, WebSocket ou atualização visual automática.

## Validações executadas

TDD: antes da implementação, os 13 casos do serviço falharam pela ausência de
`obter_desempenho`. Antes da rota, a seleção HTTP teve 14 falhas e um caso aprovado
(casa inexistente, que já retornava `404`). Após implementar, a execução abaixo
passou com **191 testes aprovados**, todos com banco em memória ou mocks.

A partir de `src/backend`, com o ambiente virtual ativo e as variáveis de
Supabase apontando para valores fictícios de teste:

```powershell
python -m pytest -q tests/test_consultas_score_router_unitario.py tests/test_desempenho_unitario.py tests/test_servico_placar_unitario.py tests/test_ciclo_vida_tarefa_unitario.py tests/test_servico_penalidade_unitario.py tests/test_reclamacao_unitario.py
```

Houve dois avisos de depreciação das dependências do TestClient (`httpx` e
`BlockingPortal`). Os testes HTTP precisaram executar fora do sandbox local:
a criação do socket do asyncio ficou bloqueada nele. Não houve acesso ao
Supabase real.

A partir da raiz do repositório:

- `python -m ruff check src/backend`: aprovado.
- `python -m ruff check --fix` nos arquivos Python alterados: executado;
  formatação posterior resolveu as linhas longas inicialmente apontadas.
- `python -m ruff format` nos arquivos Python alterados: executado;
  `python -m ruff format --check` nesses cinco arquivos: aprovado.
- `python -m bandit -r src/backend -x src/backend/tests,src/backend/venv`:
  aprovado, sem achados. Bandit instalado apenas no ambiente virtual local.
- `git -c core.whitespace=cr-at-eol diff --check`: aprovado; a opção aceita
  os finais CRLF já presentes nos arquivos do projeto.

## Limitações

Não foram executados testes contra banco real, validação visual ou deploy.
As consultas paginadas reutilizam o padrão existente e não têm snapshot
transacional entre páginas durante gravações simultâneas. Uma nova consulta
recalcula os dados persistidos.

## Integração frontend — Sprint 5

### Comportamento

- Novo bloco Desempenho geral entre o filtro compartilhado e o Placar da casa.
- Semana e Mês consultam a rota `/casas/{id_casa}/desempenho` com o período
  selecionado. O gráfico usa o acumulado diário retornado pelo backend,
  incluindo estornos, dias sem movimentação e moradores com zero pontos.
- Ano e Acumulado continuam disponíveis e exibem barras comparativas com
  os totais do placar, pois a rota de desempenho não disponibiliza séries
  diárias para esses dois períodos. Não é usado o semestre como substituto
  do ano nem é reconstruído histórico a partir do extrato limitado.
  O semestre permanece suportado no cliente da API, mas não foi incluído
  como filtro novo na interface para preservar as quatro opções atuais.
- Os filtros continuam controlando o total do cabeçalho e o placar. As
  movimentações recentes continuam independentes do período.
- A seleção de um morador destaca sua curva ou barra; inicialmente o destaque
  é do usuário atual, quando disponível. A navegação por dias atualiza o
  total do cartão e os pontos de cada morador até o dia selecionado. As
  datas vêm da API, sem conversão para o fuso do dispositivo.
- A escala inclui zero e os valores negativos. O componente usa a largura
  medida do gráfico, o tema Caldera, Avatar, MotionPressable e SVG já presente
  no manifesto do projeto; nenhum pacote novo foi adicionado.
- A série é consultada ao entrar/retomar a aba, trocar o período, usar
  Atualizar ou quando uma reclamação reabre uma tarefa e dispara a atualização
  existente. A solicitação anterior é cancelada; erros da série têm nova
  tentativa própria, sem bloquear o placar. A seleção é reiniciada na troca
  de casa ou de período. Não há polling enquanto a aba permanece aberta.

### Arquivos alterados

- `src/frontend/src/app/(app)/pontuacao.tsx`: filtro único acima do novo bloco,
  integração do componente e atualização da ajuda do placar.
- `src/frontend/src/components/grafico-desempenho.tsx`: visualização, interação
  e estados de consulta.
- `src/frontend/src/utils/grafico-desempenho.ts`: seleção de dia, escalas e
  formatação das datas civis.
- `src/frontend/src/services/tarefas-api.ts`: tipos do contrato e consulta
  autenticada na casa ativa, com cancelamento.
- `src/frontend/scripts/grafico-desempenho.test.mjs`: testes de unidade de
  visualização e cliente HTTP com sessão e fetch simulados.

### Validação executada

A partir de `src/frontend`, com Node 22.16.0:

```bash
node --experimental-strip-types --experimental-test-module-mocks --test scripts/grafico-desempenho.test.mjs scripts/placar.test.mjs
```

- Oito testes aprovados (cinco novos e três existentes). A primeira execução
  sem `--experimental-strip-types` falhou por não reconhecer a extensão TS.
  Com a flag, todos passaram. Houve avisos experimentais do Node e de tipo de
  módulo não declarado.
- Transpilação isolada dos quatro arquivos TS/TSX alterados pelo TypeScript
  global: sem erros sintáticos. Isso não substitui `tsc --noEmit` do projeto.
- `git diff --check` a partir da raiz, com os arquivos novos incluídos:
  aprovado.
- `npm ci --offline --ignore-scripts --no-audit --no-fund`: falhou por
  ausência de `zustand` no cache (`ENOTCACHED`). A consulta ao registro npm
  também falhou por resolução de DNS (`EAI_AGAIN`).

### Limitações

Não foi possível executar ESLint, Prettier, a verificação completa de tipos,
o Expo ou testes visuais web/Android/iOS neste ambiente, nem consultar o
backend real. A implementação usa o contrato da rota existente, sem mudar
backend, banco de dados, regras de pontuação, manifesto ou lockfile. A
atualização automática de eventos de outros moradores enquanto a aba está
aberta não foi implementada; nesses casos use Atualizar ou reabra a aba.
