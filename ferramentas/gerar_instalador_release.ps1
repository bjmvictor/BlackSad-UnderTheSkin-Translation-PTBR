[CmdletBinding()]
param(
    [ValidatePattern('^[0-9A-Za-z][0-9A-Za-z._-]*$')]
    [string] $Versao = '0.1.0',
    [string] $PastaSaida,
    [string] $BundleOriginal,
    [string] $RawOriginal,
    [string] $Catalogo,
    [string] $Referencia,
    [long] $PathId = -1248374269677720278
)

# Prepara um ZIP para publicacao. Ele NAO copia o bundle completo do jogo.
# O arquivo Raw e aplicado no bundle original da instalacao do jogador.
$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = (Resolve-Path (Join-Path $scriptDir '..')).Path
$uabeaDir = Join-Path $scriptDir 'uabea-v8'
$generator = Join-Path $scriptDir 'gerar_raw_ptbr_hibrido.py'
$bridgeSource = Join-Path $scriptDir 'UabeaRawPatcher.cs'
$installerSource = Join-Path $scriptDir 'instalador'
if ([string]::IsNullOrWhiteSpace($PastaSaida)) { $PastaSaida = Join-Path $root 'dist' }
if ([string]::IsNullOrWhiteSpace($BundleOriginal)) { $BundleOriginal = Join-Path $root 'teste-uabea\2172dc1d-d264-45aa-a94c-231bf3de6baa' }
if ([string]::IsNullOrWhiteSpace($RawOriginal)) { $RawOriginal = Join-Path $root 'teste-uabea\Script-original.dat' }
if ([string]::IsNullOrWhiteSpace($Catalogo)) { $Catalogo = Join-Path $root 'texto\catalogo\pt-BR.csv' }
if ([string]::IsNullOrWhiteSpace($Referencia)) { $Referencia = $BundleOriginal }

foreach ($file in @($BundleOriginal, $RawOriginal, $Catalogo, $Referencia, $generator, $bridgeSource)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Arquivo obrigatorio nao encontrado: $file" }
}
foreach ($file in @((Join-Path $uabeaDir 'AssetsTools.NET.dll'), (Join-Path $uabeaDir 'UABEAvalonia.runtimeconfig.json'))) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Dependencia UABEA nao encontrada: $file" }
}

$PastaSaida = [IO.Path]::GetFullPath($PastaSaida)
$packageName = "Blacksad_PTBR-v$Versao"
$staging = Join-Path $PastaSaida $packageName
$zip = Join-Path $PastaSaida ($packageName + '.zip')
if (Test-Path -LiteralPath $staging) { throw "A pasta de release ja existe: $staging. Escolha outra versao ou remova-a manualmente." }
if (Test-Path -LiteralPath $zip) { throw "O ZIP de release ja existe: $zip. Escolha outra versao ou remova-o manualmente." }
New-Item -ItemType Directory -Force -Path (Join-Path $staging 'conteudo'), (Join-Path $staging 'bin') | Out-Null

try {
    $raw = Join-Path $staging 'conteudo\Script-ptbr-en-hybrid.dat'
    Write-Host '1/4 Gerando Raw PT-BR hibrido a partir do CSV...'
    & python $generator $RawOriginal $Catalogo $Referencia $raw
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $raw -PathType Leaf)) { throw 'A geracao do Raw PT-BR falhou.' }

    Write-Host '2/4 Compilando aplicador minimo do UABEA...'
    $cscCandidates = @(
        'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\Roslyn\csc.exe',
        'C:\Program Files\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
    )
    $csc = $cscCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $csc) { throw 'Compilador C# do Visual Studio nao encontrado. Instale MSBuild Tools para criar a release.' }
    $runtimeRoot = 'C:\Program Files\dotnet\shared\Microsoft.NETCore.App'
    $runtime = Get-ChildItem -LiteralPath $runtimeRoot -Directory -ErrorAction Stop | Where-Object { $_.Name -like '6.*' } | Sort-Object { [Version]$_.Name } -Descending | Select-Object -First 1
    if (-not $runtime) { throw '.NET 6 Runtime nao encontrado.' }
    function Test-ManagedAssembly([string] $Path) { try { [Reflection.AssemblyName]::GetAssemblyName($Path) | Out-Null; return $true } catch { return $false } }
    $references = @()
    $references += Get-ChildItem -LiteralPath $runtime.FullName -File -Filter '*.dll' |
        Where-Object { Test-ManagedAssembly $_.FullName } |
        ForEach-Object { '/r:' + $_.FullName }
    $references += '/r:' + (Join-Path $uabeaDir 'AssetsTools.NET.dll')
    $bridge = Join-Path $staging 'bin\UabeaRawPatcher.dll'
    & $csc /noconfig /nostdlib /target:exe ("/out:{0}" -f $bridge) $references $bridgeSource
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar o aplicador UABEA.' }
    Copy-Item -LiteralPath (Join-Path $uabeaDir 'AssetsTools.NET.dll') -Destination (Join-Path $staging 'bin\AssetsTools.NET.dll')
    Copy-Item -LiteralPath (Join-Path $uabeaDir 'UABEAvalonia.runtimeconfig.json') -Destination (Join-Path $staging 'bin\UabeaRawPatcher.runtimeconfig.json')

    Write-Host '3/4 Validando o aplicador dentro do pacote...'
    $probe = Join-Path $staging 'conteudo\.probe-bundle'
    $oldLibraryDirectory = $env:UABEA_LIB_DIR
    try {
        $env:UABEA_LIB_DIR = Join-Path $staging 'bin'
        & dotnet exec --runtimeconfig (Join-Path $staging 'bin\UabeaRawPatcher.runtimeconfig.json') $bridge $BundleOriginal $raw "$PathId" $probe
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $probe -PathType Leaf)) { throw 'A validacao do aplicador dentro do pacote falhou.' }
    } finally {
        if ($null -eq $oldLibraryDirectory) { Remove-Item Env:UABEA_LIB_DIR -ErrorAction SilentlyContinue } else { $env:UABEA_LIB_DIR = $oldLibraryDirectory }
        if (Test-Path -LiteralPath $probe -PathType Leaf) { Remove-Item -LiteralPath $probe -Force }
    }

    Write-Host '4/4 Montando ZIP de distribuicao...'
    $manifest = @{ schema = 1; version = $Versao; path_id = $PathId; raw_file = 'conteudo\Script-ptbr-en-hybrid.dat'; raw_sha256 = (Get-FileHash -LiteralPath $raw -Algorithm SHA256).Hash.ToLowerInvariant(); bridge_file = 'bin\UabeaRawPatcher.dll'; runtimeconfig_file = 'bin\UabeaRawPatcher.runtimeconfig.json' }
    $manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $staging 'conteudo\manifest.json') -Encoding UTF8
    foreach ($file in @('Instalar-PTBR.ps1', 'Instalar-PTBR.cmd', 'Desinstalar-PTBR.ps1', 'Desinstalar-PTBR.cmd', 'TERCEIROS.txt')) { Copy-Item -LiteralPath (Join-Path $installerSource $file) -Destination (Join-Path $staging $file) }
    @(
        'TRADUCAO PT-BR - BLACKSAD: UNDER THE SKIN',
        '',
        '1. Feche o jogo e a Steam se ela estiver atualizando arquivos.',
        '2. Extraia o ZIP inteiro em uma pasta qualquer.',
        '3. Clique duas vezes em Instalar-PTBR.cmd e confirme a pasta localizada.',
        '4. No jogo, selecione o idioma English.',
        '',
        'O instalador procura a Steam automaticamente. Se nao encontrar, abre um seletor',
        'para voce apontar a pasta que contem Blacksad.exe.',
        '',
        'Ele cria o backup original em Blacksad_PTBR_Backup dentro da pasta do jogo.',
        'Para desfazer, execute Desinstalar-PTBR.cmd; saves e configuracoes nao sao tocados.',
        '',
        'Requisitos: Windows, .NET 6 Desktop Runtime e uma copia legitima do jogo.',
        'Este pacote nao inclui o bundle completo do jogo. Use e redistribua somente',
        'de acordo com os termos do jogo e de sua editora.',
        '',
        'Versao: ' + $Versao
    ) | Set-Content -LiteralPath (Join-Path $staging 'LEIA-ME.txt') -Encoding UTF8
    Compress-Archive -LiteralPath $staging -DestinationPath $zip -CompressionLevel Optimal
    Write-Host ''
    Write-Host 'Release pronta:' -ForegroundColor Green
    Write-Host $zip
} catch {
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    throw
}
