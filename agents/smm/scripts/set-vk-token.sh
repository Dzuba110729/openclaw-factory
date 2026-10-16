#!/bin/bash
# Замена VK_USER_TOKEN сразу в двух .env + проверка живости.
# Токен вводится скрыто и нигде не печатается.
set -u

F1="$HOME/openclaw-factory/agents/smm/.env"
F2="$HOME/.openclaw/agents/smm/.env"

echo ""
echo "  Замена пользовательского токена ВК"
echo ""

read -rsp "  Вставь новый токен (ввод скрыт) и нажми Enter: " TOKEN
echo ""

if [ -z "${TOKEN:-}" ]; then
  echo "  ✗ Пусто. Ничего не менял."
  exit 1
fi

case "$TOKEN" in
  vk1.a.*) ;;
  *) echo "  ⚠️  Токен обычно начинается с 'vk1.a.' — проверь, что скопировал целиком."
     read -rp "  Всё равно записать? [y/N] " YN
     [ "$YN" = "y" ] || { echo "  Отменено."; exit 1; } ;;
esac

echo ""
echo "  Проверяю токен до записи…"
RESP=$(curl -s --max-time 20 "https://api.vk.com/method/users.get?access_token=${TOKEN}&v=5.199")

if echo "$RESP" | grep -q '"error"'; then
  MSG=$(echo "$RESP" | sed -n 's/.*"error_msg":"\([^"]*\)".*/\1/p')
  CODE=$(echo "$RESP" | sed -n 's/.*"error_code":\([0-9]*\).*/\1/p')
  echo "  ✗ ВК отклонил токен: [$CODE] $MSG"
  echo "    Файлы не тронуты."
  exit 1
fi
echo "  ✓ Токен принят ВК"

# Проверяем доступ именно к стене группы — это то, ради чего токен и нужен
GID=$(grep -m1 '^VK_GROUP_ID=' "$F1" 2>/dev/null | cut -d= -f2 | tr -d '"'"'"' \r')
if [ -n "${GID:-}" ]; then
  WALL=$(curl -s --max-time 20 "https://api.vk.com/method/wall.get?owner_id=-${GID}&count=1&access_token=${TOKEN}&v=5.199")
  if echo "$WALL" | grep -q '"error"'; then
    MSG=$(echo "$WALL" | sed -n 's/.*"error_msg":"\([^"]*\)".*/\1/p')
    echo "  ✗ Стена группы недоступна: $MSG"
    echo "    Аккаунт должен быть админом группы, а в scope нужны wall и groups."
    echo "    Файлы не тронуты."
    exit 1
  fi
  echo "  ✓ Стена группы читается"
fi

STAMP=$(date +%Y%m%d-%H%M%S)
for F in "$F1" "$F2"; do
  [ -f "$F" ] || { echo "  ⚠️  нет файла $F — пропускаю"; continue; }
  cp "$F" "${F}.bak-${STAMP}"
  if grep -q '^VK_USER_TOKEN=' "$F"; then
    TOKEN="$TOKEN" perl -i -pe 's/^VK_USER_TOKEN=.*$/"VK_USER_TOKEN=".$ENV{TOKEN}/e' "$F"
  else
    printf '\nVK_USER_TOKEN=%s\n' "$TOKEN" >> "$F"
  fi
  echo "  ✓ записан: $F  (бэкап .bak-${STAMP})"
done

unset TOKEN

echo ""
echo "  Боевая проверка vk.js…"
cd "$HOME/openclaw-factory/agents/smm" || exit 1
set +e
OUT=$(node scripts/vk.js pending 2>&1); RC=$?
set -e
echo "$OUT" | head -20
case $RC in
  10) echo ""; echo "  ✓ ГОТОВО. Неотвеченных комментариев нет (код 10 — тишина)." ;;
  0)  echo ""; echo "  ✓ ГОТОВО. Есть неотвеченные комментарии — smm их разберёт." ;;
  *)  echo ""; echo "  ✗ vk.js всё ещё падает (код $RC). Покажи вывод выше." ;;
esac
echo ""
