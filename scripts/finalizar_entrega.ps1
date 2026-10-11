# Fecha a entrega da Fase 2: carga no Aiven -> evidências -> documento DOCX/PDF em Downloads.
#
# Uso (na raiz do projeto, depois de colar a Service URI do Aiven no .env):
#   powershell -ExecutionPolicy Bypass -File scripts\finalizar_entrega.ps1 -Repo https://github.com/<usuario>/<repo>
#   ... -SoDocumento   regenera só o documento (ex.: para trocar o link do repositório)
param(
    [string]$Repo = "",
    [switch]$SoDocumento
)
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
$saida = Join-Path $env:USERPROFILE "Downloads\Entrega_Fase2_Gustavo_Souza_Santos"

# Python: o .venv\Scripts\python.exe é bloqueado pelo Smart App Control nesta máquina,
# então usamos o interpretador do uv com os pacotes do .venv.
$py = Join-Path $env:APPDATA "uv\python\cpython-3.12.14-windows-x86_64-none\python.exe"
if (-not (Test-Path $py)) { $py = ".\.venv\Scripts\python.exe" }
$env:PYTHONPATH = Join-Path $raiz ".venv\Lib\site-packages"
$env:PYTHONIOENCODING = "utf-8"

if (-not $SoDocumento) {
    if (-not (Test-Path ".env")) { throw "Crie o .env (copie o .env.example) e cole a Service URI do Aiven em DATABASE_URL." }
    $linha = Select-String -Path ".env" -Pattern "^DATABASE_URL=" | Select-Object -First 1
    if ($null -eq $linha -or $linha.Line -match "SENHA@") { throw "DATABASE_URL no .env ainda é o exemplo. Cole a Service URI do Aiven." }
    if ($linha.Line -notmatch "sslmode=require") { throw "A Service URI precisa terminar com ?sslmode=require." }
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue   # garante que vale o .env

    Write-Host "1/3 Carga no Aiven (leva ~25 min: lê 6 XLSX e 9 milhões de óbitos)"
    & $py run_pipeline.py --sem-download
    if ($LASTEXITCODE -ne 0) { throw "run_pipeline.py falhou" }

    Write-Host "2/3 Evidências (sql/03_verificacao.sql)"
    & $py -m scripts.verificar_banco
    if ($LASTEXITCODE -ne 0) { throw "verificar_banco falhou" }
}

Write-Host "3/3 Documento"
New-Item -ItemType Directory -Force $saida | Out-Null
node docs\entrega\gerar.js $saida $Repo
if ($LASTEXITCODE -ne 0) { throw "gerar.js falhou" }
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
$html = Join-Path $saida "Entrega_Fase2_Gustavo_Souza_Santos.html"
$pdf = Join-Path $saida "Entrega_Fase2_Gustavo_Souza_Santos.pdf"
& $edge --headless=new --disable-gpu --no-pdf-header-footer "--print-to-pdf=$pdf" ("file:///" + ($html -replace "\\", "/")) | Out-Null
Start-Sleep -Seconds 3
Remove-Item $html -ErrorAction SilentlyContinue
$evid = Join-Path $saida "evidencias"
New-Item -ItemType Directory -Force $evid | Out-Null
Copy-Item docs\relatorio_tratamento.md, docs\verificacao_banco.md, docs\impacto_duplicatas.csv, docs\entrega\diagrama_estrela.png, data\raw\manifest.json $evid -Force
# código versionado (sem .env nem brutos): o que está no último commit
git archive --format=zip -o (Join-Path $saida "codigo_fase2_etl.zip") HEAD
Write-Host "Pronto: $saida"
