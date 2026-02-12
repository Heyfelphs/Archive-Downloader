# Build script for Archive Downloader
# Creates optimized Windows executable

# Read version
$version = Get-Content "VERSION" -Raw
$version = $version.Trim()

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Archive Downloader v$version - Build Script" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
Write-Host "[1/4] Ativando ambiente virtual..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Clean previous builds
Write-Host "[2/4] Limpando builds anteriores..." -ForegroundColor Yellow
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
    Write-Host "  - Pasta 'build' removida" -ForegroundColor Gray
}
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
    Write-Host "  - Pasta 'dist' removida" -ForegroundColor Gray
}

# Run PyInstaller
Write-Host "[3/4] Compilando executável..." -ForegroundColor Yellow
Write-Host "  Isso pode levar alguns minutos..." -ForegroundColor Gray
pyinstaller archive_downloader.spec --clean --noconfirm

# Check if build was successful
if (Test-Path "dist\ArchiveDownloader.exe") {
    Write-Host "[4/4] Build concluído com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host "  Executável criado em:" -ForegroundColor Green
    Write-Host "  dist\ArchiveDownloader.exe" -ForegroundColor White
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Show file size
    $fileSize = (Get-Item "dist\ArchiveDownloader.exe").Length / 1MB
    Write-Host "  Tamanho: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "[ERRO] Falha ao criar executável!" -ForegroundColor Red
    Write-Host "Verifique os logs acima para detalhes." -ForegroundColor Red
    exit 1
}
