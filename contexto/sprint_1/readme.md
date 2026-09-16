# README do projeto — Sprint 1

## Objetivo

Documentar o Teto Justo no README principal, incluindo apresentação do
aplicativo, tecnologias, fluxo da arquitetura, protótipo e execução local.

## Alterações

- `README.md` passou a exibir o `icon.png` existente na raiz do repositório.
- Foram adicionadas as seções de descrição do produto, stack tecnológica, link
  do Figma e diagrama Mermaid do fluxo entre React Native, FastAPI e Supabase.
- Foi documentada a finalidade da pasta `contexto/` e a convenção de registrar
  um resumo técnico por sprint ao concluir alterações no repositório.
- Foram documentados os requisitos, as variáveis `SUPABASE_URL` e
  `SUPABASE_KEY`, e os comandos para iniciar frontend e backend localmente ou
  via Docker.
- As instruções anteriores de qualidade foram preservadas e reorganizadas:
  configuração, uso e correção automática com Ruff; análise SAST com Bandit;
  e lint do frontend.
- Foram incluídas orientações para identificar o ambiente virtual ativo,
  resolver bloqueios de ativação no PowerShell e executar as verificações de
  qualidade antes de um commit.

## Validação

- Conferência estática do Markdown e dos comandos com base nos arquivos de
  configuração existentes no repositório.

## Limitações

- A execução local depende de um projeto Supabase configurado com credenciais
  válidas.
- A orientação de PowerShell usa escopo de processo para não alterar a política
  de execução permanente do computador.
