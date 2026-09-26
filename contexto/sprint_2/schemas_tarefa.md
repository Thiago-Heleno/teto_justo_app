# Contrato de tarefas e tolerância de atraso — Sprint 2

## Objetivo

Atualizar `TarefaCriar`, `TarefaAtualizar` e `TarefaResposta` para que a API
calcule a pontuação e o vencimento, distinguindo prazo de execução e tolerância
de atraso. Esta entrega substitui as regras anteriores de pontuação livre e
perda total no último dia permitido de atraso.

## Contrato

- `peso`: dificuldade inteira de 1 a 3, mantendo o nome utilizado pelo frontend.
  Os pontos-base são, respectivamente, 10, 25 e 50.
- `prazo_dias`: inteiro de 1 a 5, conforme o formulário.
- `atraso_maximo`: inteiro positivo, independente do prazo de execução.
- `estrategia_penalidade`: somente `proporcional`; não existem estratégias
  alternativas nem taxas livres.
- `referencia_inicio`: `criacao` para tarefa unitária ou `ocorrencia` para uma
  execução de tarefa recorrente.
- Na tarefa unitária, o servidor registra `data_inicio` no momento da criação.
  Na ocorrência, o administrador informa `data_inicio` e `proxima_ocorrencia`,
  com fuso horário. Datas são normalizadas para UTC. O início não pode ser passado.
- O servidor calcula `data_fim = data_inicio + prazo_dias`, em períodos de 24 horas.
  Nas recorrentes, `data_fim + atraso_maximo` deve ser estritamente anterior
  à próxima ocorrência, tanto na criação como na edição.
- A criação exige exatamente um responsável, nasce `pendente` e deriva
  `fk_usuario_id` da sessão do administrador. Participantes de rodízio não são
  responsáveis simultâneos pela mesma ocorrência.
- `pontuacao`, `data_fim` e `fk_usuario_id` deixam de ser entradas aceitas.
  Enviá-los gera 422. Na resposta, `pontuacao` é a base calculada pela dificuldade;
  o crédito efetivo com penalidade continua registrado em `score_event`.
- A resposta também informa estratégia, referência de início, início, duração
  e próxima ocorrência. Duração e início podem ser nulos em registros legados.

Exemplo de criação unitária (IDs substituídos por UUIDs reais):

```json
{
  "nome": "Lavar louça",
  "peso": 3,
  "prazo_dias": 3,
  "atraso_maximo": 1,
  "fk_casa_id": "UUID_DA_CASA",
  "usuarios_atribuidos": ["UUID_DO_RESPONSAVEL"]
}
```

O PATCH permite editar nome, descrição, dificuldade, duração, tolerância,
responsável e estado, respeitando a autorização existente. Alterar a duração
preserva a referência original de início; não reinicia o relógio. O vencimento
resultante deve estar no futuro. A referência e as datas de início/próxima
ocorrência não são editáveis por esse contrato.

## Penalidade e permissões

Para tolerância de N dias, o divisor é N + 1:

```text
dias_atraso = teto(max(0, conclusão - vencimento) / 24 horas)
pontos = arredondar(pontos_base × max(0, N + 1 - dias_atraso) / (N + 1))
```

No vencimento exato não há desconto. Atraso positivo até 24 horas conta como
um dia; acima de 24 até 48 horas, dois. Apenas o resultado final é arredondado,
com meio ponto para cima. Para 50 pontos e N = 2, os resultados são 50 no prazo,
33 no primeiro dia, 17 no segundo e zero após ultrapassar a tolerância.

A penalidade reduz o crédito da própria tarefa ao concluí-la. Não existe
subtração diária do saldo de moradores. Após ultrapassar a tolerância, a
consulta marca a tarefa `nao_feito`, e a conclusão é rejeitada.

O administrador configura a tarefa, mas também não pode enviar pontos livres.
Somente o responsável finaliza, em um PATCH contendo apenas
`estado_atual: finalizado`; regras não podem mudar na mesma requisição.
Ocorrências futuras não podem ser finalizadas. Tarefas encerradas não podem
ser reabertas ou editadas. Validação de novos responsáveis antecede qualquer
atualização dos dados, evitando alteração parcial em caso de vínculo inválido.

## Arquivos e banco

- `src/backend/schemas/tarefa.py`: contrato e validações.
- `src/backend/services/tarefa.py`: datas calculadas, dados da sessão,
  pontuação-base, edição, autorização e cálculo na conclusão. A consulta de atraso
  usa atualização condicional para não sobrescrever uma conclusão concorrente.
- `src/backend/services/score.py`: cálculo puro com `atraso_maximo + 1`;
  `prazo_dias` deixa de ser argumento do cálculo da penalidade.
- `docs/migrations/14.sql`: alinha a coluna `pontuacao` à dificuldade, adiciona
  duração/referência/próxima ocorrência e valida os prazos. Remove o trigger e
  a função de cálculo, e adiciona a operação transacional que persiste os pontos
  calculados no backend, a conclusão e o saldo. Restringe essa operação ao papel
  `service_role`.
- Testes de schemas, serviço e cálculo; testes com Supabase adaptados e
  ampliados para conferir saldo, evento e bloqueio de conclusão repetida.
- `.github/workflows/backend-pytest.yml`: inclui os testes novos de contrato.

A migration `14.sql` deve ser aplicada após `13.sql` antes de usar este backend
com o banco real. Ela atualiza os pontos-base das tarefas existentes e reutiliza
`criado_em` quando falta `data_inicio`, preservando saldos e eventos históricos.
Não deduz duração para registros antigos: `prazo_dias` permanece nulo. Também
desativa o cálculo SQL; atualizar apenas o estado diretamente no banco deixa
de gerar qualquer crédito.

O backend utiliza uma chave do Supabase com papel `service_role` para a
persistência da conclusão. O frontend continua usando apenas o token do Teto
Justo; a chave privilegiada nunca deve ser colocada no aplicativo.

A conclusão chama `ServicoScore` uma única vez com o instante do backend e
envia o resultado calculado à operação de persistência. Estado, evento e saldo
são gravados juntos, com bloqueio e conferência das regras/responsável lidos
pelo backend. Conclusões repetidas ou dados alterados no intervalo retornam
409. Falhas de infraestrutura não são mascaradas como conflito nem tratadas
com escritas separadas que possam duplicar ou perder créditos.

## Validação e limites

- 188 testes unitários passaram, incluindo contrato HTTP com aplicação de teste
  e serviços com banco simulado. Não são testes de integração com Supabase.
- Ruff dos arquivos Python alterados e `git diff --check`: aprovados.
- Migration e testes de integração real não executados; acesso ao Supabase foi
  adiado pelo usuário.
- O frontend continua como prévia de criação: ainda falta incluir a tolerância
  no formulário e enviar os dados à API.
- A referência de ocorrência está preparada; geração automática de repetições,
  calendário e rodízio de participantes continuam fora desta entrega.
- Tarefas legadas com múltiplos responsáveis não podem ser concluídas pelo
  cálculo que exige um único responsável. Os vínculos antigos são preservados.
- O responsável precisa ter vínculo em `pertencer` para receber o saldo; ausência
  desse vínculo retorna 409 e não grava conclusão nem evento.
- Testes de integração preparados cobrem crédito, ausência do trigger, reversão
  da gravação quando falta vínculo e duas conclusões simultâneas. Eles ainda
  dependem do Supabase de testes com a migration 14 aplicada.
