# TOOLS.md — SMM

## Sending Files & Images to User in Telegram

⚠️ **CRITICAL: MEDIA: tags with absolute paths are BLOCKED. Use CLI instead.**

To send a file (image, PDF, document) in Telegram — use exec to run:
```bash
openclaw message send --channel telegram --account smm --target {{OWNER_TG_ID}} --media /path/to/file --message "caption"
```

Works with: PNG, JPG, PDF, CSV, any local file path or https:// URL.

❌ **NEVER use** `MEDIA:/...` — absolute paths in MEDIA: tags are BLOCKED
❌ **NEVER use** `MEDIA:~/...` — tilde paths are BLOCKED
✅ **ALWAYS use** `openclaw message send --media /path` via exec

Multiple files: run the command once per file.

## Allowed Paths for Saving Files

OpenClaw only allows sending files from specific directories:
- `/tmp/openclaw/filename.png` — for temporary files
- `~/.openclaw/media/shared/` — for sharing with other agents

❌ **NEVER use** regular `/tmp/file.png` — blocked
❌ **NEVER save to** agent project folders for the purpose of sending

Always create the directory first:
```bash
mkdir -p /tmp/openclaw
```

## Quick Send

One command — copies and sends immediately:
```bash
mkdir -p /tmp/openclaw && cp /path/to/file /tmp/openclaw/file.ext && openclaw message send --channel telegram --account smm --target {{OWNER_TG_ID}} --media /tmp/openclaw/file.ext --message "Готово!"
```

**Send IMMEDIATELY after generating a file** — don't wait until end of task.

## SMM Shared Folder

Path: `~/.openclaw/media/shared/smm/`

Structure:
- `content-plan/` — контент-планы от маркетолога
- `tasks/` — задачи на посты
- `images/` — обложки от дизайнера

Pick up images from designer:
```bash
ls ~/.openclaw/media/shared/smm/images/
```

## VK Comments Check

Новые комментарии приходят **событиями сообщества** (Long Poll) на групповом токене.
Опрос стены больше не используется: ВК закрыл `wall.get`/`wall.getComments`
для групповых токенов (ошибка 27), а пользовательские для этой установки блокирует.

```bash
node ~/openclaw-factory/agents/smm/scripts/vk.js pending    # JSON; exit 10 = тишина, 0 = есть работа
node ~/openclaw-factory/agents/smm/scripts/vk.js comments   # очередь неотвеченных, по-человечески
node ~/openclaw-factory/agents/smm/scripts/vk.js reply --comment_id ID --post_id ID --text "ответ"
```

Очередь неотвеченных лежит в `memory/vk-pending.json`, точка отсчёта событий —
в `memory/vk-longpoll.json`. Ответ автоматически убирает комментарий из очереди.

**Важно:** учитываются только комментарии, появившиеся после 14.09.2026 — раньше
этой даты события не собирались. Старые смотри в ВК вручную.

## Что в ВК работает и что нет

| Операция | Статус |
|----------|--------|
| Приём новых комментариев | ✅ события сообщества |
| Ответ на комментарий | ✅ групповой токен |
| Публикация текстового поста | ✅ групповой токен |
| Число подписчиков | ✅ `vk.js stat` |
| **Пост с картинкой** | ❌ загрузка медиа закрыта для групповых токенов |
| Полная статистика группы | ❌ `stats.get` требует пользовательский токен |

Посты с обложками публикует владелец вручную. Не пытайся чинить это через
пользовательский токен — проверено 14.09.2026, ВК их блокирует.

## Публикация поста с обложкой в ВК

API ВК не даёт загружать изображения. Пост с картинкой публикуется **через браузер**
в живой сессии Claude Code. Ты кладёшь заявку в очередь — сессия её подхватывает.

**Только после явного «да» владельца.** Заявка = команда на публикацию.

```bash
bash ~/openclaw-factory/agents/smm/scripts/vk-publish-request.sh \
  --text-file ~/.openclaw/media/shared/smm/posts/post-2026-09-15-tema.md \
  --image     ~/.openclaw/media/shared/smm/images/cover-2026-09-15-tema-v1.png \
  --slug      tema
```

Можно и текстом напрямую: `--text "текст поста"`.

Очередь: `~/.openclaw/media/shared/smm/to-publish/`
Опубликованные переезжают в `~/.openclaw/media/shared/smm/published/`

**Текстовый пост без картинки публикуй сам, через API** — это работает:
```bash
node ~/openclaw-factory/agents/smm/scripts/vk.js post --text "текст"
```

Заявка нужна только когда есть обложка.

Если сессия Claude Code не запущена, заявка просто ждёт в очереди — ничего не теряется.
Сообщи владельцу, что пост поставлен в очередь и ждёт публикации.
