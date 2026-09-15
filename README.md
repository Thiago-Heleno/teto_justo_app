# Guia de Padronização de Código (Linters) - Teto Justo App

## 1. Backend (Python)

No backend, vamos usar o **Ruff**, a ferramenta mais usada para linting e formatação em Python.

### Passo a Passo de Configuração

**1. Abra o terminal na pasta do backend:**
Navegue até a pasta `src/backend`.

**2. Ative o Ambiente Virtual (venv):** venv é uma bolha do projeto. Rode os comandos do linters nele para que o windows reconheça tudo corretamente

```powershell
# Ativa o ambiente no Windows (PowerShell)
.\venv\Scripts\activate
```

*(Nota: O terminal deve mostrar `(venv)` no início da linha).*

> **Aviso no PowerShell:** Se der erro ao tentar ativar, rode `Set-ExecutionPolicy Unrestricted -Scope CurrentUser` e tente de novo.

**3. Instale o Ruff:**

```bash
#Só na primeira vez que for usar
pip install ruff
```

**4. Confira a configuração:**
Na raiz do backend, verifique que existe um arquivo chamado `pyproject.toml` com as regras da equipe:

```toml
[tool.ruff]
#tamanho da linha
line-length = 100

[tool.ruff.lint]
# Habilita as regras do Pyflakes (F) e pycodestyle (E, W)
select = ["E", "F", "W"]
```

### Como usar

Sempre com o `(venv)` ativo, rode os comandos abaixo na pasta do backend:

* **Para ver os erros do código:** `ruff check .`

* **Para corrigir os erros automaticamente (o que for possível):** `ruff check --fix .`

* **Para formatar o visual do código (espaços, aspas):** `ruff format .`

## Guia de Segurança com SAST (Backend Python) - Teto Justo App

### Passo a Passo de Instalação ferramenta Bandit

**1. Abra o terminal na pasta do backend:**
Navegue até a pasta `src/backend`.

**2. Ative o Ambiente Virtual (venv):**

```powershell
# Ativa o ambiente
.\venv\Scripts\activate
```

**3. Instale o Bandit:**

```bash
pip install bandit
```

## 4. Como Usar

Com o ambiente virtual ativo, rode o comando abaixo na raiz da pasta do backend para iniciar a varredura completa:

```bash
bandit -r . -x ./venv
```

**Explicando os parâmetros do comando:**

* `-r .` : O "-r" significa recursivo e o "." indica a pasta atual.
* `-x ./venv` : Essa parte diz ao Bandit para excluir (ignorar) a pasta `venv`. Se não fizermos isso, ele vai tentar analisar o código de todas as bibliotecas que instalamos.

## 5. Interpretando os Resultados

O Bandit vai imprimir um relatório no terminal. Ele classifica o que encontrou usando dois critérios:

* **Severity (Gravidade):** *Low* (Baixa), *Medium* (Média) ou *High* (Alta).
  * *Atenção especial:* Tudo que for **High** ou **Medium** precisa ser corrigido antes do código ir para produção.
* **Confidence (Certeza):** O nível de certeza que a ferramenta tem de que aquilo é realmente um problema de segurança.

## Integração no Fluxo de Trabalho (Boas Práticas)

A análise estática deve sempre ser feita ao terminar alguma parte do código.

1. Terminou de programar uma funcionalidade?
2. Rode o Linter: `ruff check .`
3. Rode o SAST: `bandit -r . -x ./venv`
4. Se ambos passarem sem erros graves, faça o seu `git commit`.
5. Para sair do ambiente virtual (venv) digite deactivate no terminal.
