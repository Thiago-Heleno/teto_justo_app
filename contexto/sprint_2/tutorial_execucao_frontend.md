# Tutorial: visualizar o frontend no navegador e no celular

Referência: configuração do projeto e documentação Expo consultadas em
20/09/2026. O projeto utiliza Expo SDK 57.

## 1. Preparar o projeto no Windows

Abra um terminal PowerShell na raiz do repositório e entre na pasta do frontend:

```powershell
cd src/frontend
node --version
npm.cmd --version
```

Node.js e npm precisam estar instalados. No ambiente conferido, as versões
eram Node `24.21.0` e npm `12.0.2`.

Na primeira execução, ou depois de receber mudanças nas dependências, instale
as versões registradas no projeto:

```powershell
npm.cmd ci
```

Os exemplos usam `npm.cmd` e `npx.cmd` para evitar o bloqueio de scripts
`.ps1` do PowerShell. Não é necessário alterar a política de execução.

Sem configuração da API, a tela **Nova tarefa** usa dados fictícios e não
precisa de backend, Docker ou Supabase. Com as variáveis da API já configuradas,
consulta casa e moradores reais; inicie o backend nesse caso. Tarefas comuns e
configurações de rodízio são gravadas pela API. Para que as ocorrências rotativas
sejam geradas depois, o endpoint de job também precisa estar agendado no
ambiente do backend. Se a consulta falhar, é possível tentar novamente ou
escolher explicitamente os dados de demonstração.

## 2. Abrir no navegador do computador

Na mesma pasta, execute:

```powershell
npm.cmd run web -- --port 8081
```

Mantenha o terminal aberto e acesse
[Nova tarefa](http://localhost:8081/nova-tarefa). Também é possível abrir a
página inicial e clicar em **Criar** na navegação.

Se a porta estiver ocupada, use a prévia que já está rodando ou encerre o
servidor anterior com `Ctrl+C` no terminal correspondente. Para iniciar outra
instância em uma porta diferente:

```powershell
npm.cmd run web -- --port 8082
```

Nesse caso, abra [Nova tarefa na porta 8082](http://localhost:8082/nova-tarefa).
Use sempre a porta informada pelo terminal.

## 3. Abrir no celular com Expo Go

Este é o primeiro caminho a tentar para conferir o formulário no aparelho,
sem compilar um aplicativo próprio.

1. Instale uma versão do **Expo Go compatível com SDK 57**. Consulte o
   [seletor oficial de versões](https://expo.dev/go) se houver incompatibilidade.
2. Conecte computador e celular à mesma rede Wi-Fi.
3. Se o servidor web anterior estiver aberto, encerre-o com `Ctrl+C`.
4. Na pasta do frontend, execute:

```powershell
npx.cmd expo start --go --port 8081
```

5. Leia o QR code mostrado no terminal: no Android, use a opção de leitura
   do Expo Go; no iPhone, use a câmera e abra o link no Expo Go.
6. Quando o aplicativo abrir, toque na aba **Criar**.

O QR code e a conexão pela mesma rede seguem o fluxo descrito em
[Iniciar o desenvolvimento — Expo](https://docs.expo.dev/get-started/start-developing/).
Compatibilidade de SDK deve ser conferida no aparelho; o projeto ainda não
foi homologado em um celular nesta tarefa.

### Conta Expo no iPhone

A orientação atual do Expo para SDK 57 no iPhone exige a mesma conta Expo
no terminal e no Expo Go. Faça o login no computador:

```powershell
npx.cmd expo login
```

Entre com a mesma conta no Expo Go e leia o QR novamente. Essa conta é do
Expo, não um login do Teto Justo. Veja o
[comunicado oficial de setembro de 2026](https://expo.dev/changelog/expo-go-57-login).

### Quando o celular não conecta

Confira a rede Wi-Fi e o acesso do Node.js pela rede privada no firewall.
Redes de faculdade ou de visitantes podem bloquear comunicação entre aparelhos.
Uma alternativa é parar o servidor e iniciar por túnel:

```powershell
npx.cmd expo start --go --tunnel
```

Leia o novo QR code. Esse modo depende da internet, pode solicitar a instalação
do suporte a túnel e tende a ser mais lento que a rede local.
[Orientação do Expo sobre túnel](https://docs.expo.dev/get-started/start-developing/).

Não digite `localhost:8081` no navegador do celular esperando acessar o
computador: no celular, `localhost` aponta para o próprio aparelho. O QR do
Expo fornece o endereço adequado para abrir o aplicativo.

## 4. Usar `expo run` para instalar o aplicativo

Sim, é possível. Os comandos completos são `expo run:android` e
`expo run:ios`; eles compilam e instalam uma versão de depuração.

### Android conectado ao Windows

Prepare Android Studio, Android SDK e Java conforme o
[guia oficial de ambiente Android](https://docs.expo.dev/get-started/set-up-your-environment/).
Ative as opções de desenvolvedor e a depuração USB no celular, conecte-o por
USB e autorize o computador na tela do aparelho.

Pare o servidor anterior e, na pasta do frontend, execute:

```powershell
npm.cmd run android -- --device
```

Esse script do projeto equivale a:

```powershell
npx.cmd expo run:android --device
```

Escolha o aparelho quando solicitado. A primeira compilação pode baixar
ferramentas e demorar. O comando também pode gerar a pasta nativa `android/`
e ajustar a configuração do aplicativo; revise as alterações antes de commit.
Depois da instalação, abra **Nova tarefa**.

### iPhone

`expo run:ios` precisa de **macOS e Xcode** para compilação local. Em um Mac,
com o iPhone preparado para desenvolvimento e a assinatura configurada, use
na pasta do frontend:

```sh
npx expo run:ios --device
```

No Windows, use Expo Go no iPhone para este primeiro teste. Uma compilação
iOS em nuvem é outra opção, mas exige configuração própria e não faz parte
deste tutorial. Referência dos comandos e pré-requisitos:
[Compilação local — Expo](https://docs.expo.dev/guides/local-app-development/).

## 5. Visualizar mudanças durante o desenvolvimento

Com o servidor ativo, salve o arquivo alterado. O Fast Refresh normalmente
atualiza a tela. Para o formulário, o arquivo principal é
`src/frontend/src/app/nova-tarefa.tsx`; as opções de peso ficam em
`src/frontend/src/constants/tarefa.ts`.

Se a mudança não aparecer, pressione `r` no terminal do Expo ou recarregue
a página. Se necessário, pare o servidor e limpe o cache de desenvolvimento:

```powershell
npx.cmd expo start --go --clear
```

Para a versão web, use:

```powershell
npm.cmd run web -- --clear
```

Após instalar uma versão nativa com `run:android` ou `run:ios`, alterações
apenas em TypeScript normalmente precisam somente do servidor:

```powershell
npm.cmd start
```

Abra o aplicativo instalado. Uma nova compilação é necessária quando mudam
dependências nativas ou configurações que afetam o aplicativo nativo.
[Fluxo após a primeira compilação](https://docs.expo.dev/guides/local-app-development/).

Use **Criar outra tarefa** para limpar a demonstração entre verificações.
Preencha nome, peso de 1 a 3 e prazo de 1 a 5 dias. A descrição é opcional.
Para tarefa **Comum**, selecione um responsável. Para **Rotativa**, selecione
pelo menos dois moradores, ajuste a ordem e selecione um ou mais dias da
semana e o intervalo de 1 a 4 semanas. A opção inicial é 1 semana; 4 semanas
são 28 dias, aproximadamente um mês. Use **Conferir tarefa** para abrir o resumo.
Com API configurada, essa ação grava a configuração; sem API, mostra uma
prévia local. A geração posterior depende do job agendado no backend.

Para encerrar o servidor, pressione `Ctrl+C`.

## Validação original e limites deste tutorial

Scripts conferidos em `package.json`, SDK em `app.json`/dependências e opção
`--device` conferida com a ajuda da CLI instalada (`57.0.25`). Orientações de
celular confrontadas com a documentação oficial. Nesta sessão foram alterados
somente documentos: não foi realizada instalação, compilação ou execução em
aparelhos. Os testes anteriores da tela estão em
[frontend_tarefas.md](frontend_tarefas.md).
