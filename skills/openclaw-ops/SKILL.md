---
name: openclaw-ops
description: Эксплуатация OpenClaw — конфиг, агенты, каналы, gateway, launchd, логи, диагностика. Активируется на: openclaw, gateway, бот не отвечает, перезапусти, конфиг openclaw, добавь агента.
triggers:
  - openclaw
  - gateway
  - бот не отвечает
  - конфиг openclaw
  - добавь агента
---

# OpenClaw Ops — эксплуатация

Установка на этой машине: 9 агентов, каждый — отдельный Telegram-бот. Gateway на `127.0.0.1:18789`.

## Карта путей

```
~/.openclaw/openclaw.json          конфиг
~/.openclaw/agents/<id>/           состояние, сессии
~/openclaw-factory/agents/<id>/    воркспейс агента
~/.openclaw/skills/                скиллы
~/.openclaw/logs/                  логи
~/.openclaw/backups/               бэкапы
~/Library/LaunchAgents/            plist'ы сервисов
```

## Первая команда при любой проблеме

```bash
openclaw status
```

## Диагностика: бот молчит

Порядок именно такой — он отсортирован по частоте причин.

**1. Истёкшая OAuth-сессия** — самая частая причина.

Симптом: бот на любое сообщение отвечает `Something went wrong while processing your request.`

```bash
grep "could not be refreshed" ~/.openclaw/logs/gateway.err.log
```

Лечение: `/login` в Claude Code. **Gateway перезапускать не нужно** — свежий токен подхватывается со следующего запроса.

Проверить срок текущего токена:

```bash
security find-generic-password -s "Claude Code-credentials" -w | python3 -c "import sys,json,datetime;o=json.load(sys.stdin)['claudeAiOauth'];print(datetime.datetime.fromtimestamp(o['expiresAt']/1000))"
```

**2. Gateway не запущен**

```bash
launchctl list | grep openclaw
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
```

**3. Сервис отключён** — `launchctl bootstrap` падает с `Bootstrap failed: 5: Input/output error`:

```bash
launchctl print-disabled gui/$(id -u) | grep claw
launchctl enable gui/$(id -u)/ai.openclaw.gateway
```

Ошибка EIO 5 никак не намекает на запрет — не трать время на права и синтаксис plist.

**4. Порт занят.** Вручную запущенный `openclaw gateway` держит 18789, и сервис не поднимется.

## Проверка агента без отправки наружу

```bash
openclaw agent --agent <id> -m "ответь: ок"
```

Без `--deliver` в Telegram ничего не уходит. Используй это всегда при отладке — иначе разбудишь настоящего бота, и он напишет владельцу.

## Правка конфига

Порядок обязательный:

1. Бэкап в `~/.openclaw/backups/`
2. Правка
3. Проверка валидности: `python3 -m json.tool ~/.openclaw/openclaw.json > /dev/null`
4. `launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway`
5. `openclaw status`

## Удаление агента

`openclaw agents delete <id> --force` оставляет два хвоста:

1. блок `channels.telegram.accounts.<id>` в конфиге — удалять вручную
2. пустой каталог `~/.openclaw/agents/<id>` — `rmdir`

После удаления всегда: `grep -n "<id>" ~/.openclaw/openclaw.json`. Воркспейсы агентов бывают git-репозиториями — бэкапить перед удалением.

## Логи

```bash
~/.openclaw/logs/gateway.log       вывод gateway
~/.openclaw/logs/gateway.err.log   ошибки — сюда смотреть первым
~/.openclaw/logs/vk-gate.log       гейт проверки ВК
~/.openclaw/logs/smm-morning.log   утренний гейт
~/.openclaw/logs/reindex-memory.log переиндексация памяти
```

**Ротация только обнулением на месте** (`: > файл`). Переименовывать нельзя: launchd держит дескриптор, и запись уйдёт в старый inode, а новый файл останется пустым. Скрипт: `~/.openclaw/scripts/rotate-logs.sh`, сервис `ai.openclaw.logrotate`.

Шум `polling stall detected` в логе — отдельная сетевая история, не причина молчания ботов.

## Сервисы launchd

```
ai.openclaw.gateway             основной
ai.openclaw.logrotate           ротация логов, каждые 30 мин
ai.openclaw.reindex             переиндексация памяти, 4:30
ai.openclaw.vkgate              проверка ВК, каждые 8 ч
ai.openclaw.smmmorning          утренний разбор, 9:00
```

Гейты (`vkgate`, `smmmorning`) считают условие в шелле и будят модель **только если есть работа** — на тишине выходят за секунды. Скрипты параметризованы переменными (`VK_GATE_*`, `SMM_MORNING_*`) специально для тестирования подменными командами. Тестируй только так.

## Обновление

Сидим на `2026.4.11` осознанно. `latest` требует Node новее установленного, а путь Node захардкожен в plist gateway. Путь обновления, если понадобится, — канал `extended-stable`, с полным бэкапом `~/.openclaw` и перегенерацией plist. Не перед рабочим днём.
