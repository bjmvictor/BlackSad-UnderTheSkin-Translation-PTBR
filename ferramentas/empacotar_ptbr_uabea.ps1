[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string] $BundleOrigem,

    [string] $Catalogo,
    [string] $RawOriginal,
    [string] $ReferenciaArabe,
    [string] $PastaSaida,
    [long] $PathId = -1248374269677720278,
    [ValidateSet('en', 'es')]
    [string] $IdiomaDestino = 'en',
    [switch] $InstalarNoJogo
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path
$uabeaDir = Join-Path $scriptDir 'uabea-v8'
$geradorRaw = Join-Path $scriptDir 'gerar_raw_ptbr_tamanho_fixo.py'
$geradorSlot = Join-Path $scriptDir 'gerar_raw_ptbr_slot_fixo.py'
$ponteFonte = Join-Path $scriptDir 'UabeaRawPatcher.cs'
if ([string]::IsNullOrWhiteSpace($Catalogo)) { $Catalogo = Join-Path $repoRoot 'texto\catalogo\pt-BR.csv' }
if ([string]::IsNullOrWhiteSpace($RawOriginal)) { $RawOriginal = Join-Path $repoRoot 'saida-teste\uabea-csv\Script-original.dat' }
if ([string]::IsNullOrWhiteSpace($ReferenciaArabe)) { $ReferenciaArabe = Join-Path $repoRoot 'referencia\Blacksad_Data\StreamingAssets\assets_data\2172dc1d-d264-45aa-a94c-231bf3de6baa' }
if ([string]::IsNullOrWhiteSpace($PastaSaida)) { $PastaSaida = Join-Path $repoRoot 'saida-teste\uabea-csv' }

foreach ($arquivo in @($Catalogo, $RawOriginal, $ReferenciaArabe, $geradorRaw, $geradorSlot, $ponteFonte)) {
    if (-not (Test-Path $arquivo -PathType Leaf)) {
        throw "Arquivo obrigatorio nao encontrado: $arquivo"
    }
}
if (-not (Test-Path $uabeaDir -PathType Container)) {
    throw "Pasta do UABEA nao encontrada: $uabeaDir"
}

$BundleOrigem = (Resolve-Path $BundleOrigem).Path
$Catalogo = (Resolve-Path $Catalogo).Path
$RawOriginal = (Resolve-Path $RawOriginal).Path
$ReferenciaArabe = (Resolve-Path $ReferenciaArabe).Path

New-Item -ItemType Directory -Force -Path $PastaSaida | Out-Null
$PastaSaida = (Resolve-Path $PastaSaida).Path
$nomeBase = [IO.Path]::GetFileName($BundleOrigem)
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$rawPtBr = Join-Path $PastaSaida ("Script-ptbr-{0}-{1}.dat" -f $IdiomaDestino, $timestamp)
$bundleSaida = Join-Path $PastaSaida ("{0}.ptbr-{1}-uabea-{2}" -f $nomeBase, $IdiomaDestino, $timestamp)

Write-Host '1/3 Gerando o TextAsset PT-BR a partir do CSV...'
if ($IdiomaDestino -eq 'es') {
    & python $geradorSlot $RawOriginal $Catalogo es $rawPtBr
}
else {
    & python $geradorRaw $RawOriginal $Catalogo $ReferenciaArabe $rawPtBr
}
if ($LASTEXITCODE -ne 0) { throw 'A geracao do Raw PT-BR falhou.' }

Write-Host '2/3 Compilando a ponte local do UABEA...'
$cscCandidates = @(
    'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\Roslyn\csc.exe',
    'C:\Program Files\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
)
$csc = $cscCandidates | Where-Object { Test-Path $_ -PathType Leaf } | Select-Object -First 1
if (-not $csc) {
    throw 'Compilador C# do Visual Studio nao encontrado. Instale o componente "MSBuild Tools" do Visual Studio para usar a automacao.'
}
$runtimeRoot = 'C:\Program Files\dotnet\shared\Microsoft.NETCore.App'
$runtimeDir = Get-ChildItem -LiteralPath $runtimeRoot -Directory -ErrorAction Stop |
    Where-Object { $_.Name -like '6.*' } |
    Sort-Object { [Version]$_.Name } -Descending |
    Select-Object -First 1
if (-not $runtimeDir) {
    throw 'O .NET 6 Runtime nao foi encontrado; ele e necessario porque o UABEA instalado usa .NET 6.'
}
function Test-ManagedAssembly([string] $Path) {
    try { [Reflection.AssemblyName]::GetAssemblyName($Path) | Out-Null; return $true }
    catch { return $false }
}
$runtimeReferences = Get-ChildItem -LiteralPath $runtimeDir.FullName -Filter '*.dll' -File |
    Where-Object { Test-ManagedAssembly $_.FullName } |
    ForEach-Object { '/r:' + $_.FullName }
$uabeaReferences = Get-ChildItem -LiteralPath $uabeaDir -Filter '*.dll' -File |
    Where-Object { Test-ManagedAssembly $_.FullName } |
    ForEach-Object { '/r:' + $_.FullName }
$outputAssembly = Join-Path $uabeaDir 'UabeaRawPatcher.dll'
$runtimeConfig = Join-Path $uabeaDir 'UabeaRawPatcher.runtimeconfig.json'
& $csc /noconfig /nostdlib /target:exe ("/out:{0}" -f $outputAssembly) `
    $runtimeReferences $uabeaReferences $ponteFonte
if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar a ponte UABEA.' }
Copy-Item -LiteralPath (Join-Path $uabeaDir 'UABEAvalonia.runtimeconfig.json') -Destination $runtimeConfig -Force

Write-Host '3/3 Aplicando o Raw no bundle copiado...'
& dotnet exec --runtimeconfig $runtimeConfig $outputAssembly $BundleOrigem $rawPtBr "$PathId" $bundleSaida
if ($LASTEXITCODE -ne 0) { throw "A ponte UABEA retornou o codigo $LASTEXITCODE." }

Write-Host ''
if ($InstalarNoJogo) {
    Write-Host 'Bundle gerado e pronto para a instalacao:' -ForegroundColor Green
    Write-Host $bundleSaida
    $backup = "{0}.backup-ptbr-uabea-{1}" -f $BundleOrigem, $timestamp
    if ($PSCmdlet.ShouldProcess($BundleOrigem, "criar backup em '$backup' e instalar o bundle PT-BR gerado")) {
        Copy-Item -LiteralPath $BundleOrigem -Destination $backup -ErrorAction Stop
        Copy-Item -LiteralPath $bundleSaida -Destination $BundleOrigem -ErrorAction Stop
        Write-Host "Instalado no jogo. Backup criado em: $backup" -ForegroundColor Green
    }
}
else {
    Write-Host 'Concluido. O bundle de saida NAO foi copiado para a pasta do jogo:' -ForegroundColor Green
    Write-Host $bundleSaida
    Write-Host 'Teste esse arquivo manualmente no jogo antes de usar -InstalarNoJogo.' -ForegroundColor Yellow
}
