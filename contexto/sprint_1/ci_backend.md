# CI do backend com pytest

## O que foi feito

Adicionado o workflow `.github/workflows/backend-pytest.yml` para executar os testes unitários do backend automaticamente em eventos de `push` e `pull_request`.

## Como funciona

- Usa Ubuntu e Python 3.12, a mesma versão-base do `src/backend/Dockerfile`.
- Instala as dependências de `src/backend/requirements.txt`, além de `pytest` e `httpx` necessários para executar os testes existentes.
- Executa `python -m pytest -q tests` a partir de `src/backend`. O pytest também coleta os testes atuais escritos com `unittest`.
- Concede ao workflow apenas permissão de leitura do conteúdo do repositório.

Nenhum teste novo foi adicionado. O workflow faz integração contínua dos testes; não há etapa de deploy.
