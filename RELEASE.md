# Release Guide - Archive Downloader

## Preparação para Release

### 1. Pré-requisitos
- Python 3.13+ instalado
- Ambiente virtual ativado
- Todas as dependências instaladas (`pip install -r requirements.txt`)
- PyInstaller instalado (`pip install pyinstaller`)

### 2. Build do Executável

#### Opção A: Script Automatizado (Recomendado)
```powershell
.\build.ps1
```

#### Opção B: Manual
```powershell
# Limpar builds anteriores
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# Criar executável
pyinstaller archive_downloader.spec --clean --noconfirm
```

### 3. Resultado
O executável será gerado em:
```
dist\ArchiveDownloader.exe
```

### 4. Teste do Executável
Antes de distribuir, teste o executável:
1. Execute `dist\ArchiveDownloader.exe` diretamente
2. Teste todas as funcionalidades principais:
   - [ ] Adicionar links de download
   - [ ] Checar arquivos disponíveis
   - [ ] Fazer download de arquivos
   - [ ] Verificar progress bar e status
   - [ ] Testar tema claro/escuro
   - [ ] Verificar logs

### 5. Criando um Release no GitHub

#### Passo 1: Tag da versão
```bash
git tag -a v1.0.0 -m "Release v1.0.0 - Initial Release"
git push origin v1.0.0
```

#### Passo 2: Criar Release
1. Vá para o repositório no GitHub
2. Clique em "Releases" → "Create a new release"
3. Selecione a tag `v1.0.0`
4. Título: `Archive Downloader v1.0.0`
5. Descrição: Use o template abaixo
6. Faça upload do executável `ArchiveDownloader.exe`
7. Publique o release

### Template de Release Notes

```markdown
# Archive Downloader v1.0.0

## 🎉 First Release

Archive Downloader é uma aplicação desktop para Windows que permite baixar arquivos de sites de arquivos como Fapello e Picazor.

## ✨ Features

- 🔗 Suporte para Fapello e Picazor
- 📊 Barra de progresso em tempo real
- 🎨 Tema claro e escuro
- 📁 Organização automática de arquivos
- 🖼️ Geração de thumbnails para vídeos
- 🔄 Download paralelo com múltiplas threads
- ⚡ Cache e otimizações de performance

## 📦 Download

Baixe o executável standalone:
- **Windows**: [ArchiveDownloader.exe](link-aqui)

Não requer instalação, apenas execute o arquivo .exe

## 🚀 Como Usar

1. Baixe e execute `ArchiveDownloader.exe`
2. Adicione URLs na caixa de texto (uma por linha)
3. Clique em "Checar" para buscar arquivos disponíveis
4. Clique em "Baixar" para iniciar o download
5. Os arquivos serão salvos em `C:\Users\SeuUsuario\Downloads\ArchiveDownloads`

## 📋 Requisitos

- Windows 10/11 (64-bit)
- Conexão com a internet

## 🐛 Issues Conhecidas

Nenhuma no momento. Reporte bugs na aba Issues.

## 📝 Changelog

### v1.0.0 (2026-02-12)
- ✨ Release inicial
- 🎨 Interface gráfica com PySide6
- 📊 Sistema de progresso e status
- 🔧 Download resiliente com retry automático
- 🧪 Suite de testes com pytest
```

## 6. Otimizações Opcionais

### Reduzir Tamanho do Executável
Se o .exe estiver muito grande, você pode:

1. **Usar UPX** (compressão já está habilitada no .spec)

2. **Build sem debug**:
   Já configurado em `archive_downloader.spec` com `debug=False`

3. **Excluir mais módulos**:
   Edite `archive_downloader.spec` e adicione mais módulos em `excludes`

### Adicionar Ícone
1. Crie ou obtenha um arquivo `icon.ico`
2. Coloque na raiz do projeto
3. Edite `archive_downloader.spec`:
   ```python
   icon='icon.ico'
   ```

### Variante com Console (para debug)
Crie `archive_downloader_debug.spec`:
```python
console=True,  # Altera de False para True
```

## 7. Distribuição

### Upload Manual
- Anexe o .exe ao Release do GitHub
- Compartilhe o link direto

### Alternativas
- **Distribuição por Installer**: Use Inno Setup ou NSIS
- **Portable ZIP**: Compacte o .exe em um arquivo ZIP
- **Code Signing**: Considere assinar o executável para evitar avisos do Windows

## 8. Checklist Final

Antes de publicar:
- [ ] Executável testado em máquina limpa
- [ ] README atualizado com links de download
- [ ] Tag da versão criada no Git
- [ ] Release notes escritas
- [ ] Screenshots/GIFs preparados (opcional)
- [ ] CHANGELOG atualizado

## 9. Troubleshooting

### Erro: "PySide6 not found"
- Reinstale: `pip install --force-reinstall PySide6`

### Executável muito grande
- Revise `excludes` no .spec
- Considere build `onedir` ao invés de `onefile`

### Antivírus bloqueia o .exe
- Normal para executáveis não assinados
- Considere code signing para releases oficiais

### Import errors no executável
- Adicione módulos faltantes em `hiddenimports` no .spec
- Use `pyinstaller --debug=all` para diagnóstico
