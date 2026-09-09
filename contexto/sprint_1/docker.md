# Docker — Sprint 1

## O que foi feito
Configuração do ambiente do backend com Docker, para que qualquer pessoa do time suba a API sem precisar instalar Python e dependências manualmente na própria máquina.

## Arquivos adicionados
- `src/backend/Dockerfile` — receita que empacota o backend FastAPI numa imagem Docker.
- `docker-compose.yml` — sobe o serviço `backend` já mapeado na porta `8000`, montando o código local dentro do container e carregando as variáveis de ambiente do `.env`.

## Como funciona
1. O `Dockerfile` usa a imagem `python:3.12-slim`, instala as dependências do `requirements.txt` e roda a API com `uvicorn` na porta `8000`, com `--reload` ativado (recarrega sozinho quando o código muda).
2. O `docker-compose.yml` faz o "elo" entre o container e a máquina do desenvolvedor: monta a pasta `src/backend` como volume, então editar o código local já reflete dentro do container sem precisar rebuildar a imagem.
3. As credenciais sensíveis (chaves do Supabase) ficam no `.env`, que não é commitado (está no `.gitignore`).

## Como rodar
```bash
docker compose up

## para fechar
docker compose down
```
A API fica disponível em `http://localhost:8000`, com healthcheck em `/health`.

## Para falar com o professor
- O time já tem um ambiente de desenvolvimento padronizado e reprodutível (não depende de "na minha máquina funciona").
- Falta (próximos passos): variáveis de ambiente de exemplo (`.env.example`) para facilitar onboarding de quem entra no projeto agora.
