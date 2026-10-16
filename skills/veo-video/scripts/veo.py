#!/usr/bin/env python3
"""
Генерация видео через Veo по LaoZhang API (асинхронная схема).

  python3 veo.py --prompt "промпт" --model veo-3.1-fast --out clip.mp4
  python3 veo.py --prompt "медленный наезд" --ref cover.png --out anim.mp4
  python3 veo.py --status <task_id>
  python3 veo.py --prompt "..." --dry-run

Ключ: LAOZHANG_API_KEY либо ~/.openclaw/agents/designer/.env
Зависимостей нет — только стандартная библиотека.
"""

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DEFAULT_ENV = Path.home() / ".openclaw/agents/designer/.env"
BASE_URL = "https://api.laozhang.ai"
POLL_INTERVAL = 10
POLL_TIMEOUT = 900


def load_key():
    key = os.environ.get("LAOZHANG_API_KEY")
    if key:
        return key
    env_path = Path(os.environ.get("LAOZHANG_ENV", DEFAULT_ENV))
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("LAOZHANG_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit(f"Не найден LAOZHANG_API_KEY (ни в окружении, ни в {DEFAULT_ENV})")


def call(url, key, data=None, headers=None, timeout=120, raw=False):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Authorization", f"Bearer {key}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return body if raw else json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")
    except urllib.error.URLError as e:
        sys.exit(f"Сеть недоступна: {e.reason}")


def multipart(fields, files):
    """Сборка multipart/form-data без внешних зависимостей."""
    boundary = uuid.uuid4().hex
    buf = bytearray()
    for name, value in fields.items():
        buf += f"--{boundary}\r\n".encode()
        buf += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        buf += f"{value}\r\n".encode()
    for name, path in files:
        p = Path(path)
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        buf += f"--{boundary}\r\n".encode()
        buf += (
            f'Content-Disposition: form-data; name="{name}"; filename="{p.name}"\r\n'
        ).encode()
        buf += f"Content-Type: {mime}\r\n\r\n".encode()
        buf += p.read_bytes() + b"\r\n"
    buf += f"--{boundary}--\r\n".encode()
    return bytes(buf), f"multipart/form-data; boundary={boundary}"


def submit(key, prompt, model, refs, dry_run):
    url = f"{BASE_URL}/v1/videos"
    if refs:
        for r in refs:
            if not Path(r).is_file():
                sys.exit(f"Референс не найден: {r}")
        fields = {"model": model, "prompt": prompt}
        files = [("input_reference", r) for r in refs]
        if dry_run:
            print(f"POST {url}  (multipart)")
            print(json.dumps({**fields, "input_reference": refs}, ensure_ascii=False, indent=2))
            print("\n(сухой прогон — не отправлено, баланс не потрачен)")
            return None
        body, ctype = multipart(fields, files)
        data = call(url, key, body, {"Content-Type": ctype})
    else:
        payload = {"model": model, "prompt": prompt}
        if dry_run:
            print(f"POST {url}")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            print("\n(сухой прогон — не отправлено, баланс не потрачен)")
            return None
        data = call(url, key, json.dumps(payload).encode(), {"Content-Type": "application/json"})

    task = data.get("id") or data.get("task_id") or data.get("data", {}).get("id")
    if not task:
        sys.exit("В ответе нет task_id:\n" + json.dumps(data, ensure_ascii=False)[:600])
    return task


def poll(key, task):
    print(f"Задача {task}, жду готовности…")
    started = time.time()
    while time.time() - started < POLL_TIMEOUT:
        st = call(f"{BASE_URL}/v1/videos/{task}", key)
        status = str(st.get("status") or st.get("state") or "").lower()
        if status in ("completed", "succeeded", "success", "done"):
            return st
        if status in ("failed", "error", "cancelled"):
            sys.exit("Задача провалилась:\n" + json.dumps(st, ensure_ascii=False)[:600])
        print(f"  … {status or 'в работе'} ({int(time.time()-started)} с)")
        time.sleep(POLL_INTERVAL)
    sys.exit(f"Не дождались за {POLL_TIMEOUT} с. Проверь позже: --status {task}")


def download(key, task, out):
    info = call(f"{BASE_URL}/v1/videos/{task}/content", key)
    url = info.get("url") or info.get("data", {}).get("url") if isinstance(info, dict) else None
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if url:
        with urllib.request.urlopen(url, timeout=300) as r:
            out.write_bytes(r.read())
    else:
        out.write_bytes(call(f"{BASE_URL}/v1/videos/{task}/content", key, raw=True, timeout=300))
    print(f"✓ {out}  ({out.stat().st_size // 1024} КБ)")


def main():
    ap = argparse.ArgumentParser(description="Генерация видео через Veo / LaoZhang")
    ap.add_argument("--prompt")
    ap.add_argument("--model", default="veo-3.1-fast")
    ap.add_argument("--ref", action="append", help="кадр-референс, можно дважды (начало и конец)")
    ap.add_argument("--out", default="video.mp4")
    ap.add_argument("--status", help="проверить существующую задачу по id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    key = load_key()

    if args.status:
        print(json.dumps(call(f"{BASE_URL}/v1/videos/{args.status}", key), ensure_ascii=False, indent=2))
        return

    if not args.prompt:
        ap.error("нужен --prompt (или --status)")

    task = submit(key, args.prompt, args.model, args.ref, args.dry_run)
    if task is None:
        return
    poll(key, task)
    download(key, task, args.out)


if __name__ == "__main__":
    main()
