#!/usr/bin/env python3
"""
Генерация изображений через Gemini Image по LaoZhang API.

Зависимостей нет — только стандартная библиотека.

  python3 generate.py --prompt "промпт" --ratio 16:9 --size 4K --out cover.png
  python3 generate.py --prompt "..." --ref base.png --out variant.png
  python3 generate.py --prompt "..." --dry-run          # показать запрос, не тратить баланс
  python3 generate.py --balance                          # остаток на счету

Ключ берётся из окружения LAOZHANG_API_KEY либо из
~/.openclaw/agents/designer/.env
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_ENV = Path.home() / ".openclaw/agents/designer/.env"
BASE_URL = "https://api.laozhang.ai"
MODEL = "gemini-3-pro-image-preview"


def load_key():
    key = os.environ.get("LAOZHANG_API_KEY")
    if key:
        return key
    env_path = Path(os.environ.get("LAOZHANG_ENV", DEFAULT_ENV))
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("LAOZHANG_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit(
        "Не найден LAOZHANG_API_KEY. Задай переменную окружения "
        f"или положи его в {DEFAULT_ENV}"
    )


def request(url, key, payload=None, timeout=300):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Authorization", f"Bearer {key}")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        sys.exit(f"HTTP {e.code} от LaoZhang: {body}")
    except urllib.error.URLError as e:
        sys.exit(f"Сеть недоступна: {e.reason}")


def build_payload(prompt, refs, ratio, size):
    parts = []
    for ref in refs or []:
        p = Path(ref)
        if not p.is_file():
            sys.exit(f"Референс не найден: {ref}")
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime,
                    "data": base64.b64encode(p.read_bytes()).decode(),
                }
            }
        )
    parts.append({"text": prompt})
    return {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": ratio, "imageSize": size},
        },
    }


def extract_image(data):
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            blob = part.get("inline_data") or part.get("inlineData")
            if blob and blob.get("data"):
                return base64.b64decode(blob["data"])
    return None


def main():
    ap = argparse.ArgumentParser(description="Генерация изображений через LaoZhang")
    ap.add_argument("--prompt", help="текст промпта")
    ap.add_argument("--ref", action="append", help="файл-референс, можно несколько")
    ap.add_argument("--ratio", default="16:9", help="16:9, 4:5, 1:1, 9:16")
    ap.add_argument("--size", default="2K", help="1K, 2K, 4K")
    ap.add_argument("--out", default="output.png", help="куда сохранить")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--dry-run", action="store_true", help="показать запрос, не отправлять")
    ap.add_argument("--balance", action="store_true", help="показать остаток и выйти")
    args = ap.parse_args()

    key = load_key()

    if args.balance:
        # /v1/user/balance больше не существует (404). Рабочий — billing/subscription.
        info = request(f"{BASE_URL}/v1/dashboard/billing/subscription", key)
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return

    if not args.prompt:
        ap.error("нужен --prompt (или --balance)")

    payload = build_payload(args.prompt, args.ref, args.ratio, args.size)

    if args.dry_run:
        preview = json.loads(json.dumps(payload))
        for part in preview["contents"][0]["parts"]:
            if "inline_data" in part:
                part["inline_data"]["data"] = f"<{len(part['inline_data']['data'])} байт base64>"
        print(f"POST {BASE_URL}/v1beta/models/{args.model}:generateContent")
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        print("\n(сухой прогон — запрос не отправлен, баланс не потрачен)")
        return

    url = f"{BASE_URL}/v1beta/models/{args.model}:generateContent"
    data = request(url, key, payload)
    img = extract_image(data)
    if not img:
        sys.exit(
            "В ответе нет изображения. Ответ API:\n"
            + json.dumps(data, ensure_ascii=False)[:800]
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(img)
    print(f"✓ {out}  ({len(img) // 1024} КБ, {args.ratio}, {args.size})")


if __name__ == "__main__":
    main()
