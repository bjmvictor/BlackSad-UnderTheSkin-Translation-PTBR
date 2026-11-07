[CmdletBinding()]
param(
    [string] $PastaJogo,
    [switch] $SemConfirmacao
)

$ErrorActionPreference = 'Stop'
$script:BundleRelative = 'Blacksad_Data\StreamingAssets\assets_data\2172dc1d-d264-45aa-a94c-231bf3de6baa'
$script:BackupFolderName = 'Blacksad_PTBR_Backup'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($PastaJogo) { $arguments += " -PastaJogo `"$PastaJogo`"" }
    if ($SemConfirmacao) { $arguments += ' -SemConfirmacao' }
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $arguments
    exit
}

function Get-Sha256([string] $Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Resolve-GameRoot([string] $Candidate) {
    if ([string]::IsNullOrWhiteSpace($Candidate) -or -not (Test-Path -LiteralPath $Candidate)) { return $null }
    $item = Get-Item -LiteralPath $Candidate
    $root = if ($item.PSIsContainer) { $item.FullName } elseif ($item.Name -ieq 'Blacksad.exe') { $item.Directory.FullName } else { return $null }
    if ((Test-Path -LiteralPath (Join-Path $root 'Blacksad.exe') -PathType Leaf) -and (Test-Path -LiteralPath (Join-Path $root $script:BundleRelative) -PathType Leaf)) { return (Resolve-Path -LiteralPath $root).Path }
    return $null
}
function Get-DetectedGameRoots {
    $steamRoots = @('C:\Program Files (x86)\Steam', 'C:\Program Files\Steam') | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
    try { $steamRoots += (Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -Name SteamPath -ErrorAction Stop).SteamPath } catch { }
    $libraries = [System.Collections.Generic.List[string]]::new()
    foreach ($steam in ($steamRoots | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $steam -PathType Container)) { continue }
        $libraries.Add($steam)
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf -PathType Leaf) {
            foreach ($match in [regex]::Matches((Get-Content -LiteralPath $vdf -Raw), '"path"\s+"([^"]+)"', [Text.RegularExpressions.RegexOptions]::IgnoreCase)) { $libraries.Add($match.Groups[1].Value.Replace('\\', '\')) }
        }
    }
    $result = foreach ($library in ($libraries | Select-Object -Unique)) {
        $manifest = Join-Path $library 'steamapps\appmanifest_1003890.acf'
        if (Test-Path -LiteralPath $manifest -PathType Leaf) {
            $match = [regex]::Match((Get-Content -LiteralPath $manifest -Raw), '"installdir"\s+"([^"]+)"', [Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if ($match.Success) { Resolve-GameRoot (Join-Path $library ('steamapps\common\' + $match.Groups[1].Value)) }
        }
    }
    return @($result | Where-Object { $_ } | Select-Object -Unique)
}
function Select-GameRoot([string] $RequestedPath) {
    $provided = Resolve-GameRoot $RequestedPath
    if ($provided) { return $provided }
    if ($RequestedPath) { throw "A pasta informada nao contem Blacksad.exe e o bundle esperado: $RequestedPath" }
    $found = @(Get-DetectedGameRoots)
    if ($found.Count -eq 1) { Write-Host "Jogo localizado: $($found[0])" -ForegroundColor Cyan; return $found[0] }
    if ($found.Count -gt 1) {
        for ($index = 0; $index -lt $found.Count; $index++) { Write-Host "[$($index + 1)] $($found[$index])" }
        $answer = Read-Host 'Digite o numero da instalacao ou deixe vazio para escolher uma pasta'; $number = 0
        if ([int]::TryParse($answer, [ref]$number) -and $number -ge 1 -and $number -le $found.Count) { return $found[$number - 1] }
    }
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = [System.Windows.Forms.FolderBrowserDialog]::new(); $dialog.Description = 'Selecione a pasta que contem Blacksad.exe'
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $selected = Resolve-GameRoot $dialog.SelectedPath; if ($selected) { return $selected } }
    throw 'Nenhuma instalacao valida do Blacksad foi selecionada.'
}
function Confirm([string] $Question, [switch] $Skip) { if (-not $Skip -and (Read-Host "$Question [s/N]") -notmatch '^(s|sim|y|yes)$') { throw 'Operacao cancelada.' } }
function Write-State([string] $BackupRoot, [hashtable] $State) {
    $temporary = Join-Path $BackupRoot ('.instalacao-' + [guid]::NewGuid().ToString('N') + '.tmp'); $statePath = Join-Path $BackupRoot 'instalacao.json'
    $State | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $temporary -Encoding UTF8; Move-Item -LiteralPath $temporary -Destination $statePath -Force
}

try {
    $root = Select-GameRoot $PastaJogo
    if (Get-Process -Name 'Blacksad' -ErrorAction SilentlyContinue) { throw 'Feche Blacksad antes de desinstalar a traducao.' }
    $target = Join-Path $root $script:BundleRelative
    $backupRoot = Join-Path $root $script:BackupFolderName
    $statePath = Join-Path $backupRoot 'instalacao.json'
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) { throw 'Nenhuma instalacao PT-BR controlada por este pacote foi encontrada.' }
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if (-not $state.installed -or -not $state.original_backup_relative) { throw 'A traducao ja foi removida ou o estado do instalador esta invalido.' }
    $backup = Join-Path $root $state.original_backup_relative
    $expectedPrefix = (Resolve-Path -LiteralPath $backupRoot).Path + [IO.Path]::DirectorySeparatorChar
    if (-not (Test-Path -LiteralPath $backup -PathType Leaf) -or -not ((Resolve-Path -LiteralPath $backup).Path).StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'O backup original nao esta disponivel dentro da pasta segura do instalador.' }
    if ((Get-Sha256 $backup) -ne $state.original_sha256) { throw 'O backup original esta corrompido; a desinstalacao foi bloqueada.' }
    Confirm "Restaurar o bundle original em '$root'? Os saves nao serao alterados." $SemConfirmacao
    $temporary = Join-Path (Split-Path -Parent $target) ('.' + [IO.Path]::GetFileName($target) + '.restore-' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        Copy-Item -LiteralPath $backup -Destination $temporary -ErrorAction Stop
        try { [IO.File]::Replace($temporary, $target, $null, $true) }
        catch { Copy-Item -LiteralPath $temporary -Destination $target -Force; Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
    } finally { if (Test-Path -LiteralPath $temporary -PathType Leaf) { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue } }
    $newState = @{ schema = 1; installed = $false; version = $state.version; game_root = $root; original_backup_relative = $state.original_backup_relative; original_sha256 = $state.original_sha256; uninstalled_at = (Get-Date).ToString('o') }
    Write-State $backupRoot $newState
    Write-Host 'PT-BR removido e bundle original restaurado.' -ForegroundColor Green
    Write-Host "O backup foi mantido em: $backup"
} catch {
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
