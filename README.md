# Dependency Graph Visualizer for Alpine Linux (`apk`)

Инструмент **CLI** для **визуализации графа зависимостей пакетов Alpine Linux**.

---
**Команда для запуска инструмента:**

```bash
python main.py \
  --package busybox \
  --repo https://dl-cdn.alpinelinux.org/alpine/v3.19/main/x86_64 \
  --mermaid \
  --ascii \
  --max-depth 3
```

---

### Пояснение:

| Параметр | Почему                                                                       |
|--------|------------------------------------------------------------------------------|
| `main.py` | Испольняемый файл                                                            |
| `--package` | Название пакета                                                              |
| `--repo` | Актуальный репозиторий                                                       |
| `--mermaid` | Создание графа mermaid                                                       |
| `--ascii` | Создание ascii-дерева                                                        |
| `--max-depth` | Ограничение, чтобы не утонуть в зависимостях                                 |
| `--filter` | Фильтруем |

---

## Установка
```bash
git clone https://github.com/Estriper0/pr_konf2