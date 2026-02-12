# Release Preparation Script
# Automates the release process

param(
    [Parameter(Mandatory=$false)]
    [string]$Version
)

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Archive Downloader - Release Preparation" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Get current version
$currentVersion = Get-Content "VERSION" -Raw
$currentVersion = $currentVersion.Trim()

if (-not $Version) {
    Write-Host "Versão atual: $currentVersion" -ForegroundColor Yellow
    $Version = Read-Host "Digite a nova versão (ex: 1.0.1)"
}

Write-Host ""
Write-Host "[1/7] Atualizando VERSION..." -ForegroundColor Yellow
Set-Content -Path "VERSION" -Value $Version -NoNewline
Write-Host "  ✓ VERSION atualizado para $Version" -ForegroundColor Green

Write-Host ""
Write-Host "[2/7] Verificando Git status..." -ForegroundColor Yellow
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "  ! Arquivos não commitados encontrados:" -ForegroundColor Yellow
    Write-Host $gitStatus -ForegroundColor Gray
    $continue = Read-Host "  Continuar mesmo assim? (s/N)"
    if ($continue -ne "s" -and $continue -ne "S") {
        Write-Host "Operação cancelada." -ForegroundColor Red
        exit 1
    }
}
Write-Host "  ✓ Git status verificado" -ForegroundColor Green

Write-Host ""
Write-Host "[3/7] Rodando testes..." -ForegroundColor Yellow
& .\.venv\Scripts\pytest.exe -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Testes falharam!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Todos os testes passaram" -ForegroundColor Green

Write-Host ""
Write-Host "[4/7] Criando build..." -ForegroundColor Yellow
& .\build.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Build falhou!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Build criado com sucesso" -ForegroundColor Green

Write-Host ""
Write-Host "[5/7] Verificando executável..." -ForegroundColor Yellow
if (-not (Test-Path "dist\ArchiveDownloader.exe")) {
    Write-Host "  ✗ Executável não encontrado!" -ForegroundColor Red
    exit 1
}
$fileSize = (Get-Item "dist\ArchiveDownloader.exe").Length / 1MB
Write-Host "  ✓ Executável verificado ($([math]::Round($fileSize, 2)) MB)" -ForegroundColor Green

Write-Host ""
Write-Host "[6/7] Preparando commit de release..." -ForegroundColor Yellow
Write-Host "  Arquivos modificados:"
Write-Host "  - VERSION" -ForegroundColor Gray
$addMore = Read-Host "  Adicionar CHANGELOG.md também? (S/n)"
if ($addMore -ne "n" -and $addMore -ne "N") {
    git add CHANGELOG.md
    Write-Host "  - CHANGELOG.md" -ForegroundColor Gray
}
git add VERSION

Write-Host ""
Write-Host "[7/7] Próximos passos:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Commit as mudanças:" -ForegroundColor White
Write-Host "     git commit -m ""Release v$Version""" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Crie a tag:" -ForegroundColor White
Write-Host "     git tag -a v$Version -m ""Release v$Version""" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. Push para o repositório:" -ForegroundColor White
Write-Host "     git push origin main" -ForegroundColor Cyan
Write-Host "     git push origin v$Version" -ForegroundColor Cyan
Write-Host ""
Write-Host "  4. Teste o executável:" -ForegroundColor White
Write-Host "     .\dist\ArchiveDownloader.exe" -ForegroundColor Cyan
Write-Host ""
Write-Host "  5. Crie o release no GitHub e faça upload de:" -ForegroundColor White
Write-Host "     dist\ArchiveDownloader.exe" -ForegroundColor Cyan
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Preparação concluída!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$autoCommit = Read-Host "Deseja fazer o commit e tag automaticamente? (s/N)"
if ($autoCommit -eq "s" -or $autoCommit -eq "S") {
    Write-Host ""
    Write-Host "Criando commit..." -ForegroundColor Yellow
    git commit -m "Release v$Version"
    
    Write-Host "Criando tag..." -ForegroundColor Yellow
    git tag -a "v$Version" -m "Release v$Version"
    
    Write-Host ""
    Write-Host "✓ Commit e tag criados!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Para publicar, execute:" -ForegroundColor Yellow
    Write-Host "  git push origin main" -ForegroundColor Cyan
    Write-Host "  git push origin v$Version" -ForegroundColor Cyan
}
