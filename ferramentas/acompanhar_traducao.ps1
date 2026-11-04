param(
    [switch]$Watch,
    [int]$IntervalSeconds = 10
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$catalog = Join-Path $root 'texto\catalogo\pt-BR.csv'

function Show-TranslationStatus {
    $rows = Import-Csv -LiteralPath $catalog
    $total = $rows.Count
    $filled = @($rows | Where-Object { $_.pt_br }).Count
    $machine = @($rows | Where-Object { $_.status -eq 'machine-draft' }).Count
    $manual = @($rows | Where-Object { $_.status -eq 'draft' }).Count
    $remaining = $total - $filled
    $distinctTotal = @($rows.en | Select-Object -Unique).Count
    $distinctFilled = @($rows | Where-Object { $_.pt_br } | Select-Object -ExpandProperty en -Unique).Count
    $worker = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
        Where-Object { $_.CommandLine -match 'traduzir_restante_argos.py' } |
        Select-Object -First 1

    Write-Host "Catalogo PT-BR" -ForegroundColor Cyan
    Write-Host "  Ocorrencias: $filled / $total ($(if($total){[math]::Round(100*$filled/$total,2)}else{0})%) | faltam $remaining"
    Write-Host "  Textos distintos: $distinctFilled / $distinctTotal | faltam $($distinctTotal-$distinctFilled)"
    Write-Host "  Manual: $manual | automatico: $machine"
    if ($worker) {
        $process = Get-Process -Id $worker.ProcessId
        $elapsed = (Get-Date) - $process.StartTime
        Write-Host "  Tradutor: ATIVO (PID $($process.Id), ha $($elapsed.ToString('hh\:mm\:ss')), $([math]::Round($process.WS/1MB)) MiB)" -ForegroundColor Yellow
        if ($machine -eq 0) {
            Write-Host "  Aviso: esta execucao antiga grava o catalogo apenas ao final; o progresso exato ainda nao esta disponivel." -ForegroundColor DarkYellow
        }
    } else {
        Write-Host "  Tradutor: parado ou concluido" -ForegroundColor Green
    }
    Write-Host "  Atualizado: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

do {
    if ($Watch) { Clear-Host }
    Show-TranslationStatus
    if ($Watch) { Start-Sleep -Seconds $IntervalSeconds }
} while ($Watch)
