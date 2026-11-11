# Administrador da casa e dono da tarefa

## Objetivo e investigação

Distinguir o administrador da casa do responsável (dono) pela tarefa no backend.
Foram encontrados parâmetros, mensagens e testes que chamavam o administrador
da casa de proprietário ou dono. Nas verificações revisadas, as permissões já
distinguiam a administração da casa dos responsáveis atribuídos à tarefa.

## Alterações e decisões

- `src/backend/services/autorizacao.py`, `casa.py` e `convite_casa.py`: parâmetros
  e variáveis passam a identificar o administrador da casa explicitamente.
- `src/backend/services/casa.py`, `pertencer.py` e `usuario.py`: mensagens de
  vínculo, saída da casa e exclusão da conta usam administrador.
- `src/backend/schemas/casa.py`: a descrição de `fk_usuario_id` identifica o
  administrador da casa.
- `src/backend/schemas/tarefa.py`: as descrições esclarecem que
  `usuarios_atribuidos` contém os responsáveis (donos) pela tarefa, enquanto
  `fk_usuario_id` identifica seu criador. Ser criador não concede, por si só,
  permissão de responsável.
- Testes do backend usam administrador nos nomes e cenários correspondentes.
  Os testes de conclusão por atualização e pelo método de conclusão foram
  ampliados para rejeitar também o criador quando não está atribuído à tarefa.
- Preservados os campos e formatos de requisição/resposta, os códigos HTTP e as
  regras existentes: administração da casa para criação, edição e exclusão;
  responsabilidade atribuída para conclusão; administrador ou responsável para
  reabertura, sujeita às validações do ciclo de vida.
- Não houve migração nem alteração no banco ou no frontend.

## Validações executadas

A partir de `src/backend`, com `SUPABASE_URL` e `SUPABASE_KEY` configuradas para
testes locais, sem Supabase real:

- `../../.venv/Scripts/python.exe -u -B -m pytest -q -p no:cacheprovider tests --ignore-glob=*_integracao.py`:
  **726 testes passaram**, com dois avisos de depreciação do TestClient e AnyIO.
- `ruff check . --no-cache`: **sem erros**.
- A execução inicial no sandbox travou na criação de sockets locais do asyncio
  no Windows; a suíte completa passou fora dessa restrição. Antes disso,
  **225 testes unitários de serviços passaram** no sandbox.

## Limitações

Testes de integração com Supabase real não foram executados. O Bandit não pôde
ser executado porque o comando não está instalado no ambiente.
