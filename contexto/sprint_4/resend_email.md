# Envio de emails com Resend — Sprint 4

## Objetivo e comportamento

Criar a base para o backend enviar emails (verificação de email, recuperação de
conta e similares). Nenhuma dessas features foi implementada; o serviço apenas
fica disponível para elas.

```python
from services.envio_email import ServicoEmail

ServicoEmail().enviar("pessoa@example.com", "Assunto", "<p>Olá</p>")
```

- `para` aceita um endereço (`str`) ou uma lista de endereços.
- Se `RESEND_API` não estiver definida ou o envio falhar, o serviço levanta
  `HTTPException(503)` com mensagem genérica. Falhas cobertas: erro HTTP do
  Resend (4xx/5xx), timeout (10 s) e erro de rede.
- Quem chama decide se trata a exceção ou a deixa subir, como em `convite_casa.py`.

## Configuração

Variáveis lidas em cada envio (`.env`, documentadas em `.env.example`):

- `RESEND_API`: chave criada no painel do Resend. Obrigatória.
- `RESEND_FROM`: remetente. Opcional; o padrão é `onboarding@resend.dev`, que
  só entrega para o email da conta Resend até um domínio ser verificado no
  painel. Depois disso, basta definir esta variável.

O `docker-compose.yml` já carrega o `.env`; não houve mudança nele.

## Arquivos e decisões

- `src/backend/services/envio_email.py`: classe `ServicoEmail` com `enviar`.
- `src/backend/tests/test_servico_email_unitario.py`: testes unitários.
- `.env.example`: `RESEND_API` e `RESEND_FROM`, sem valores.

Decisões:

- **`httpx` em vez do SDK `resend`:** a chamada é um único
  `POST https://api.resend.com/emails`, e `httpx` já está em
  `src/backend/requirements.txt`. Não houve nova dependência.
- **Mensagem de erro genérica:** o erro original do `httpx` pode conter a chave
  ou o destinatário, então ele só é encadeado (`from erro`) e não vai ao cliente.
- **Variáveis lidas no momento do envio**, seguindo `convite_casa.py`.
- **Chamada síncrona**, como os demais serviços; funciona em rotas `def` e pode
  ser usada com `BackgroundTasks` se o envio não precisar bloquear a resposta.

## Validação executada

Comandos executados a partir de `src/backend`:

- `python -m pytest tests/test_servico_email_unitario.py`: 7 testes aprovados.
  Cobrem chave ausente (sem requisição), payload e cabeçalho com remetente
  padrão, remetente configurado com lista de destinatários, e respostas 401/500,
  timeout e erro de rede virando 503 sem vazar a chave. São testes unitários:
  `httpx.post` é simulado e o Resend não é chamado.
- `python -m pytest tests -k unitario`: 386 testes aprovados, 31 não selecionados
  (integração com banco, não executados).
- `python -m ruff check` nos dois arquivos novos: aprovado.

- Envio real: um único email de teste, com `ServicoEmail().enviar(...)` e as
  variáveis do `.env` local, para o email da conta Resend. O Resend aceitou a
  requisição (HTTP 2xx, sem exceção) e o usuário confirmou o recebimento do email.

Foi usado o Python global da máquina, porque `.venv` e `venv` do backend não
tinham `pytest`.

## Limites

- O envio real foi feito uma única vez, de forma manual; os testes automatizados
  seguem simulando o Resend.
- Sem templates, fila, retry ou envio em lote.
- Enquanto não houver domínio verificado, o remetente padrão só entrega para o
  email da conta Resend.
- O serviço é usado pelo código de verificação do cadastro
  (`verificacao_email.md`) e pela recuperação de senha
  (`recuperacao_senha.md`).
