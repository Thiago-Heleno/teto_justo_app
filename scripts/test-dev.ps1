#requires -Version 5.1
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/dev.ps1"

function Assert-DevTest {
    param([bool]$Condition, [string]$Message)
    if (!$Condition) { throw $Message }
}

function Assert-DevFailure {
    param([scriptblock]$Action, [string]$Expected)
    $failed = $false
    try { & $Action } catch {
        $failed = $true
        Assert-DevTest ($_.Exception.Message -like "*$Expected*") 'Mensagem de erro inesperada.'
    }
    Assert-DevTest $failed 'A operacao deveria ter falhado.'
}

$work = Join-Path ([IO.Path]::GetTempPath()) ('teto-justo-dev-test-' + [guid]::NewGuid())
$oldApi = $env:EXPO_PUBLIC_API_URL
try {
    New-Item -ItemType Directory -Path "$work/src/frontend/node_modules/.bin" -Force | Out-Null
    [IO.File]::WriteAllText("$work/src/frontend/package.json", '{}')
    [IO.File]::WriteAllText("$work/src/frontend/package-lock.json", '{}')
    [IO.File]::WriteAllText("$work/src/frontend/node_modules/.bin/expo.cmd", '')
    [IO.File]::WriteAllText("$work/.env.example", "SUPABASE_URL=`nSUPABASE_KEY=`nCASA_CONVITE_SECRET=`n")

    $launcherRoot = Join-Path $work 'checkout com espacos'
    New-Item -ItemType Directory -Path "$launcherRoot/scripts" | Out-Null
    Copy-Item -LiteralPath "$PSScriptRoot/../dev.cmd" -Destination "$launcherRoot/dev.cmd"
    [IO.File]::WriteAllText("$launcherRoot/scripts/dev.ps1", @'
param([switch]$CheckOnly, [string]$Ip)
if (!$CheckOnly -or $Ip -ne '192.0.2.10') { exit 2 }
if ((Get-ExecutionPolicy -Scope Process) -ne 'Bypass') { exit 3 }
exit 37
'@)
    $launcherPath = "$launcherRoot/dev.cmd".Replace("'", "''")
    & powershell.exe -NoProfile -ExecutionPolicy Restricted -Command "& '$launcherPath' -CheckOnly -Ip 192.0.2.10; exit `$LASTEXITCODE"
    Assert-DevTest ($LASTEXITCODE -eq 37) 'Iniciador falhou sob Restricted, perdeu argumentos ou codigo de saida.'
    Write-Host 'PASS: dev.cmd sob Restricted, caminho com espacos, argumentos e codigo de saida.'

    $configuration = [pscustomobject]@{
        SUPABASE_URL = 'https://example.supabase.co'
        SUPABASE_KEY = [guid]::NewGuid().ToString()
        SUPABASE_SECRET_KEY = ''
        CASA_CONVITE_SECRET = [guid]::NewGuid().ToString()
    }
    Assert-DevTest (@(Get-DevConfigurationIssues $configuration).Count -eq 0) 'Configuracao valida rejeitada.'
    $configuration.SUPABASE_URL = 'http://localhost:54321'
    $configuration.CASA_CONVITE_SECRET = ''
    Assert-DevTest (@(Get-DevConfigurationIssues $configuration).Count -eq 2) 'URL local e segredo ausente precisam ser rejeitados.'
    $configuration.SUPABASE_URL = 'https://example.supabase.co'
    $configuration.SUPABASE_SECRET_KEY = $configuration.SUPABASE_KEY
    $configuration.SUPABASE_KEY = ''
    $configuration.CASA_CONVITE_SECRET = [guid]::NewGuid().ToString()
    Assert-DevTest (@(Get-DevConfigurationIssues $configuration).Count -eq 0) 'Alias da chave Supabase rejeitado.'
    Write-Host 'PASS: validacao de configuracao e alias da chave.'

    $nativeResult = Invoke-DevCommand node.exe @('--version') 'Falha ao consultar Node.' -Capture
    Assert-DevTest ($nativeResult -match '^v\d+\.') 'Saida do processo nao foi capturada.'
    Assert-DevFailure {
        Invoke-DevCommand node.exe @('-e', 'process.exit(7)') 'Falha esperada do processo.' -Capture
    } 'Falha esperada do processo.'
    if (![Console]::IsOutputRedirected) {
        Invoke-DevCommand node.exe @('-e', 'if (!process.stdout.isTTY) process.exit(9)') `
            'O comando interativo perdeu o console nativo.'
        Write-Host 'PASS: comando interativo preserva o console nativo.'
    }
    Write-Host 'PASS: comando externo propaga falha e captura saida.'

    function Invoke-DevCommand {
        return ($configuration | ConvertTo-Json -Compress | ForEach-Object { '{"services":{"backend":{"environment":' + $_ + '}}}' })
    }
    $parsed = Get-DevConfiguration @('compose')
    Assert-DevTest ($parsed.SUPABASE_SECRET_KEY -ceq $configuration.SUPABASE_SECRET_KEY) 'Configuracao Compose nao foi interpretada.'
    function Invoke-DevCommand { return 'resposta invalida' }
    Assert-DevFailure { Get-DevConfiguration @('compose') } 'configuracao valida'
    Write-Host 'PASS: leitura do JSON Compose e mensagem sanitizada para resposta invalida.'

    function Get-NetIPAddress {
        @(
            [pscustomobject]@{ IPAddress = '127.0.0.1'; AddressState = 'Preferred'; InterfaceIndex = 1 }
            [pscustomobject]@{ IPAddress = '192.0.2.10'; AddressState = 'Preferred'; InterfaceIndex = 2 }
            [pscustomobject]@{ IPAddress = '198.51.100.10'; AddressState = 'Preferred'; InterfaceIndex = 3 }
        )
    }
    function Get-NetIPConfiguration {
        [pscustomobject]@{ IPv4DefaultGateway = '192.0.2.1'; InterfaceIndex = 2 }
    }
    Assert-DevTest ((Get-DevIp '') -eq '192.0.2.10') 'Selecao da rede com gateway falhou.'
    Assert-DevTest ((Get-DevIp '198.51.100.10') -eq '198.51.100.10') 'IP explicito ativo rejeitado.'
    Assert-DevFailure { Get-DevIp '127.0.0.1' } 'IPv4 ativo'
    Assert-DevFailure { Get-DevIp '203.0.113.20' } 'IPv4 ativo'
    Write-Host 'PASS: selecao de IP e rejeicao de loopback/IP nao atribuido.'

    # Daqui em diante, Docker, instaladores e servicos sao simulados.
    function Get-Command { [pscustomobject]@{ Name = 'simulado' } }
    function Read-Host { return 'n' }
    function Invoke-DevCommand { throw 'Nenhum instalador deveria ser executado.' }
    Assert-DevFailure { Install-DevDependency 'Docker' 'Docker.DockerDesktop' 'https://example.test' } 'Instale Docker'
    Write-Host 'PASS: recusar instalacao nao executa instalador.'

    function Get-DevConfiguration {
        if (!(Test-Path "$work/.env")) { throw 'Arquivo ausente.' }
        $content = [IO.File]::ReadAllText("$work/.env")
        $configuration.CASA_CONVITE_SECRET = [regex]::Match($content, "(?m)^CASA_CONVITE_SECRET='([^']+)'").Groups[1].Value
        return $configuration
    }
    Initialize-DevConfiguration $work @()
    $before = [IO.File]::ReadAllText("$work/.env")
    Initialize-DevConfiguration $work @()
    Assert-DevTest ([IO.File]::ReadAllText("$work/.env") -ceq $before) 'Segredo existente foi alterado na segunda execucao.'
    Assert-DevTest ([Text.Encoding]::UTF8.GetByteCount($configuration.CASA_CONVITE_SECRET) -ge 32) 'Segredo gerado insuficiente.'
    Write-Host 'PASS: primeira execucao cria .env e segredo; segunda preserva o arquivo.'

    $script:calls = [Collections.Generic.List[string]]::new()
    $script:failAt = ''
    function Test-DevNode { return $true }
    function Initialize-DevConfiguration { }
    function Get-DevIp { return '192.0.2.10' }
    function Get-NetTCPConnection { }
    function Wait-DevDocker { $script:calls.Add('docker-ready') }
    function Wait-DevBackend {
        $script:calls.Add('health')
        if ($script:failAt -eq 'health') { throw 'health falhou' }
    }
    function Invoke-DevCommand {
        param([string]$Command, [string[]]$Arguments, [string]$Failure, [switch]$Capture)
        if ($Command -eq 'npm.cmd') { $stage = 'npm' }
        elseif ($Command -eq 'node.exe') {
            $stage = 'expo'
            Assert-DevTest (($Arguments -join ' ') -eq 'node_modules/expo/bin/cli start --go --lan --port 8081') 'Comando Expo incorreto.'
            Assert-DevTest ($env:EXPO_PUBLIC_API_URL -eq 'http://192.0.2.10:8000') 'URL da API nao chegou ao Expo.'
            Assert-DevTest ($env:EXPO_NO_DOTENV -eq '1') 'Expo nao deve carregar .env.'
            Assert-DevTest ($env:REACT_NATIVE_PACKAGER_HOSTNAME -eq '192.0.2.10') 'IP anunciado pelo Expo incorreto.'
        }
        elseif ($Arguments -contains 'up') {
            $stage = 'up'
            Assert-DevTest (($Arguments[0..4] -join ' ') -eq 'compose --ansi never --progress plain') 'Compose precisa usar progresso sem console interativo.'
            Assert-DevTest (($Arguments[-5..-1] -join ' ') -eq 'up -d --build redis backend') 'Servicos inesperados; nao iniciar agendador.'
        }
        elseif ($Arguments -contains 'exec') { $stage = 'redis' }
        else { $stage = 'compose-version' }
        $script:calls.Add($stage)
        if ($script:failAt -eq $stage) { throw "$stage falhou" }
    }
    $env:EXPO_PUBLIC_API_URL = 'http://original.invalid'
    $originalDirectory = (Get-Location).Path
    Start-Dev $work
    Assert-DevTest (($script:calls -join ',') -eq 'compose-version,docker-ready,npm,up,health,redis,expo') 'Ordem de inicializacao incorreta.'
    Assert-DevTest ($env:EXPO_PUBLIC_API_URL -eq 'http://original.invalid') 'Ambiente nao restaurado.'
    Assert-DevTest ((Get-Location).Path -eq $originalDirectory) 'Diretorio nao restaurado.'
    $script:calls.Clear()
    Start-Dev $work
    Assert-DevTest (!$script:calls.Contains('npm')) 'Dependencias foram reinstaladas sem mudanca.'
    [IO.File]::WriteAllText("$work/src/frontend/package-lock.json", '{"lockfileVersion":3}')
    $script:calls.Clear()
    Start-Dev $work
    Assert-DevTest ($script:calls.Contains('npm')) 'Mudanca no lockfile nao disparou npm ci.'
    Write-Host 'PASS: ordem, argumentos, ambiente temporario e reinstalacao somente quando necessaria.'

    foreach ($stage in @('npm', 'up', 'health', 'redis', 'expo')) {
        if ($stage -eq 'npm') { Remove-Item -LiteralPath "$work/src/frontend/node_modules/.dev-install" }
        $script:failAt = $stage
        $script:calls.Clear()
        Assert-DevFailure { Start-Dev $work } "$stage falhou"
        if ($stage -ne 'expo') { Assert-DevTest (!$script:calls.Contains('expo')) 'Expo iniciou antes dos servicos ficarem prontos.' }
        Assert-DevTest ($env:EXPO_PUBLIC_API_URL -eq 'http://original.invalid') 'Ambiente nao restaurado apos falha.'
        Assert-DevTest ((Get-Location).Path -eq $originalDirectory) 'Diretorio nao restaurado apos falha.'
    }
    Write-Host 'PASS: falhas de containers, health, Redis e Expo interrompem o fluxo e restauram o ambiente.'
    Write-Host 'Todos os testes do script passaram (servicos simulados; sem banco ou instalacoes).'
} finally {
    [Environment]::SetEnvironmentVariable('EXPO_PUBLIC_API_URL', $oldApi, 'Process')
    $resolved = [IO.Path]::GetFullPath($work)
    if ($resolved.StartsWith([IO.Path]::GetTempPath(), [StringComparison]::OrdinalIgnoreCase) -and
        (Split-Path $resolved -Leaf) -like 'teto-justo-dev-test-*') {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
