# 📦 Archive Downloader

**Archive Downloader** é um aplicativo desktop moderno desenvolvido em Python para download automatizado de arquivos multimídia de sites como Fapello e Picazor. Com uma interface gráfica intuitiva construída em PySide6 (Qt6), oferece controle total sobre o processo de download com recursos avançados de otimização e personalização.

## ✨ Funcionalidades

### Downloads Inteligentes
- 🚀 **Download paralelo otimizado** com thread pools configurados para máxima performance
- 🌐 **Suporte multi-site**: Fapello e Picazor
- 📊 **Barra de progresso em tempo real** com estimativa de tempo
- 🖼️ **Visualização de miniaturas** durante o download (limite de 12 thumbnails)
- ⏸️ **Controle de pausar/retomar** downloads
- 📝 **Log detalhado** de todas as operações

### Interface Moderna
- 🎨 **Temas claro e escuro** com transição suave
- ✨ **Animações fluidas** (fade-in de thumbnails)
- 🎯 **Interface responsiva** com atualizações throttled
- 💾 **Persistência de estado** (tema, configurações de batch)

### Otimização de Performance
- ⚡ **Configurações fixas otimizadas** via benchmarking automatizado:
  - Fapello: 3 threads, 512KB chunks
  - Picazor: 4 threads, 256KB chunks, delay 0.1s
- 📦 **Batch downloading configurável** para Picazor
- 🔄 **Throttling inteligente** de atualizações de UI (120ms)
- 🎲 **Chunk size otimizado** para melhor velocidade

## 🛠️ Tecnologias

- **Python 3.13+**
- **PySide6 (Qt6)** - Interface gráfica moderna
- **aiohttp** - Requisições HTTP assíncronas
- **BeautifulSoup4** - Parse de HTML
- **Pillow** - Processamento de imagens
- **asyncio** - Operações assíncronas

## 📁 Estrutura do Projeto
```
Archive-Downloader/
├── app.py                      # Inicialização da aplicação
├── main.py                     # Ponto de entrada principal
├── config.py                   # Constantes e configurações
├── requirements.txt            # Dependências do projeto
├── ui_state.json               # Persistência de estado da UI
├── core/
│   ├── downloader_progress.py  # Sistema de progresso de download
│   ├── fapello_client.py       # Client para Fapello
│   ├── picazor_client.py       # Client para Picazor
│   ├── picazor_downloader.py   # Downloader Picazor otimizado
│   ├── worker.py               # Worker threads
│   └── services/
│       └── download_service.py # Orquestração de downloads
├── ui/
│   ├── widgets.py              # Widgets personalizados e temas
│   ├── window.py               # Janela principal
│   ├── workers.py              # Qt Workers (fetch/download/thumbnail)
│   └── link_utils.py           # Utilitários de links
├── utils/
│   ├── filesystem.py           # Operações de arquivo
│   └── network.py              # Utilitários de rede
└── tools/
    └── benchmark_download.py   # Script de benchmarking
```

## 🚀 Instalação

### Pré-requisitos
- Python 3.13+ (recomendado)
- pip (gerenciador de pacotes Python)
- Sistema operacional: Windows, macOS ou Linux

### Passo a Passo

1. **Clone o repositório**
   ```bash
   git clone <repository-url>
   cd Archive-Downloader
   ```

2. **Crie um ambiente virtual** (recomendado)
   ```bash
   python -m venv .venv
   ```

3. **Ative o ambiente virtual**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```

4. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

5. **Execute o aplicativo**
   ```bash
   python main.py
   ```

## 📖 Como Usar

1. **Cole o link** do perfil/álbum na caixa de entrada
2. **Selecione o site** (Fapello ou Picazor)
3. **Clique em "Fetch"** para buscar os itens disponíveis
4. **Visualize as miniaturas** que aparecem durante o fetch
5. **Clique em "Download"** para iniciar o download
6. **Acompanhe o progresso** na barra e nos logs
7. **Altere o tema** no seletor no rodapé (claro/escuro)

### Configurações Avançadas

- **Picazor Batch Check**: Controle quantos itens são verificados por vez (padrão: 30)
- **Tema**: Escolha entre claro e escuro no rodapé
- As configurações de threads e chunk size são **otimizadas e fixas** no código

## ⚙️ Configurações Otimizadas

O aplicativo usa configurações fixas otimizadas via benchmarking automatizado:

| Site     | Threads | Chunk Size | Delay | Batch |
|----------|---------|------------|-------|-------|
| Fapello  | 3       | 512 KB     | N/A   | N/A   |
| Picazor  | 4       | 256 KB     | 0.1s  | 30    |

Essas configurações foram determinadas através de 30 testes automatizados para garantir a melhor performance.

## 🧪 Benchmarking

Para executar seus próprios benchmarks:

```bash
python tools/benchmark_download.py --fapello <url> --picazor <url> --max-items 30 --output ./benchmarks
```

Os resultados serão salvos em `benchmarks/results.csv`.

## 📊 Características Técnicas

- **Arquitetura modular** com separação clara de responsabilidades
- **Download assíncrono** com controle de concorrência
- **Sistema de progresso robusto** com callbacks throttled
- **Gerenciamento de memória eficiente** com limite de thumbnails
- **Persistência de estado** em JSON
- **Animações suaves** com QPropertyAnimation
- **Throttling de UI** para evitar congelamentos
- **Log em tempo real** com buffering otimizado

## 🐛 Solução de Problemas

### Erro de conexão
- Verifique sua conexão com a internet
- Alguns sites podem ter proteção anti-bot; aguarde alguns minutos

### Download lento
- As configurações já estão otimizadas
- Verifique sua velocidade de internet
- Alguns sites limitam a taxa de download

### Aplicativo não abre
- Certifique-se de que instalou todas as dependências
- Verifique se está usando Python 3.13+
- Execute em modo debug: `python main.py` e observe os erros

## 📝 Licença

Este projeto está sob uma **Licença Proprietária de Uso Pessoal**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

**Resumo**: Você pode usar este software apenas para fins pessoais. Redistribuição, modificação e uso comercial são proibidos.

## 👤 Autor

Desenvolvido com ❤️ para facilitar o gerenciamento de downloads de arquivos multimídia.

---

**Nota**: Este software é fornecido "como está", sem garantias. Use por sua conta e risco e respeite os termos de serviço dos sites que você acessa.
