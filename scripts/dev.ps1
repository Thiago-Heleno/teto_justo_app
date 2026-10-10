#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Ip,
    [switch]$CheckOnly
)

function Invoke-DevCommand {
    param([string]$Command, [string[]]$Arguments, [string]$Failure, [switch]$Capture)
    # Stderr de config/exec pode conter configuracao privada. Nao o reproduza.
    $ErrorActionPreference = 'Continue'
    if ($Capture) { $output = & $Command @Arguments 2>$null }
    # Preserve o console nativo para Docker, instaladores e o QR/interacao do Expo.
    else { & $Command @Arguments }
    if ($LASTEXITCODE -ne 0) { throw $Failure }
    if ($Capture) { return $output }
}

function Test-DevNode {
    if (!(Get-Command node.exe -ErrorAction SilentlyContinue) -or
        !(Get-Command npm.cmd -ErrorAction SilentlyContinue)) { return $false }
    try {
        $version = Invoke-DevCommand node.exe @('--version') 'Node.js nao respondeu.' -Capture
        return [version]($version.Trim().TrimStart('v')) -ge [version]'24.3.0'
    } catch { return $false }
}

function Install-DevDependency {
    param([string]$Name, [string]$Package, [string]$Url)
    if (!(Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "Instale $Name em $Url e execute novamente. WinGet nao esta disponivel."
    }
    $answer = Read-Host "$Name ausente ou incompativel. Instalar pelo WinGet agora? [s/N]"
    if ($answer -notmatch '^(s|sim)$') { throw "Instale $Name em $Url para continuar." }
    Invoke-DevCommand winget.exe @('install', '--exact', '--id', $Package, '--source', 'winget') `
        "Instalacao de $Name nao concluida. Termine o instalador; se ele pedir, reinicie o Windows e execute novamente."
    $env:Path = @(
        [Environment]::GetEnvironmentVariable('Path', 'Machine')
        [Environment]::GetEnvironmentVariable('Path', 'User')
        $env:Path
    ) -join ';'
}

function Get-DevConfiguration {
    param([string[]]$Compose)
    $json = Invoke-DevCommand docker.exe ($Compose + @('config', '--format', 'json')) `
        'Nao foi possivel ler a configuracao do Compose. Confira a sintaxe do .env.' -Capture
    try { return ($json -join "`n" | ConvertFrom-Json).services.backend.environment }
    catch { throw 'O Docker Compose nao retornou uma configuracao valida. Atualize o Docker Desktop.' }
}

function Get-DevConfigurationIssues {
    param($Configuration)
    $url = $null
    if (![Uri]::TryCreate($Configuration.SUPABASE_URL, [UriKind]::Absolute, [ref]$url) -or
        $url.Scheme -ne 'https' -or !$url.Host -or $url.UserInfo) {
        'SUPABASE_URL (URL HTTPS do projeto de teste)'
    }
    if (!$Configuration.SUPABASE_KEY -and !$Configuration.SUPABASE_SECRET_KEY) {
        'SUPABASE_KEY (ou SUPABASE_SECRET_KEY)'
    }
    if ([Text.Encoding]::UTF8.GetByteCount([string]$Configuration.CASA_CONVITE_SECRET) -lt 32) {
        'CASA_CONVITE_SECRET (ao menos 32 bytes)'
    }
}

function Initialize-DevConfiguration {
    param([string]$Root, [string[]]$Compose)
    $envFile = Join-Path $Root '.env'
    if (!(Test-Path -LiteralPath $envFile)) {
        Copy-Item -LiteralPath (Join-Path $Root '.env.example') -Destination $envFile
        Write-Host 'Arquivo .env criado a partir de .env.example.'
    }
    $configuration = Get-DevConfiguration $Compose
    if (!$configuration.CASA_CONVITE_SECRET) {
        $bytes = New-Object byte[] 32
        $random = [Security.Cryptography.RandomNumberGenerator]::Create()
        try { $random.GetBytes($bytes) } finally { $random.Dispose() }
        $secret = [Convert]::ToBase64String($bytes)
        $content = [IO.File]::ReadAllText($envFile)
        if ($content -match '(?m)^\s*CASA_CONVITE_SECRET\s*=') {
            $content = [regex]::Replace($content, '(?m)^\s*CASA_CONVITE_SECRET\s*=.*$', "CASA_CONVITE_SECRET='$secret'")
        } else { $content += "`nCASA_CONVITE_SECRET='$secret'`n" }
        [IO.File]::WriteAllText($envFile, $content, (New-Object Text.UTF8Encoding($false)))
        Write-Host 'Segredo local de convites gerado e salvo apenas no .env.'
    }
    while ($true) {
        $issues = @(Get-DevConfigurationIssues (Get-DevConfiguration $Compose))
        if (!$issues.Count) { break }
        Write-Host ('Preencha/corrija no .env: ' + ($issues -join ', '))
        Write-Host 'Use um projeto Supabase de TESTE com as migrations do projeto ja revisadas/aplicadas.'
        [void](Read-Host 'Edite o .env no seu editor e pressione Enter para verificar novamente (Ctrl+C cancela)')
    }
}

function Get-DevIp {
    param([string]$RequestedIp)
    $addresses = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
        Where-Object { $_.AddressState -eq 'Preferred' -and $_.IPAddress -notmatch '^(127\.|169\.254\.|0\.)' })
    if ($RequestedIp) {
        if ($RequestedIp -notin $addresses.IPAddress) {
            throw 'O -Ip precisa ser um IPv4 ativo deste computador, acessivel pelo celular.'
        }
        return $RequestedIp
    }
    $interfaces = @(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway }).InterfaceIndex
    $candidates = @($addresses | Where-Object { $_.InterfaceIndex -in $interfaces } |
        Sort-Object IPAddress -Unique)
    if (!$candidates.Count) { throw 'Nenhuma rede encontrada. Conecte o Wi-Fi ou informe -Ip com o IPv4 da rede local.' }
    if ($candidates.Count -eq 1) { return $candidates[0].IPAddress }
    Write-Host 'Mais de uma rede encontrada. Escolha a rede compartilhada com o celular (evite VPN).'
    for ($i = 0; $i -lt $candidates.Count; $i++) {
        Write-Host ("{0}: {1} ({2})" -f ($i + 1), $candidates[$i].IPAddress, $candidates[$i].InterfaceAlias)
    }
    $choice = 0
    if (![int]::TryParse((Read-Host 'Numero da rede'), [ref]$choice) -or
        $choice -lt 1 -or $choice -gt $candidates.Count) { throw 'Escolha invalida. Execute novamente ou informe -Ip.' }
    return $candidates[$choice - 1].IPAddress
}

function Wait-DevDocker {
    $desktop = @(
        (Join-Path $env:ProgramFiles 'Docker/Docker/Docker Desktop.exe')
        (Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/Docker Desktop.exe')
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    try {
        $engine = Invoke-DevCommand docker.exe @('info', '--format', '{{.OSType}}') 'Docker indisponivel.' -Capture
    } catch {
        if ($desktop) { Start-Process -FilePath $desktop -WindowStyle Hidden }
        Write-Host 'Aguardando Docker. Na primeira vez, abra o Docker Desktop e conclua sua configuracao.'
        $deadline = (Get-Date).AddSeconds(120)
        do {
            Start-Sleep -Seconds 3
            try { $engine = Invoke-DevCommand docker.exe @('info', '--format', '{{.OSType}}') 'Docker indisponivel.' -Capture }
            catch { $engine = $null }
        } until ($engine -or (Get-Date) -ge $deadline)
    }
    if (!$engine) {
        throw 'Docker nao iniciou. Confira o WSL 2 e a virtualizacao no Docker Desktop. Se houver pedido de reinicio, reinicie e execute o script novamente.'
    }
    if ($engine.Trim() -ne 'linux') { throw 'Selecione Linux containers no Docker Desktop e execute novamente.' }
}

function Wait-DevBackend {
    $deadline = (Get-Date).AddSeconds(90)
    do {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 3
            if ($health.status -eq 'ok') { return }
        } catch { }
        Start-Sleep -Seconds 2
    } until ((Get-Date) -ge $deadline)
    throw 'Backend nao ficou pronto em /health. Confira o Docker Compose e a configuracao do backend; o Expo nao foi iniciado.'
}

function Start-Dev {
    param([string]$Root, [string]$RequestedIp, [switch]$OnlyCheck)
    $ErrorActionPreference = 'Stop'
    $PSNativeCommandUseErrorActionPreference = $false
    if ($env:OS -ne 'Windows_NT') { throw 'Este script foi preparado para Windows.' }
    $compose = @('compose', '--ansi', 'never', '--progress', 'plain', '--project-directory', $Root, '--env-file', (Join-Path $Root '.env'), '-f', (Join-Path $Root 'docker-compose.yml'))
    if ($OnlyCheck) {
        $issues = @()
        if (!(Test-DevNode)) { $issues += 'Node.js 24.3+ e npm ausentes ou incompativeis.' }
        if (!(Get-Command docker.exe -ErrorAction SilentlyContinue)) { $issues += 'Docker Desktop nao encontrado.' }
        else {
            try {
                Invoke-DevCommand docker.exe @('compose', 'version') 'Docker Compose indisponivel.' -Capture | Out-Null
                $engine = Invoke-DevCommand docker.exe @('info', '--format', '{{.OSType}}') 'Docker Desktop nao esta pronto.' -Capture
                if ($engine.Trim() -ne 'linux') { $issues += 'Docker precisa usar Linux containers.' }
                if (Test-Path -LiteralPath (Join-Path $Root '.env')) {
                    $issues += @(Get-DevConfigurationIssues (Get-DevConfiguration $compose))
                }
            } catch { $issues += $_.Exception.Message }
        }
        if (!(Test-Path -LiteralPath (Join-Path $Root '.env'))) { $issues += 'Arquivo .env ainda nao configurado.' }
        if ($issues.Count) { throw ('Pendencias: ' + ($issues -join ' ')) }
        Write-Host 'Pre-requisitos e configuracao conferidos. Banco, migrations e acesso pelo celular nao foram testados.'
        return
    }
    if (!(Test-DevNode)) {
        Install-DevDependency 'Node.js LTS (24.3+)' 'OpenJS.NodeJS.LTS' 'https://nodejs.org/en/download'
        if (!(Test-DevNode)) { throw 'Node.js 24.3+ e npm ainda nao disponiveis. Reabra o terminal e execute novamente.' }
    }
    if (!(Get-Command docker.exe -ErrorAction SilentlyContinue)) {
        Install-DevDependency 'Docker Desktop' 'Docker.DockerDesktop' 'https://docs.docker.com/desktop/setup/install/windows-install/'
        if (!(Get-Command docker.exe -ErrorAction SilentlyContinue)) { throw 'Reabra o terminal apos instalar o Docker Desktop e execute novamente.' }
    }
    Invoke-DevCommand docker.exe @('compose', 'version') 'Instale/atualize o Docker Desktop com Docker Compose v2.' -Capture | Out-Null
    Initialize-DevConfiguration $Root $compose
    $lanIp = Get-DevIp $RequestedIp
    if (Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue) {
        throw 'A porta 8081 esta ocupada. Encerre a outra instancia do Expo/servico e execute novamente.'
    }
    Wait-DevDocker
    $frontend = Join-Path $Root 'src/frontend'
    Push-Location $frontend
    $saved = @{}
    $variables = @('EXPO_PUBLIC_API_URL', 'REACT_NATIVE_PACKAGER_HOSTNAME', 'EXPO_NO_DOTENV')
    foreach ($name in $variables) { $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
    try {
        $fingerprint = ((Get-FileHash package.json, package-lock.json).Hash -join '-') + '-' + (& node.exe --version)
        $stamp = Join-Path $frontend 'node_modules/.dev-install'
        if (!(Test-Path node_modules/.bin/expo.cmd) -or !(Test-Path $stamp) -or
            [IO.File]::ReadAllText($stamp).Trim() -ne $fingerprint) {
            Write-Host 'Instalando dependencias do frontend pelo package-lock.json...'
            Invoke-DevCommand npm.cmd @('ci') 'npm ci falhou. Confira a conexao e a compatibilidade do package-lock.json.'
            [IO.File]::WriteAllText($stamp, $fingerprint)
        }
        Write-Host 'Iniciando Redis e backend (o agendador de penalidades nao sera iniciado)...'
        Invoke-DevCommand docker.exe ($compose + @('up', '-d', '--build', 'redis', 'backend')) `
            'Falha ao subir os containers. Consulte o erro do Docker acima; o Expo nao foi iniciado.'
        Wait-DevBackend
        Invoke-DevCommand docker.exe ($compose + @('exec', '-T', 'backend', 'python', '-c',
            "import os; from redis import Redis; assert Redis.from_url(os.environ['REDIS_URL'], socket_connect_timeout=3, socket_timeout=3).ping()")) `
            'Backend respondeu, mas nao conseguiu acessar o Redis. O Expo nao foi iniciado.' -Capture | Out-Null
        $env:EXPO_PUBLIC_API_URL = "http://${lanIp}:8000"
        $env:REACT_NATIVE_PACKAGER_HOSTNAME = $lanIp
        $env:EXPO_NO_DOTENV = '1'
        Write-Host "Backend e Redis prontos. No celular, confira http://${lanIp}:8000/health."
        Write-Host 'Supabase configurado; conexao, credenciais e migrations ainda dependem da validacao dos fluxos do app.'
        Write-Host 'Use o mesmo Wi-Fi. Instale o Expo Go compativel com SDK 57: https://expo.dev/go'
        Write-Host 'Se o Expo solicitar login, siga a orientacao exibida. Leia o QR code no Expo Go.'
        Write-Host 'Se o celular nao conectar, confira o firewall para Node/Docker e as portas 8000 e 8081 na rede privada.'
        Invoke-DevCommand node.exe @('node_modules/expo/bin/cli', 'start', '--go', '--lan', '--port', '8081') 'O Expo encerrou com erro.'
    } finally {
        foreach ($name in $variables) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
        Pop-Location
        Write-Host 'Se algum container foi iniciado, ele continua disponivel. Para parar, na raiz: docker compose stop backend redis'
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try { Start-Dev -Root (Split-Path $PSScriptRoot -Parent) -RequestedIp $Ip -OnlyCheck:$CheckOnly }
    catch { Write-Host ("ERRO: " + $_.Exception.Message) -ForegroundColor Red; exit 1 }
}
