# Fotos de perfil e da casa

## Implementação

- Em **Meu perfil**, o usuário escolhe uma imagem, vê a prévia e salva. Em **Gerenciar casa → Editar casa**, o administrador usa o mesmo fluxo. Cancelar o seletor preserva a foto anterior.
- O componente `Avatar` também exibe a casa na seleção e no gerenciamento. Quando a imagem falta ou falha, ele mostra as iniciais. A foto ampliada nos detalhes acompanha a alteração depois de salvar.
- Em `src/frontend/src/utils/`, os seletores nativo e web usam a validação de `foto.ts` para JPEG, PNG, GIF e WebP de até 3 MiB. Os serviços `perfil-api.ts` e `casas-api.ts` enviam a foto em Base64 pelo PATCH quando ela muda.
- No backend, os serviços de usuário e casa usam `src/backend/services/foto.py` para validar o Base64 e converter a imagem para a coluna binária existente. A leitura continua compatível com fotos de perfil antigas gravadas como texto Base64.

- A Home exibe o banner da casa antes de “Dia a dia da casa” e mantém a foto ampliada nos detalhes. A lista de moradores, as tarefas do dia no calendário e o placar passaram a usar o Avatar. A edição de tarefa e o seletor de participantes do rodízio também exibem a foto junto ao nome.
- Em Pontuação, as fotos vêm de uma consulta à lista de moradores da casa do placar. A associação usa o ID de usuário. Uma falha nessa consulta mantém a classificação visível com as iniciais.

- Para remover a foto em **Meu perfil** ou **Editar casa**, o usuário pode conferir a prévia com iniciais e desfazer a remoção antes de salvar. O PATCH envia `{"foto": null}` para apagar a imagem. Omitir o campo preserva a foto existente. A remoção da casa continua restrita ao administrador.

## Validação da implementação

- Após adicionar a remoção, passaram 48 testes unitários do backend, 147 testes do frontend e as verificações ESLint e Ruff dos arquivos da implementação. Os testes de serviço cobrem remoção explícita, preservação de outros dados e edição sem envio da foto. Com os dois formulários simulados, foram verificados remoção, desfazer, cancelamento do seletor, salvamento e descarte de uma imagem recém-selecionada.

- Após essa ampliação, passaram novamente os 145 testes das três suítes do frontend e o ESLint dos seis arquivos de tela e componentes alterados. Uma simulação dos componentes verificou o banner com foto, sem foto e com falha, tarefas com múltiplos responsáveis ou sem responsável e o placar com sucesso e falha na consulta das fotos.

- Passaram 145 testes do frontend nas suítes de tarefas, casas e gerenciamento, e 46 testes unitários do backend para usuário, casa e leitura das fotos. ESLint e Ruff passaram nos arquivos de código alterados.
- Com os seletores web e nativo simulados, passaram os oito casos de leitura, cancelamento, formato inválido e tamanho excedido.
- Ficou pendente testar o fluxo visual em navegador e aparelho. A checagem completa de TypeScript foi bloqueada pela ausência local de Firebase e `lucide-react-native`. A suíte de rotas da casa foi bloqueada pela ausência de `firebase_admin`.
