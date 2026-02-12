# Build Troubleshooting

## Issue: "No module named 'email'" Error

### Problema
Ao executar o `.exe` gerado pelo PyInstaller, ocorria o erro:
```
ModuleNotFoundError: No module named 'email'
```

### Causa
O módulo `email` estava na lista de `excludes` no arquivo `.spec`, impedindo sua inclusão no executável. O módulo `requests` depende de `email` e outros módulos nativos do Python para funcionar.

### Solução
1. **Remover `email` da lista de excludes**
2. **Adicionar módulos necessários aos hiddenimports**:
   ```python
   hiddenimports=[
       # ... outros módulos
       'email',
       'email.mime',
       'email.mime.text',
       'email.mime.multipart',
       'http.cookiejar',
       'http.client',
   ]
   ```

### Aplicado em
- Commit: `[será preenchido após commit]`
- Arquivo: `archive_downloader.spec`
- Versão: 1.0.0

---

## Outros Problemas Comuns

### Windows Defender / Antivírus Bloqueia o .exe

**Causa**: Executáveis não assinados são sinalizados como suspeitos.

**Soluções**:
1. Adicione exceção no Windows Defender
2. Para distribuição profissional, considere code signing
3. Distribua também via código fonte para usuários técnicos

### Executável Muito Grande (~93 MB)

**Causa**: PyInstaller embute Python, Qt, OpenCV e todas as dependências.

**Soluções para reduzir tamanho**:
1. Use `onedir` ao invés de `onefile` (mais rápido, mas múltiplos arquivos)
2. Adicione mais módulos aos `excludes` (cuidado para não quebrar)
3. Use UPX para compressão (já habilitado)
4. Considere alternativas como PyOxidizer ou Nuitka

### Erro "Failed to execute script"

**Possíveis causas**:
1. Módulo faltando nos hiddenimports
2. Arquivo de dados (data files) não incluído
3. DLL faltando

**Debug**:
1. Execute com console habilitado:
   ```python
   console=True,  # no .spec
   ```
2. Use `--debug=all` no PyInstaller
3. Verifique logs em `build/archive_downloader/warn-*.txt`

### Import Errors de Bibliotecas

**Solução**: Adicione aos hiddenimports no `.spec`

**Exemplo**:
```python
hiddenimports=[
    'nome_do_modulo',
    'nome_do_modulo.submodulo',
]
```

### Qt Platform Plugin Errors

**Erro**: `Could not find the Qt platform plugin "windows"`

**Solução**: Já incluído automaticamente pelo hook do PySide6, mas se ocorrer:
```python
datas=[
    ('path/to/platforms', 'platforms'),
]
```

---

## Checklist de Build

Antes de distribuir um release:

- [ ] Todos os testes passam (`pytest`)
- [ ] Build limpo sem warnings críticos
- [ ] Executável testado em máquina limpa (sem Python instalado)
- [ ] Todas as funcionalidades testadas manualmente
- [ ] Tamanho do .exe aceitável
- [ ] Antivírus não bloqueia excesso (opcional: code signing)
- [ ] Documentação atualizada
- [ ] CHANGELOG atualizado
- [ ] VERSION atualizado
- [ ] Tag Git criada

---

## Recursos Úteis

- [PyInstaller Documentation](https://pyinstaller.org/)
- [PyInstaller Hooks](https://pyinstaller.readthedocs.io/en/stable/hooks.html)
- [PySide6 Deployment](https://doc.qt.io/qtforpython/deployment.html)
- [Code Signing on Windows](https://docs.microsoft.com/en-us/windows/win32/seccrypto/cryptography-tools)
