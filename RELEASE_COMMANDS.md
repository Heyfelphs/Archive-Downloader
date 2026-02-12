# Quick Release Commands

## Preparar Release v1.0.0

### 1. Verificar que está tudo commitado
```bash
git status
```

### 2. Criar build
```powershell
.\build.ps1
```

### 3. Testar executável
```powershell
.\dist\ArchiveDownloader.exe
```

### 4. Commitar arquivos de release
```bash
git add .
git commit -m "Release v1.0.0"
```

### 5. Criar tag
```bash
git tag -a v1.0.0 -m "Release v1.0.0 - Initial Release"
```

### 6. Push para repositório
```bash
git push origin main
git push origin v1.0.0
```

### 7. Criar Release no GitHub

1. Vá para: `https://github.com/SEU_USUARIO/Archive-Downloader/releases/new`
2. Selecione a tag: `v1.0.0`
3. Release title: `Archive Downloader v1.0.0`
4. Copie o conteúdo de `.github/RELEASE_TEMPLATE.md` na descrição
5. Faça upload de: `dist/ArchiveDownloader.exe`
6. Clique em "Publish release"

## Futuras Releases

### Patch (v1.0.1, v1.0.2...)
Para bug fixes:
```bash
# Atualizar VERSION
echo "1.0.1" > VERSION

# Commit
git add VERSION CHANGELOG.md
git commit -m "Bump version to 1.0.1"

# Tag e push
git tag -a v1.0.1 -m "Release v1.0.1 - Bug fixes"
git push origin main
git push origin v1.0.1
```

### Minor (v1.1.0, v1.2.0...)
Para novas features:
```bash
# Atualizar VERSION
echo "1.1.0" > VERSION

# Commit
git add VERSION CHANGELOG.md
git commit -m "Bump version to 1.1.0"

# Tag e push
git tag -a v1.1.0 -m "Release v1.1.0 - New features"
git push origin main
git push origin v1.1.0
```

### Major (v2.0.0, v3.0.0...)
Para breaking changes:
```bash
# Atualizar VERSION
echo "2.0.0" > VERSION

# Commit
git add VERSION CHANGELOG.md
git commit -m "Bump version to 2.0.0"

# Tag e push
git tag -a v2.0.0 -m "Release v2.0.0 - Major update"
git push origin main
git push origin v2.0.0
```

## Checklist Pré-Release

- [ ] Todos os testes passando (`pytest`)
- [ ] CHANGELOG.md atualizado
- [ ] VERSION atualizado
- [ ] Build testado (`.\build.ps1`)
- [ ] Executável testado manualmente
- [ ] README atualizado (se necessário)
- [ ] Commits limpos e descritivos
- [ ] Branch main está atualizado

## Dicas

### Deletar tag (se errou)
```bash
# Local
git tag -d v1.0.0

# Remoto
git push --delete origin v1.0.0
```

### Ver todas as tags
```bash
git tag -l
```

### Ver diferenças entre tags
```bash
git diff v1.0.0 v1.1.0
```

### Criar Release Draft
No GitHub, marque "This is a pre-release" para releases beta/alpha.
