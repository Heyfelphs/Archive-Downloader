# ⚡ Quick Start - Catalog Server Otimizado

## 🚀 Início Rápido (5 minutos)

### 1. Iniciar o Servidor
```bash
python catalog_server.py --port 8008
```

**Output esperado:**
```
╔═══════════════════════════════════════════════════╗
║  Catalog Server - Otimizado                       ║
╠═══════════════════════════════════════════════════╣
║  URL: http://localhost:8008                       ║
║  Models Dir: C:\Users\...\Archive-Downloader      ║
╚═══════════════════════════════════════════════════╝

[INFO] Servidor rodando. Pressione Ctrl+C para parar.
```

### 2. Abrir no Navegador
```
http://localhost:8008
```

### 3. Validar Performance
```bash
# Terminal 2
python test_catalog_performance.py
```

---

## 📊 Endpoints Principais

### Sites
```bash
# Listar todos os sites
curl http://localhost:8008/api/sites
```

**Resposta:**
```json
{
  "sites": [
    {"name": "fapello", "models": 42},
    {"name": "picazor", "models": 18}
  ]
}
```

### Modelos
```bash
# Listar modelos de um site
curl http://localhost:8008/api/models?site=fapello
```

### Detalhes
```bash
# Ver arquivos de um modelo
curl "http://localhost:8008/api/model?site=fapello&model=exemplo"
```

---

## 🔧 Gerenciamento de Cache

### Ver Estatísticas
```bash
curl http://localhost:8008/api/cache_stats
```

**Resposta:**
```json
{
  "models_cache": {
    "size": 12,
    "max_size": 500,
    "ttl": 1800
  },
  "model_info_cache": {
    "size": 45,
    "max_size": 2000,
    "ttl": 1800
  },
  "media_list_cache": {
    "size": 8,
    "max_size": 1000,
    "ttl": 1800
  }
}
```

### Limpar Cache
```bash
curl http://localhost:8008/api/clear_cache
```

**Resposta:**
```json
{
  "status": "cleared",
  "hash_cache": "cleared",
  "memory_caches": "cleared",
  "message": "Todos os caches foram limpos com sucesso"
}
```

---

## 🔍 Scan de Duplicatas

### Iniciar Scan
```bash
curl http://localhost:8008/api/scan_duplicates
```

**Resposta:**
```json
{
  "status": "started",
  "message": "Scan iniciado com processamento otimizado"
}
```

### Verificar Progresso
```bash
# Fazer polling até completar
curl http://localhost:8008/api/scan_progress
```

**Durante o scan:**
```json
{
  "current": 1250,
  "total": 5000,
  "is_scanning": true,
  "completed": false
}
```

**Após completar:**
```json
{
  "current": 5000,
  "total": 5000,
  "is_scanning": false,
  "completed": true,
  "results": {
    "total_files": 5000,
    "duplicate_groups": 87,
    "total_waste_bytes": 1234567890,
    "duplicates": [...],
    "cache_stats": {
      "hits": 4200,
      "misses": 800,
      "hit_rate": 84.0
    }
  }
}
```

---

## 🎯 Casos de Uso Comuns

### Caso 1: Navegar pelo Catálogo

```bash
# 1. Listar sites
curl http://localhost:8008/api/sites

# 2. Escolher um site e listar modelos
curl http://localhost:8008/api/models?site=fapello

# 3. Ver detalhes de um modelo
curl "http://localhost:8008/api/model?site=fapello&model=maria_silva"

# 4. Acessar mídia
# http://localhost:8008/media/fapello/maria_silva/foto1.jpg
```

### Caso 2: Limpar Espaço em Disco

```bash
# 1. Iniciar scan
curl http://localhost:8008/api/scan_duplicates

# 2. Aguardar completar (ou fazer polling)
sleep 60

# 3. Ver resultados
curl http://localhost:8008/api/scan_progress

# 4. Deletar duplicatas via interface web
# (ou via API POST /api/delete_duplicate)
```

### Caso 3: Monitorar Performance

```bash
# 1. Ver uso de cache
curl http://localhost:8008/api/cache_stats

# 2. Se cache cheio, limpar
curl http://localhost:8008/api/clear_cache

# 3. Executar testes
python test_catalog_performance.py
```

---

## ⚙️ Configurações Avançadas

### Customizar Diretório
```bash
python catalog_server.py \
  --port 8008 \
  --models-dir "D:\Meus Downloads\Archive"
```

### Ajustar Cache (editar código)
```python
# No início de catalog_server.py
CACHE_TTL = 3600  # 1 hora ao invés de 30min
MAX_CACHE_SIZE = 2000  # Mais entradas
```

### Ajustar Chunk Size
```python
SCAN_CHUNK_SIZE = 1000  # Processar mais por vez
```

---

## 📈 Interpretar Logs

### Logs Normais
```
[INFO] Iniciando scan de duplicatas otimizado...
[INFO] Coletando lista de arquivos...
[INFO] Total de arquivos a processar: 5432
[INFO] Progresso: 500/5432 (9.2%)
[INFO] Scan finalizado!
  - Arquivos processados: 5432
  - Grupos duplicados: 127
  - Espaço desperdiçado: 2.34 GB
  - Taxa de cache hit: 87.3%
```

### Significado
- **Cache hit >80%**: Excelente! Cache funcionando bem
- **Cache hit <50%**: Considere aumentar `CACHE_TTL`
- **Grupos duplicados**: Número de conjuntos de arquivos idênticos
- **Espaço desperdiçado**: Quanto pode ser economizado

---

## 🐛 Troubleshooting

### Problema: Servidor não inicia
```bash
# Verificar se porta está em uso
netstat -ano | findstr :8008  # Windows
lsof -i :8008                  # Linux/Mac

# Usar porta diferente
python catalog_server.py --port 9000
```

### Problema: Cache não funciona
```bash
# Limpar e reiniciar
curl http://localhost:8008/api/clear_cache
# Parar servidor (Ctrl+C)
# Iniciar novamente
python catalog_server.py
```

### Problema: Scan muito lento
```bash
# Verificar se há cache anterior
# (primeira execução é sempre lenta)

# Aumentar chunk size
# Editar SCAN_CHUNK_SIZE no código para 1000
```

### Problema: Uso alto de memória
```bash
# Reduzir tamanhos de cache
# Editar no código:
models_cache = CacheManager(max_size=100, ttl=1800)
model_info_cache = CacheManager(max_size=500, ttl=1800)
```

---

## 📊 Benchmarks Esperados

### Sistema Teste
- **CPU**: Intel i5 ou similar
- **RAM**: 8GB
- **SSD**: Recomendado
- **Arquivos**: ~5000 arquivos

### Resultados Esperados

| Operação | Tempo (primeira) | Tempo (cache) |
|----------|------------------|---------------|
| Listar sites | 100-200ms | <10ms |
| Listar 50 modelos | 500-800ms | 10-20ms |
| Detalhes modelo | 100-200ms | <10ms |
| Scan 5000 arquivos | 60-120s | 30-60s (cache hit) |

### Se Performance Diferente
- **Mais lento**: Pode ser HD mecânico ou muitos arquivos
- **Mais rápido**: SSD NVMe ou menos arquivos
- **Cache não funciona**: Verificar logs, pode ter erro

---

## 🎓 Dicas de Otimização

### 1. Use SSD
- **HDD**: Scan pode levar minutos
- **SSD**: Scan é 3-5x mais rápido

### 2. Execute Scan uma vez
- Cache de hash é persistente
- Scans subsequentes são muito mais rápidos

### 3. Monitore Memória
```bash
# Ver uso de cache
curl http://localhost:8008/api/cache_stats

# Se >80% usado, tudo bem
# Se >95%, considere aumentar limite
```

### 4. Aproveite Cache HTTP
- Navegador cacheia mídia por 24h
- Não precisa recarregar imagens já vistas

### 5. Use Compressão
- Navegadores modernos suportam gzip
- 60-80% economia de banda automática

---

## 📚 Documentação Adicional

- **Detalhes técnicos**: `CATALOG_OPTIMIZATION.md`
- **Histórico de mudanças**: `CHANGELOG_CATALOG.md`
- **Resumo executivo**: `OTIMIZACOES_RESUMO.md`
- **README geral**: `README.md`

---

## 💡 Exemplos de Scripts

### Monitoramento Contínuo
```bash
#!/bin/bash
# monitor_cache.sh

while true; do
  clear
  echo "=== Cache Stats ==="
  curl -s http://localhost:8008/api/cache_stats | jq
  sleep 5
done
```

### Backup Automático
```bash
#!/bin/bash
# backup_cache.sh

# Parar servidor
# Fazer backup do cache de hash
cp "C:\Users\...\duplicates_cache.json" "backup_$(date +%Y%m%d).json"
# Reiniciar servidor
```

---

## ✅ Checklist Pós-Instalação

- [ ] Servidor inicia sem erros
- [ ] Interface web carrega
- [ ] API `/api/sites` retorna dados
- [ ] Cache funciona (speedup visível)
- [ ] Gzip ativo (ver Network tab)
- [ ] Scan de duplicatas funciona
- [ ] Testes passam (`test_catalog_performance.py`)

---

## 🎉 Pronto!

Seu Catalog Server otimizado está rodando!

**Próximos passos:**
1. Navegar pela interface
2. Executar scan de duplicatas
3. Monitorar performance
4. Aproveitar velocidade 50-100x melhor! 🚀

---

**Versão:** 2.0.0  
**Última atualização:** 13/02/2026  
**Suporte:** Consultar documentação completa
