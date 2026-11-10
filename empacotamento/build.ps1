<#
  Compila o CK Etiquetas: testes -> ícone -> executável (PyInstaller) -> instalador (Inno Setup).

  Uso (na pasta do projeto, em um PowerShell):
      powershell -ExecutionPolicy Bypass -File empacotamento\build.ps1
  Opções:
      -SemTestes       pula o pytest
      -SemInstalador   gera só o executável

  Resultados:
      dist\CKEtiquetas\CKEtiquetas.exe              (programa; copie a pasta inteira)
      dist\instalador\CK_Etiquetas_Setup_v2.0.exe   (instalador)
#>
param([switch]$SemTestes, [switch]$SemInstalador)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

function Passo($texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }

$python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

Passo "Dependências"
& $python -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências." }

if (-not $SemTestes) {
    Passo "Testes automatizados"
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Testes falharam: o executável NÃO foi gerado." }
}

Passo "Ícone multi-resolução a partir do logotipo"
& $python empacotamento\gerar_icone.py
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o ícone." }

Passo "Executável (PyInstaller)"
& $python -m PyInstaller empacotamento\CKEtiquetas.spec --noconfirm --clean --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) { throw "Falha no PyInstaller." }
$exe = Join-Path $raiz "dist\CKEtiquetas\CKEtiquetas.exe"
if (-not (Test-Path $exe)) { throw "Executável não encontrado: $exe" }
Write-Host "OK: $exe"

if ($SemInstalador) { exit 0 }

Passo "Instalador (Inno Setup)"
$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup 6 não encontrado. Instale com:  winget install JRSoftware.InnoSetup"
}
& $iscc empacotamento\CKEtiquetas.iss
if ($LASTEXITCODE -ne 0) { throw "Falha ao compilar o instalador." }
Write-Host "OK: $(Join-Path $raiz 'dist\instalador\CK_Etiquetas_Setup_v2.0.exe')" -ForegroundColor Green
