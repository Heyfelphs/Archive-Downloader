# 🎉 Archive Downloader v1.0.0

## First Official Release!

Archive Downloader é uma aplicação desktop profissional para Windows que permite baixar arquivos de sites de arquivo como **Fapello** e **Picazor** com facilidade e controle total.

---

## ✨ Principais Funcionalidades

### 🚀 Performance Otimizada
- **Download paralelo inteligente** com configurações específicas por site
- **Fapello**: 3 threads, chunks de 512KB
- **Picazor**: 4 threads, chunks de 256KB com delay
- **Streaming** de downloads para arquivos grandes

### 🎨 Interface Moderna
- Interface gráfica moderna com **PySide6 (Qt6)**
- **Temas claro e escuro** com transição suave
- **Barra de progresso** em tempo real com percentual
- **Miniaturas de vídeos** geradas automaticamente
- **Logs detalhados** de todas as operações

### 🛡️ Confiabilidade
- **Retry automático** em caso de falhas
- **Sessões HTTP thread-safe** para estabilidade
- **Validação robusta** de arquivos e URLs
- **Tratamento de erros** abrangente

### 💾 Gerenciamento
- Downloads organizados por site e perfil
- Persistência de configurações (tema, batch size)
- Verificação de arquivos existentes (evita re-download)
- Logs salvos para auditoria

---

## 📦 Download

### Opção 1: Executável Standalone (Recomendado)
Baixe apenas o arquivo EXE e execute. Não precisa instalar Python ou dependências!

**➡️ [ArchiveDownloader.exe](https://github.com/yourusername/Archive-Downloader/releases/download/v1.0.0/ArchiveDownloader.exe)** (~93 MB)

✅ Não requer instalação  
✅ Não requer Python  
✅ Pronto para usar

### Opção 2: Código Fonte
Se preferir executar via Python ou contribuir com o projeto:

```bash
git clone https://github.com/yourusername/Archive-Downloader.git
cd Archive-Downloader
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 🎯 Como Usar

1. **Execute** `ArchiveDownloader.exe`
2. **Cole o link** do perfil/álbum na caixa de texto
3. **Selecione o site** (Fapello ou Picazor)
4. **Clique em "Checar"** para buscar arquivos disponíveis
5. **Clique em "Baixar"** para iniciar o download
6. **Acompanhe o progresso** e miniaturas na interface
7. **Arquivos salvos em**: `C:\Users\SeuUsuario\Downloads\ArchiveDownloads\`

### ⚙️ Configurações
- **Tema**: Alterne entre claro/escuro no seletor inferior
- **Batch Picazor**: Ajuste quantos itens verificar por vez (padrão: 30)

---

## 📋 Requisitos de Sistema

- **Sistema Operacional**: Windows 10/11 (64-bit)
- **Memória RAM**: 4GB mínimo, 8GB recomendado
- **Espaço em Disco**: 100MB para aplicação + espaço para downloads
- **Internet**: Conexão estável necessária

---

## 🔧 Stack Tecnológica

- **Python 3.13.12**
- **PySide6** - Interface Qt6 moderna
- **requests** - HTTP com retry automático
- **cloudscraper** - Bypass de proteções JavaScript
- **BeautifulSoup4** - Parser HTML
- **opencv-python** - Processamento de vídeo
- **PyInstaller** - Empacotamento em executável

---

## 🧪 Qualidade

✅ **6 testes automatizados** com pytest  
✅ **100% dos testes passando**  
✅ **Cobertura de funcionalidades críticas**

Testes cobrem:
- Preparação de nomes de arquivo
- Isolamento de sessões thread-local
- Resolução de URLs de mídia
- Downloads streaming
- Orquestração completa de downloads

---

## 📚 Documentação

- [README.md](https://github.com/yourusername/Archive-Downloader/blob/main/README.md) - Guia completo do usuário
- [RELEASE.md](https://github.com/yourusername/Archive-Downloader/blob/main/RELEASE.md) - Guia técnico de releases
- [CHANGELOG.md](https://github.com/yourusername/Archive-Downloader/blob/main/CHANGELOG.md) - Histórico de mudanças

---

## 🐛 Problemas Conhecidos

Nenhum no momento! 

Se encontrar bugs, por favor [abra uma issue](https://github.com/yourusername/Archive-Downloader/issues/new).

---

## 🙏 Agradecimentos

Obrigado a todos que testaram e forneceram feedback durante o desenvolvimento!

---

## 📜 Licença

Este projeto está sob a licença especificada no arquivo [LICENSE](https://github.com/yourusername/Archive-Downloader/blob/main/LICENSE).

---

## 🔐 Nota de Segurança

**Aviso do Windows Defender**: Como este executável não possui assinatura digital (code signing certificate), o Windows pode exibir um aviso de segurança. Isso é normal para executáveis não assinados. Você pode verificar o código-fonte e compilar você mesmo se preferir.

---

## 📊 Estatísticas desta Release

- **105 commits** até esta versão
- **6 testes automatizados**
- **~93 MB** tamanho do executável
- **4 sites** suportados (Fapello e Picazor em múltiplas regiões)

---

**Aproveite o Archive Downloader! 🎉**

Se você gostou do projeto, considere dar uma ⭐ no repositório!
