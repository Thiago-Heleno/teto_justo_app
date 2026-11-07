# Fotos de perfil e da casa

## Implementação

- Em **Meu perfil**, o usuário escolhe uma imagem, vê a prévia e salva. Em **Gerenciar casa → Editar casa**, o administrador usa o mesmo fluxo. Cancelar o seletor preserva a foto anterior.
- O componente `Avatar` também exibe a casa na seleção e no gerenciamento. Quando a imagem falta ou falha, ele mostra as iniciais. A foto ampliada nos detalhes acompanha a alteração depois de salvar.
- Em `src/frontend/src/utils/`, os seletores nativo e web usam a validação de `foto.ts` para JPEG, PNG, GIF e WebP de até 3 MiB. Os serviços `perfil-api.ts` e `casas-api.ts` enviam a foto em Base64 pelo PATCH quando ela muda.
- No backend, os serviços de usuário e casa usam `src/backend/services/foto.py` para validar o Base64 e converter a imagem para a coluna binária existente. A leitura continua compatível com fotos de perfil antigas gravadas como texto Base64.

## Validação da implementação

- Passaram 145 testes do frontend nas suítes de tarefas, casas e gerenciamento, e 46 testes unitários do backend para usuário, casa e leitura das fotos. ESLint e Ruff passaram nos arquivos de código alterados.
- Com os seletores web e nativo simulados, passaram os oito casos de leitura, cancelamento, formato inválido e tamanho excedido.
- Ficou pendente testar o fluxo visual em navegador e aparelho. A checagem completa de TypeScript foi bloqueada pela ausência local de Firebase e `lucide-react-native`. A suíte de rotas da casa foi bloqueada pela ausência de `firebase_admin`.
