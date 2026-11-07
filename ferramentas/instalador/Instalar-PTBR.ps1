[CmdletBinding()]
param(
    [string] $PastaJogo,
    [switch] $SemConfirmacao
)

$ErrorActionPreference = 'Stop'
$script:BundleRelative = 'Blacksad_Data\StreamingAssets\assets_data\2172dc1d-d264-45aa-a94c-231bf3de6baa'
$script:BackupFolderName = 'Blacksad_PTBR_Backup'
$script:PathId = [long]-1248374269677720278
$script:PackageRoot = $PSScriptRoot

# Steam costuma instalar o jogo em Program Files, onde a troca do bundle exige
# elevacao. O pedido e feito somente ao iniciar o instalador.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($PastaJogo) { $arguments += " -PastaJogo `"$PastaJogo`"" }
    if ($SemConfirmacao) { $arguments += ' -SemConfirmacao' }
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $arguments
    exit
}

function Get-Sha256([string] $Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Resolve-GameRoot([string] $Candidate) {
    if ([string]::IsNullOrWhiteSpace($Candidate) -or -not (Test-Path -LiteralPath $Candidate)) { return $null }
    $item = Get-Item -LiteralPath $Candidate
    $root = if ($item.PSIsContainer) { $item.FullName } elseif ($item.Name -ieq 'Blacksad.exe') { $item.Directory.FullName } else { return $null }
    $exe = Join-Path $root 'Blacksad.exe'
    $bundle = Join-Path $root $script:BundleRelative
    if ((Test-Path -LiteralPath $exe -PathType Leaf) -and (Test-Path -LiteralPath $bundle -PathType Leaf) -and ((Get-Item -LiteralPath $bundle).Length -gt 1048576)) {
        return (Resolve-Path -LiteralPath $root).Path
    }
    return $null
}

function Get-DetectedGameRoots {
    $steamRoots = [System.Collections.Generic.List[string]]::new()
    foreach ($path in @('C:\Program Files (x86)\Steam', 'C:\Program Files\Steam')) { if (Test-Path -LiteralPath $path -PathType Container) { $steamRoots.Add($path) } }
    try {
        $steamPath = (Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -Name SteamPath -ErrorAction Stop).SteamPath
        if ($steamPath -and (Test-Path -LiteralPath $steamPath -PathType Container)) { $steamRoots.Add($steamPath) }
    } catch { }

    $libraries = [System.Collections.Generic.List[string]]::new()
    foreach ($steam in ($steamRoots | Select-Object -Unique)) {
        $libraries.Add($steam)
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf -PathType Leaf) {
            foreach ($match in [regex]::Matches((Get-Content -LiteralPath $vdf -Raw), '"path"\s+"([^"]+)"', [Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
                $path = $match.Groups[1].Value.Replace('\\', '\')
                if (Test-Path -LiteralPath $path -PathType Container) { $libraries.Add($path) }
            }
        }
    }

    $found = [System.Collections.Generic.List[string]]::new()
    foreach ($library in ($libraries | Select-Object -Unique)) {
        $manifest = Join-Path $library 'steamapps\appmanifest_1003890.acf'
        $candidates = [System.Collections.Generic.List[string]]::new()
        if (Test-Path -LiteralPath $manifest -PathType Leaf) {
            $match = [regex]::Match((Get-Content -LiteralPath $manifest -Raw), '"installdir"\s+"([^"]+)"', [Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if ($match.Success) { $candidates.Add((Join-Path $library ('steamapps\common\' + $match.Groups[1].Value))) }
        }
        $common = Join-Path $library 'steamapps\common'
        if (Test-Path -LiteralPath $common -PathType Container) { $candidates.AddRange(@(Get-ChildItem -LiteralPath $common -Directory -ErrorAction SilentlyContinue | ForEach-Object FullName)) }
        foreach ($candidate in ($candidates | Select-Object -Unique)) {
            $root = Resolve-GameRoot $candidate
            if ($root) { $found.Add($root) }
        }
    }
    return @($found | Select-Object -Unique)
}

function Select-GameRoot([string] $RequestedPath) {
    $provided = Resolve-GameRoot $RequestedPath
    if ($provided) { return $provided }
    if ($RequestedPath) { throw "A pasta informada nao contem Blacksad.exe e o bundle esperado: $RequestedPath" }

    $found = @(Get-DetectedGameRoots)
    if ($found.Count -eq 1) {
        Write-Host "Jogo localizado: $($found[0])" -ForegroundColor Cyan
        return $found[0]
    }
    if ($found.Count -gt 1) {
        Write-Host 'Foram encontradas varias instalacoes:' -ForegroundColor Cyan
        for ($index = 0; $index -lt $found.Count; $index++) { Write-Host "[$($index + 1)] $($found[$index])" }
        $answer = Read-Host 'Digite o numero da instalacao ou deixe vazio para escolher uma pasta'
        $number = 0
        if ([int]::TryParse($answer, [ref]$number) -and $number -ge 1 -and $number -le $found.Count) { return $found[$number - 1] }
    }

    Add-Type -AssemblyName System.Windows.Forms
    $dialog = [System.Windows.Forms.FolderBrowserDialog]::new()
    $dialog.Description = 'Selecione a pasta que contem Blacksad.exe'
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $selected = Resolve-GameRoot $dialog.SelectedPath
        if ($selected) { return $selected }
    }
    throw 'Nenhuma instalacao valida do Blacksad foi selecionada.'
}

function Confirm([string] $Question, [switch] $Skip) {
    if ($Skip) { return }
    $answer = Read-Host "$Question [s/N]"
    if ($answer -notmatch '^(s|sim|y|yes)$') { throw 'Operacao cancelada.' }
}

function Test-GameClosed {
    if (Get-Process -Name 'Blacksad' -ErrorAction SilentlyContinue) { throw 'Feche Blacksad antes de instalar a traducao.' }
}

function Write-State([string] $BackupRoot, [hashtable] $State) {
    New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
    $temporary = Join-Path $BackupRoot ('.instalacao-' + [guid]::NewGuid().ToString('N') + '.tmp')
    $statePath = Join-Path $BackupRoot 'instalacao.json'
    $State | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $statePath -Force
}

try {
    $manifestPath = Join-Path $script:PackageRoot 'conteudo\manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'Pacote incompleto: conteudo\manifest.json nao foi encontrado.' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.schema -ne 1 -or [long]$manifest.path_id -ne $script:PathId) { throw 'Manifesto de instalacao invalido.' }
    $raw = Join-Path $script:PackageRoot $manifest.raw_file
    $bridge = Join-Path $script:PackageRoot $manifest.bridge_file
    $runtimeConfig = Join-Path $script:PackageRoot $manifest.runtimeconfig_file
    $libraries = Split-Path -Parent $bridge
    foreach ($file in @($raw, $bridge, $runtimeConfig, (Join-Path $libraries 'AssetsTools.NET.dll'))) { if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Pacote incompleto: $file" } }
    if ((Get-Sha256 $raw) -ne $manifest.raw_sha256.ToLowerInvariant()) { throw 'O arquivo de traducao esta corrompido ou foi alterado.' }

    $root = Select-GameRoot $PastaJogo
    $target = Join-Path $root $script:BundleRelative
    Test-GameClosed
    Confirm "Instalar PT-BR em '$root'? O bundle original sera copiado para '$script:BackupFolderName'" $SemConfirmacao

    $backupRoot = Join-Path $root $script:BackupFolderName
    $statePath = Join-Path $backupRoot 'instalacao.json'
    $previous = $null
    if (Test-Path -LiteralPath $statePath -PathType Leaf) {
        try { $previous = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json } catch { }
    }
    $backupRelative = $null
    if ($previous -and $previous.installed -and $previous.original_backup_relative) {
        $candidate = Join-Path $root $previous.original_backup_relative
        if ((Test-Path -LiteralPath $candidate -PathType Leaf) -and ((Get-Sha256 $candidate) -eq $previous.original_sha256)) { $backupRelative = $previous.original_backup_relative }
    }
    if (-not $backupRelative) {
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $backupRelative = "$script:BackupFolderName\original-$stamp\$([IO.Path]::GetFileName($target))"
        $backup = Join-Path $root $backupRelative
        New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
        Copy-Item -LiteralPath $target -Destination $backup -ErrorAction Stop
    }
    $backup = Join-Path $root $backupRelative
    $backupHash = Get-Sha256 $backup

    $temporaryOutput = Join-Path (Split-Path -Parent $target) ('.' + [IO.Path]::GetFileName($target) + '.ptbr-' + [guid]::NewGuid().ToString('N') + '.tmp')
    $oldLibraryDirectory = $env:UABEA_LIB_DIR
    try {
        $env:UABEA_LIB_DIR = $libraries
        & dotnet exec --runtimeconfig $runtimeConfig $bridge $target $raw "$script:PathId" $temporaryOutput
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $temporaryOutput -PathType Leaf)) { throw "O aplicador UABEA falhou (codigo $LASTEXITCODE)." }
        if ((Get-Item -LiteralPath $temporaryOutput).Length -le 1048576) { throw 'O aplicador produziu um bundle invalido.' }
        try { [IO.File]::Replace($temporaryOutput, $target, $null, $true) }
        catch { Copy-Item -LiteralPath $temporaryOutput -Destination $target -Force; Remove-Item -LiteralPath $temporaryOutput -Force -ErrorAction SilentlyContinue }
    } finally {
        if ($null -eq $oldLibraryDirectory) { Remove-Item Env:UABEA_LIB_DIR -ErrorAction SilentlyContinue } else { $env:UABEA_LIB_DIR = $oldLibraryDirectory }
        if (Test-Path -LiteralPath $temporaryOutput -PathType Leaf) { Remove-Item -LiteralPath $temporaryOutput -Force -ErrorAction SilentlyContinue }
    }
    $state = @{ schema = 1; installed = $true; version = [string]$manifest.version; installed_at = (Get-Date).ToString('o'); game_root = $root; bundle_relative = $script:BundleRelative; original_backup_relative = $backupRelative; original_sha256 = $backupHash; installed_sha256 = (Get-Sha256 $target) }
    Write-State $backupRoot $state
    Write-Host ''
    Write-Host 'PT-BR instalado com sucesso.' -ForegroundColor Green
    Write-Host "Backup original: $backup"
    Write-Host 'No jogo, selecione o idioma English.' -ForegroundColor Green
} catch {
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
