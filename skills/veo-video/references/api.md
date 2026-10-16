# Veo через LaoZhang — API

Схема асинхронная: поставить задачу → опрашивать статус → скачать результат.

```
1. POST /v1/videos                    → task_id
2. GET  /v1/videos/{task_id}          → статус
3. GET  /v1/videos/{task_id}/content  → ссылка на файл
4. Скачать mp4
```

Скрипт `scripts/veo.py` проходит все четыре шага сам.

## Постановка задачи

Текст в видео:

```bash
curl -s -X POST "https://api.laozhang.ai/v1/videos" \
  -H "Authorization: Bearer $LAOZHANG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "model": "veo-3.1-fast", "prompt": "промпт" }'
```

С кадрами-референсами — multipart, не JSON:

```bash
curl -s -X POST "https://api.laozhang.ai/v1/videos" \
  -H "Authorization: Bearer $LAOZHANG_API_KEY" \
  -F "model=veo-3.1-fast-fl" \
  -F "prompt=плавный переход между кадрами" \
  -F "input_reference=@start.jpg" \
  -F "input_reference=@end.jpg"
```

Два референса при модели `-fl` означают начальный и конечный кадр — модель строит переход между ними.

## Опрос и скачивание

```bash
curl -s "https://api.laozhang.ai/v1/videos/$TASK" -H "Authorization: Bearer $KEY"
curl -s "https://api.laozhang.ai/v1/videos/$TASK/content" -H "Authorization: Bearer $KEY"
```

Опрашивать не чаще раза в 10 секунд. Обычная генерация — от одной до нескольких минут.

## Модели

| Модель | Назначение |
|--------|-----------|
| `veo-3.1-fast` | черновики, быстрее и дешевле |
| `veo-3.1` | финальное качество |
| `veo-3.1-fast-fl` | переход между двумя заданными кадрами |
| `veo-3.1-fl` | то же, полное качество |

## Команды скрипта

```bash
S=~/.openclaw/skills/veo-video/scripts/veo.py

python3 $S --prompt "..." --model veo-3.1-fast --out clip.mp4
python3 $S --prompt "..." --ref cover.png --out anim.mp4
python3 $S --prompt "..." --ref start.png --ref end.png --model veo-3.1-fast-fl --out trans.mp4
python3 $S --status <task_id>      # проверить задачу позже
python3 $S --prompt "..." --dry-run
```

Если генерация не уложилась в 15 минут, скрипт выходит и печатает `task_id` — задача при этом продолжает считаться на сервере, забрать её можно через `--status`.

## Пакетная генерация

Ставить задачи параллельно, собирать `task_id`, опрашивать все разом, скачивать по готовности. Последовательный запуск роликов по одному теряет много времени на ожидании.

Но: **сначала один ролик на проверку**, пакет — только после одобрения. Видео дороже изображений в разы.

## Диагностика

| Ответ | Причина |
|-------|---------|
| `401` | ключ неверный |
| `402`, отказ по балансу | кончились средства |
| `429` | слишком частые запросы |
| статус `failed` | промпт отклонён фильтром либо внутренняя ошибка — смягчить формулировки, повторить |
| нет `task_id` в ответе | неверная модель или формат запроса |

Проверить, что ключ жив:

```bash
python3 ~/.openclaw/skills/nano-banana/scripts/generate.py --balance
```
