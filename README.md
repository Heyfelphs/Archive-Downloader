# Archive Downloader

Archive Downloader é um aplicativo Python para baixar arquivos de sites como Fapello e Picazor, com uma interface gráfica intuitiva.

## Funcionalidades
- Download de arquivos de múltiplos sites (Fapello, Picazor)
- Interface gráfica para acompanhamento do progresso
- Gerenciamento de múltiplos downloads simultâneos
- Configuração personalizada via arquivo `config.py`

## Estrutura do Projeto
```
app.py                # Inicialização da aplicação
config.py             # Configurações gerais
main.py               # Ponto de entrada principal
requirements.txt      # Dependências do projeto
test.py               # Testes
ui_state.json         # Estado da interface
core/                 # Lógica de download e clientes
ui/                   # Componentes da interface gráfica
utils/                # Utilitários (filesystem, network, threading)
```

## Como usar
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute o aplicativo:
   ```bash
   python main.py
   ```

## Requisitos
- Python 3.8+
- Bibliotecas listadas em `requirements.txt`

## Contribuição
Pull requests são bem-vindos. Para grandes mudanças, abra uma issue primeiro para discutir o que você gostaria de modificar.

## Licença
Este projeto está sob a licença MIT.
