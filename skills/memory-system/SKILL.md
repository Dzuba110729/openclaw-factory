---
name: memory-system
description: Развёртывание и обслуживание системы памяти агентов OpenClaw — структура, индекс, поиск, диагностика. Активируется на: настрой память, переиндексируй, память не ищет, memory index, структура памяти.
triggers:
  - настрой память
  - переиндексируй
  - память не ищет
  - memory index
---

# Memory System — обслуживание памяти

Скилл для настройки и починки памяти агентов. Про то, что писать в память, — скилл `agent-memory`.

## Структура воркспейса

```
~/openclaw-factory/agents/<id>/
  SOUL.md            — личность и принципы
  AGENTS.md          — регламент работы
  IDENTITY.md        — кто агент, как представляется
  USER.md            — про владельца
  TOOLS.md           — доступные инструменты и их особенности
  HEARTBEAT.md       — что делать по расписанию
  MEMORY.md          — долговременная память
  memory/            — дневники YYYY-MM-DD.md + active-context.md
  memory-archive/    — старое, вне индекса
  knowledge/         — справочники: бренд, продукты, регламенты
  learning/          — patterns.md, anti-patterns.md, corrections.md
```

Файлы из первого блока вживляются в системный промпт на каждом ходу. Каждая лишняя строка в них — это токены в каждом запросе. `memory/` и `knowledge/` в промпт не попадают, читаются по требованию.

## Поиск и индекс

Конфигурация — в `~/.openclaw/openclaw.json`:

```json
"memorySearch": {
  "enabled": true,
  "sources": ["memory"],
  "provider": "mistral",
  "model": "mistral-embed",
  "query": { "maxResults": 8, "minScore": 0.3 }
}
```

Команды:

```bash
openclaw memory status                      # состояние индекса
openclaw memory search "запрос" --agent smm # поиск
openclaw memory index                       # переиндексация
openclaw memory promote                     # кандидаты в MEMORY.md
```

Переиндексация идёт по расписанию: launchd `ai.openclaw.reindex`, 4:30. Лог — `~/.openclaw/logs/reindex-memory.log`.

## Диагностика

| Симптом | Проверить |
|---------|-----------|
| Поиск ничего не находит | `openclaw memory status` — есть ли индекс у этого агента |
| Находит устаревшее | Индекс протух → `openclaw memory index` |
| Поиск падает с ошибкой | `MISTRAL_API_KEY` в `env` конфига — ключ жив? |
| Агент «забыл» решение | Оно попало в дневник, но не в `MEMORY.md` |
| Промпт разбух | Проверить размер файлов первого блока |

## Замер системного промпта

```bash
~/.openclaw/scripts/measure-context.sh <агент> <метка>
```

История замеров — `~/.openclaw/logs/measure/context-history.jsonl`.

Точная разбивка приходит в `openclaw agent --json` → `result.meta.systemPromptReport`. Это единственный достоверный способ понять, на что уходит промпт.

## Что на самом деле влияет на расход

Под провайдером `claude-cli` **не работают**: `contextInjection`, `contextPruning`, `compaction`, `thinkingDefault` — OpenClaw в этом режиме не пишет транскрипты, и эти настройки до CLI не доходят.

Влияют только:

1. Состав системного промпта — файлы воркспейса и allowlist скиллов (`agents.list[].skills`)
2. Модель
3. Число ходов и число запусков агента

Поэтому оптимизация начинается с вопроса «а можно ли не будить модель вообще» — условие периодической задачи часто считается шеллом.

## Ловушка: skillsSnapshot

Список скиллов кэшируется в сессии — `~/.openclaw/agents/<id>/sessions/sessions.json`, поле `skillsSnapshot`.

После смены allowlist или содержимого скиллов **живые сессии продолжают работать со старым снимком**, пока их не сбросить. Новые сессии и изолированные прогоны подхватывают сразу.

Если поменял скиллы и «ничего не изменилось» — сначала проверь это, а не логику.

## Добавление памяти новому агенту

1. Создать `memory/` и `MEMORY.md` в воркспейсе
2. Прописать регламент в `AGENTS.md`: что писать в дневник, что в долговременную
3. `openclaw memory index`
4. Проверить `openclaw memory search` по заведомо известной фразе
