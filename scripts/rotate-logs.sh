#!/bin/zsh
# Ротация логов OpenClaw gateway.
# Логи пишет launchd (StandardOutPath/StandardErrorPath), файловый дескриптор
# открыт на всё время работы процесса — поэтому файл нельзя переименовывать,
# иначе gateway продолжит писать в старый inode. Обнуляем на месте (: > file),
# а перед этим сохраняем сжатый хвост.

set -u

LOGDIR="${OPENCLAW_LOG_DIR:-$HOME/.openclaw/logs}"
MAX_BYTES="${OPENCLAW_LOG_MAX_BYTES:-$((50 * 1024 * 1024))}"    # порог ротации: 50 МБ
TAIL_BYTES="${OPENCLAW_LOG_TAIL_BYTES:-$((3 * 1024 * 1024))}"   # сохраняем в архив: 3 МБ хвоста
STATE="$LOGDIR/rotate.log"

for name in gateway.log gateway.err.log; do
  f="$LOGDIR/$name"
  [[ -f "$f" ]] || continue

  size=$(stat -f%z "$f" 2>/dev/null) || continue
  (( size > MAX_BYTES )) || continue

  # сдвигаем поколения: .1.gz -> .2.gz, текущий хвост -> .1.gz
  [[ -f "$f.1.gz" ]] && mv -f "$f.1.gz" "$f.2.gz"
  if tail -c "$TAIL_BYTES" "$f" | gzip -c > "$f.1.gz.tmp"; then
    mv -f "$f.1.gz.tmp" "$f.1.gz"
  else
    rm -f "$f.1.gz.tmp"
  fi

  : > "$f"
  print -r -- "$(date '+%Y-%m-%dT%H:%M:%S%z') rotated $name (было $size байт)" >> "$STATE"
done

# не даём разрастись самому журналу ротации
if [[ -f "$STATE" ]] && (( $(stat -f%z "$STATE") > 65536 )); then
  tail -n 200 "$STATE" > "$STATE.tmp" && mv -f "$STATE.tmp" "$STATE"
fi
