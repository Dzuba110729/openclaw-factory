#!/bin/bash
# Заявка на публикацию поста с картинкой в ВК.
#
# API ВК не даёт загружать изображения (см. TOOLS.md), поэтому пост с обложкой
# публикуется через браузер в живой сессии Claude Code. Этот скрипт кладёт заявку
# в очередь — сессия её увидит и опубликует.
#
#   vk-publish-request.sh --text-file posts/post-2026-09-15-tema.md \
#                         --image /path/to/cover.png \
#                         [--slug tema]
#
# Только для СОГЛАСОВАННЫХ постов: владелец уже сказал «да».

set -u
QUEUE="$HOME/.openclaw/media/shared/smm/to-publish"
TEXT_FILE=""; IMAGE=""; SLUG=""

while [ $# -gt 0 ]; do
  case "$1" in
    --text-file) TEXT_FILE="$2"; shift 2;;
    --text)      TEXT_INLINE="$2"; shift 2;;
    --image)     IMAGE="$2"; shift 2;;
    --slug)      SLUG="$2"; shift 2;;
    *) echo "Неизвестный аргумент: $1"; exit 1;;
  esac
done

if [ -z "${TEXT_FILE}" ] && [ -z "${TEXT_INLINE:-}" ]; then
  echo "❌ Нужен --text-file <путь> или --text \"...\""; exit 1
fi
if [ -n "$TEXT_FILE" ] && [ ! -f "$TEXT_FILE" ]; then
  echo "❌ Файл с текстом не найден: $TEXT_FILE"; exit 1
fi
if [ -n "$IMAGE" ] && [ ! -f "$IMAGE" ]; then
  echo "❌ Картинка не найдена: $IMAGE"; exit 1
fi

mkdir -p "$QUEUE"
[ -z "$SLUG" ] && SLUG="post-$(date +%Y%m%d-%H%M%S)"
REQ="$QUEUE/${SLUG}.json"

TEXT=$([ -n "$TEXT_FILE" ] && cat "$TEXT_FILE" || printf '%s' "${TEXT_INLINE:-}")

TEXT="$TEXT" IMAGE="$IMAGE" SLUG="$SLUG" python3 - "$REQ" <<'PY'
import json,os,sys,datetime
json.dump({
  "slug": os.environ["SLUG"],
  "text": os.environ["TEXT"],
  "image": os.environ.get("IMAGE") or None,
  "created": datetime.datetime.now().isoformat(timespec="seconds"),
  "status": "ожидает публикации",
}, open(sys.argv[1],"w"), ensure_ascii=False, indent=2)
PY

echo "✅ Заявка создана: $REQ"
echo "   Сессия Claude Code опубликует пост через браузер."
echo "   Если сессия не запущена — заявка дождётся её."
