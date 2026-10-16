---
name: figma
description: Работа с Figma через REST API. Скачивает макеты, компоненты, стили и изображения по ссылке на Figma-файл или фрейм. Используй когда пользователь скидывает ссылку на Figma или просит взять макет из Figma и сделать код/изображение.
---

# Figma API — Получить макет по ссылке

## Настройка (один раз)

Токен хранится в `~/.openclaw/agents/designer/.env`:
```
FIGMA_TOKEN=figd_xxxxxxxxxx
```

Загрузить токен:
```bash
source ~/.openclaw/agents/designer/.env
```

## Разбор ссылки Figma

Ссылки бывают двух форматов:
```
https://www.figma.com/file/FILE_KEY/...?node-id=NODE_ID
https://www.figma.com/design/FILE_KEY/...?node-id=NODE_ID
```

- `FILE_KEY` — ключ файла (часть URL между `/file/` и следующим `/`)
- `NODE_ID` — ID конкретного фрейма/компонента (параметр `node-id`, символ `:` заменить на `%3A`)

## Получить данные макета

```bash
source ~/.openclaw/agents/designer/.env

FILE_KEY="ВАШ_FILE_KEY"
NODE_ID="0%3A1"  # замените : на %3A

# Получить структуру файла / фрейма
curl -H "X-Figma-Token: $FIGMA_TOKEN" \
  "https://api.figma.com/v1/files/$FILE_KEY/nodes?ids=$NODE_ID" \
  | python3 -m json.tool > /tmp/figma_frame.json

cat /tmp/figma_frame.json | python3 -c "
import sys,json
d=json.load(sys.stdin)
nodes = d.get('nodes',{})
for nid,node in nodes.items():
    doc = node.get('document',{})
    print('Name:', doc.get('name'))
    print('Type:', doc.get('type'))
    print('Size:', doc.get('absoluteBoundingBox',{}))
    # Цвета заливки
    fills = doc.get('fills',[])
    for f in fills[:3]:
        c = f.get('color',{})
        if c:
            r,g,b = int(c.get('r',0)*255), int(c.get('g',0)*255), int(c.get('b',0)*255)
            print(f'Fill: rgb({r},{g},{b}) = #{r:02x}{g:02x}{b:02x}')
"
```

## Экспортировать изображение фрейма

```bash
source ~/.openclaw/agents/designer/.env

FILE_KEY="ВАШ_FILE_KEY"
NODE_ID="0:1"  # здесь : без замены

# Получить URL изображения (PNG, scale 2x)
EXPORT_URL=$(curl -s -H "X-Figma-Token: $FIGMA_TOKEN" \
  "https://api.figma.com/v1/images/$FILE_KEY?ids=$NODE_ID&format=png&scale=2" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); imgs=d.get('images',{}); print(list(imgs.values())[0] if imgs else 'ERROR')")

echo "URL: $EXPORT_URL"

# Скачать изображение
curl -L "$EXPORT_URL" -o ~/.openclaw/media/shared/smm/images/figma-export.png
echo "Сохранено: ~/.openclaw/media/shared/smm/images/figma-export.png"
```

## Получить стили файла (цвета, шрифты)

```bash
source ~/.openclaw/agents/designer/.env
FILE_KEY="ВАШ_FILE_KEY"

curl -s -H "X-Figma-Token: $FIGMA_TOKEN" \
  "https://api.figma.com/v1/files/$FILE_KEY/styles" \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
for s in d.get('meta',{}).get('styles',[]):
    print(s.get('style_type'), '—', s.get('name'))
"
```

## Алгоритм: Figma → Код

1. Получить ссылку от пользователя → извлечь FILE_KEY и NODE_ID
2. Скачать структуру фрейма → прочитать размеры, цвета, шрифты
3. Экспортировать PNG → изучить визуально через `image` tool
4. Применить скилл `frontend-design` → написать HTML/CSS максимально близко к макету
5. Скриншотить результат → сравнить с оригиналом
6. Итерировать до совпадения

## Частые ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `403 Forbidden` | Нет доступа к файлу | Файл должен быть "Anyone with link can view" |
| `404 Not Found` | Неверный FILE_KEY | Проверить ссылку |
| `invalid_grant` | Истёк токен | Сгенерировать новый в Figma Settings |
| Пустой node | NODE_ID не найден | Использовать точный id из URL |
