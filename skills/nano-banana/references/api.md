# LaoZhang API — генерация изображений

## Ключ

```
~/.openclaw/agents/designer/.env
  LAOZHANG_API_KEY=sk-...
  LAOZHANG_BASE_URL=https://api.laozhang.ai
```

Скрипт `scripts/generate.py` подхватывает ключ сам: сначала из переменной окружения `LAOZHANG_API_KEY`, затем из этого файла. В чат ключ не печатать.

Оплата идёт с баланса LaoZhang — это **отдельный платный канал**, не связанный ни с какими подписками. Каждая генерация стоит денег.

## Команды

```bash
S=~/.openclaw/skills/nano-banana/scripts/generate.py

# базовая генерация
python3 $S --prompt "промпт" --ratio 16:9 --size 2K --out cover.png

# с референсом (сохранение персонажа, стиля, композиции)
python3 $S --prompt "тот же человек, другой ракурс" --ref base.png --out v2.png

# несколько референсов
python3 $S --prompt "..." --ref face.png --ref style.png --out out.png

# посмотреть запрос, не тратя баланс
python3 $S --prompt "..." --dry-run

# состояние счёта
python3 $S --balance
```

## Параметры

| Флаг | Значения | По умолчанию |
|------|----------|--------------|
| `--ratio` | `16:9`, `4:5`, `1:1`, `9:16`, `3:2` | `16:9` |
| `--size` | `1K`, `2K`, `4K` | `2K` |
| `--model` | `gemini-3-pro-image-preview`, `gemini-2.5-flash-image` | pro |
| `--ref` | путь к PNG/JPG, повторяемый | — |
| `--out` | путь сохранения | `output.png` |

`4K` заметно дороже и медленнее. Для обложек постов хватает `2K`. Черновики гонять на `gemini-2.5-flash-image` — он дешевле, потом финал на pro.

## Сырой запрос

```bash
curl -X POST "https://api.laozhang.ai/v1beta/models/gemini-3-pro-image-preview:generateContent" \
  -H "Authorization: Bearer $LAOZHANG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"parts": [{"text": "ПРОМПТ"}]}],
    "generationConfig": {
      "responseModalities": ["IMAGE"],
      "imageConfig": { "aspectRatio": "16:9", "imageSize": "2K" }
    }
  }'
```

Изображение приходит в base64: `candidates[0].content.parts[].inline_data.data`.

Референсы добавляются в тот же массив `parts` перед текстом:

```json
{"inline_data": {"mime_type": "image/png", "data": "<base64>"}}
```

## Работа с референсами

| Задача | Как |
|--------|-----|
| Тот же персонаж в другой сцене | референс с лицом + описание новой сцены |
| Сохранить стиль | референс-образец + «в стиле приложенного изображения» |
| Правка детали | исходник как референс + описание только изменения |
| Серия в одном ключе | один и тот же референс на все кадры |

Ссылаться на референс в тексте промпта: «человек с приложенного фото», «палитра как на референсе».

## Диагностика

| Ответ | Причина |
|-------|---------|
| `HTTP 401` | ключ неверный или истёк |
| `HTTP 404 Invalid URL` | неверный эндпоинт; у моделей путь `/v1beta/...`, у биллинга `/v1/dashboard/...` |
| `HTTP 429` | лимит запросов, подождать |
| `HTTP 402` / отказ по балансу | кончились средства на счету LaoZhang |
| Ответ без картинки | промпт отклонён фильтром — смягчить формулировки |
| Долгий ответ | `4K` генерируется дольше минуты, это нормально |

Проверить, что ключ жив:

```bash
python3 $S --balance
curl -s "https://api.laozhang.ai/v1/models" -H "Authorization: Bearer $LAOZHANG_API_KEY" | head -c 200
```

## Экономия

- Черновики — `1K`/`2K` и flash-модель, финал — pro
- Не генерировать текст на картинке: накладывать отдельно
- Серию делать после того, как одобрен первый кадр
- Сохранять удачные промпты в `knowledge/` — переиспользовать дешевле, чем подбирать заново
