# Remoção completa do botão de teste de notificações

Guia da sprint 4, conferido com a implementação em 27/10/2026.
Todos os caminhos abaixo partem da raiz do repositório.

## Objetivo

Remover o botão **Testar notificações**, o formulário, a chamada de API, a
rota de envio manual, os schemas e os testes exclusivos desse recurso.
A remoção deve preservar as notificações reais e seus testes.

Este documento orienta uma remoção futura. Sua criação não remove o botão.
O registro da implementação está em [notificacoes_push.md](notificacoes_push.md).

## 1. Conferir o estado antes de editar

Na raiz do repositório:

```powershell
git status --short
git diff
```

Os arquivos compartilhados também contêm funcionalidades permanentes. Faça
as exclusões por símbolo/trecho, sem restaurar arquivos inteiros de uma versão
antiga. Confira se os três arquivos exclusivos abaixo receberam outras
funcionalidades desde a escrita deste guia antes de apagá-los integralmente.

## 2. Remover a interface e a chamada de API

### `src/frontend/src/components/perfil.tsx`

Remova a importação:

```tsx
import { TestarNotificacoes } from "@/components/testar-notificacoes";
```

Remova a inclusão no JSX:

```tsx
{perfil && <TestarNotificacoes usuarioId={perfil.id} />}
```

Mantenha o botão **Ativar notificações**, o indicador **Notificações ativas**,
a função `ativarPush` e os imports usados por eles.

### `src/frontend/src/services/notificacoes.ts`

Remova integralmente estas duas declarações:

- `export type TipoNotificacaoTeste`;
- `export function enviarNotificacaoTeste(...)`.

A segunda declaração contém a chamada a `/usuarios/eu/notificacoes/teste`.
Não remova `requisitar`: as demais funções continuam usando esse import.

### Arquivo exclusivo da interface

Apague `src/frontend/src/components/testar-notificacoes.tsx` inteiro. Isso
remove `TestarNotificacoes`, `FormularioTesteNotificacao`, a constante `TIPOS`,
os estados, os efeitos, os textos e os estilos exclusivos do formulário.

## 3. Remover a rota e o serviço do backend

### `src/backend/routers/usuario.py`

Remova do import de `schemas.notificacao`:

```python
NotificacaoTesteEntrada,
NotificacaoTesteResposta,
```

Remova esta importação:

```python
from services.notificacao_teste import enviar_notificacao_teste
```

Remova o decorador e toda a função:

```python
@router.post("/eu/notificacoes/teste", response_model=NotificacaoTesteResposta)
def testar_notificacao(
    dados: NotificacaoTesteEntrada,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    return enviar_notificacao_teste(supabase, usuario_atual.id, dados)
```

Mantenha as rotas de cadastro e remoção de dispositivos e os demais imports
usados no arquivo. Não é necessário alterar `main.py`: a rota temporária foi
adicionada ao router de usuários existente.

### `src/backend/schemas/notificacao.py`

Remova integralmente as classes `NotificacaoTesteEntrada` e
`NotificacaoTesteResposta`. Mantenha os schemas `DispositivoPush*`.
Os imports de `UUID`, `Literal`, `BaseModel` e `ConfigDict` continuam sendo
usados pelos schemas permanentes.

### Arquivo exclusivo do serviço

Apague `src/backend/services/notificacao_teste.py` inteiro. Isso também remove
`_TITULOS`, as mensagens de teste e a função `enviar_notificacao_teste`.

## 4. Remover os testes e seus auxiliares exclusivos

### `src/backend/tests/test_notificacao_unitario.py`

Remova somente a função:

```python
test_rota_de_teste_encaminha_somente_usuario_da_sessao
```

Os imports de `testar_notificacao` e `NotificacaoTesteEntrada` estão dentro
dessa função e desaparecem com ela. Mantenha os imports compartilhados,
incluindo `Mock`, `SimpleNamespace` e `uuid4`, usados em outros testes.

Apague também o arquivo exclusivo
`src/backend/tests/test_notificacao_teste_unitario.py` inteiro.

### `src/frontend/scripts/notificacoes.test.mjs`

Remova os dois testes completos:

1. `teste manual envia apenas o tipo e a tarefa à rota do usuário logado`;
2. `teste manual preserva a falha da API para a tela informar o problema`.

Remova também todos estes auxiliares exclusivos:

- A declaração `let falhaTeste;`.
- A linha `falhaTeste = undefined;` dentro de `beforeEach`.
- `enviarNotificacaoTeste` da desestruturação do import dinâmico de
  `../src/services/notificacoes.ts`.
- O bloco abaixo, dentro do mock de `requisitar`:

```javascript
if (caminho === "/usuarios/eu/notificacoes/teste") {
  if (falhaTeste) throw falhaTeste;
  return { aceitos: 1, falhas: 0, invalidos: 0 };
}
```

Mantenha o `return undefined` posterior e o tratamento de `/tarefas/`.
Mantenha o arquivo e sua entrada no script `test:tarefas` do `package.json`:
ele continua testando ativação, remoção do aparelho, navegação e ações reais.

## 5. Conferir o inventário da remoção

| Ação | Caminho relativo à raiz |
| --- | --- |
| Apagar | `src/frontend/src/components/testar-notificacoes.tsx` |
| Apagar | `src/backend/services/notificacao_teste.py` |
| Apagar | `src/backend/tests/test_notificacao_teste_unitario.py` |
| Editar | `src/frontend/src/components/perfil.tsx` |
| Editar | `src/frontend/src/services/notificacoes.ts` |
| Editar | `src/frontend/scripts/notificacoes.test.mjs` |
| Editar | `src/backend/routers/usuario.py` |
| Editar | `src/backend/schemas/notificacao.py` |
| Editar | `src/backend/tests/test_notificacao_unitario.py` |

O recurso não criou migration, tabela, coluna, variável de ambiente,
dependência, script de execução, chave de armazenamento local ou agendamento.
Não há configuração ou dado exclusivo do botão a apagar nesses lugares.

Preserve `ServicoNotificacao.enviar_push`, os jobs, as migrations 29 a 32,
os cadastros de aparelhos e a configuração Firebase/Expo. Preserve também
`abrirTarefaNotificada`, a categoria `tarefa_pendente`, as ações `concluir_tarefa`
e `ver_tarefa` e seus testes. Os tipos `tarefa_atribuida`, `tarefa_vence_hoje` e
`tarefa_atrasada` pertencem às notificações reais e devem continuar existindo.

## 6. Buscar referências que sobraram

Na raiz do repositório, em PowerShell, execute:

```powershell
$pastasCodigo = @('src/backend', 'src/frontend/src', 'src/frontend/scripts')
$padraoTeste = 'TestarNotificacoes|FormularioTesteNotificacao|enviarNotificacaoTeste|TipoNotificacaoTeste|enviar_notificacao_teste|NotificacaoTesteEntrada|NotificacaoTesteResposta|testar_notificacao|notificacao_teste|testar-notificacoes|notificacoes/teste|falhaTeste|test_rota_de_teste_encaminha_somente_usuario_da_sessao|teste manual envia apenas o tipo|teste manual preserva a falha|Testar notificações|Teste de notificações|Fechar teste de notificações|Enviar notificação de teste|Teste: nova tarefa|Teste: tarefa vence hoje|Teste: tarefa atrasada|Aviso de teste'
Get-ChildItem -LiteralPath $pastasCodigo -Recurse -File |
    Where-Object { $_.Extension -in '.py', '.ts', '.tsx', '.js', '.mjs', '.json' } |
    Select-String -Pattern $padraoTeste
```

O resultado esperado é **nenhuma ocorrência**. A busca inclui arquivos ainda
não rastreados pelo Git. A pasta `contexto` está fora dessa busca porque contém
o registro histórico e este guia.

Confirme também, ainda na raiz, que os arquivos exclusivos não existem:

```powershell
@(
    'src/frontend/src/components/testar-notificacoes.tsx'
    'src/backend/services/notificacao_teste.py'
    'src/backend/tests/test_notificacao_teste_unitario.py'
) | ForEach-Object {
    [pscustomobject]@{ Arquivo = $_; Existe = (Test-Path -LiteralPath $_) }
}
```

As três linhas devem mostrar `Existe = False`.

## 7. Validar o código restante

Use o ambiente Python com `src/backend/requirements-dev.txt` instalado e as
dependências do frontend disponíveis. O runner JavaScript usado na validação
da implementação foi o Node 24.

A partir de `src/frontend`:

```powershell
node --experimental-test-module-mocks --test scripts/notificacoes.test.mjs scripts/autenticacao-api.test.mjs
node node_modules/typescript/bin/tsc --noEmit
node node_modules/eslint/bin/eslint.js src/components/perfil.tsx src/services/notificacoes.ts
```

A partir de `src/backend`:

```powershell
python -m pytest tests/test_notificacao_unitario.py -q
python -m ruff check routers/usuario.py schemas/notificacao.py tests/test_notificacao_unitario.py
```

Na raiz do repositório:

```powershell
git diff --check
git diff --stat
git diff
git status --short
```

Na revisão de 27/10, o Python local estava sem `tzdata` e três testes de horário
falharam por esse motivo. Uma execução anterior dos testes HTTP também havia
travado. Esses são limites do ambiente registrado, não justificativas para
apagar testes permanentes: prepare o ambiente e registre qualquer verificação
que continuar bloqueada. Os comandos desta seção são instruções para a remoção
futura; não foram executados como validação de uma remoção nesta documentação.

## 8. Validar a retirada na aplicação publicada

- Abra o perfil e confirme que não há botão, formulário ou textos de teste,
  mas que a ativação de notificações continua disponível no aplicativo nativo.
- Confira que `POST /usuarios/eu/notificacoes/teste` não aparece no OpenAPI
  do backend atualizado. Uma chamada a esse caminho não pode executar envio;
  após a remoção da rota, o esperado é 404.
- Valide uma notificação real em uma conta de teste: recebimento, abertura da
  tarefa e ações continuam funcionando. Isso é uma verificação futura, não
  um envio já realizado por este guia.
- Publique o backend e a versão web atualizados e distribua um novo build do
  aplicativo. Remover a rota encerra o envio manual também para versões antigas;
  o botão só desaparece dos aparelhos quando eles recebem a versão atualizada.
- Gere a distribuição a partir de uma árvore limpa de build, para não reutilizar
  bundles antigos. Não é necessário apagar credenciais ou dados dos usuários.

## 9. Atualizar os registros

Em `contexto/sprint_4/notificacoes_push.md`, registre a data da retirada e as
validações realmente realizadas. Identifique a seção de implementação como
histórica para não sugerir que o botão ainda está disponível.

Este guia e o registro histórico não são código executável. Se a decisão for
eliminar também a documentação do recurso, remova a seção específica do botão
em `notificacoes_push.md`, o link para este guia e este arquivo, por último.
Preserve a documentação das notificações permanentes. Não é necessário
reescrever o histórico do Git para retirar o recurso do código atual.

## Critério de conclusão

A retirada está completa quando os três arquivos exclusivos foram apagados,
os seis arquivos compartilhados foram limpos, a busca não encontra referências
no código/testes, a rota não existe, a interface atualizada não mostra o botão
e as notificações permanentes continuam passando nas verificações aplicáveis.

## Verificação deste guia

Os caminhos, símbolos, testes e auxiliares foram conferidos no código atual.
Nenhum arquivo de implementação foi removido ou alterado na criação do guia.
