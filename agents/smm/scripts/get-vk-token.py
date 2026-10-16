#!/usr/bin/env python3
"""
Получение пользовательского токена ВК и запись его в оба .env агента smm.

  python3 get-vk-token.py

Поддерживает два пути:
  1) Простой (implicit flow) — устаревший, но обычно ещё работает. 2 шага.
  2) VK ID (OAuth 2.1 + PKCE) — официальный текущий. Скрипт сам считает
     code_verifier/code_challenge и обменивает код на токен.

Токен нигде не печатается. Перед записью проверяется, что он:
  - пользовательский (users.get возвращает имя),
  - имеет доступ к стене группы (wall.get работает).
"""

import base64
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path.home()
ENV_FILES = [
    HOME / "openclaw-factory/agents/smm/.env",
    HOME / ".openclaw/agents/smm/.env",
]
REDIRECT = "https://oauth.vk.com/blank.html"
API_V = "5.199"


def c(text, color):
    codes = {"g": 32, "r": 31, "y": 33, "b": 36, "d": 2}
    return f"\033[{codes[color]}m{text}\033[0m"


def ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nОтменено.")
        sys.exit(1)


def http(url, data=None, timeout=25):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return json.loads(raw)
        except Exception:
            return {"_http_error": e.code, "_raw": raw[:500]}
    except Exception as e:
        return {"_error": str(e)}


def read_group_id():
    for f in ENV_FILES:
        if f.is_file():
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("VK_GROUP_ID="):
                    return line.split("=", 1)[1].strip().strip("\"'")
    return None


def verify(token, group_id):
    """Проверяет, что токен пользовательский и видит стену группы."""
    print("\n  Проверяю токен…")

    u = http(f"https://api.vk.com/method/users.get?access_token={token}&v={API_V}")
    if "error" in u:
        e = u["error"]
        print(c(f"  ✗ ВК отклонил: [{e.get('error_code')}] {e.get('error_msg')}", "r"))
        return False
    resp = u.get("response")
    if not resp:
        print(c("  ✗ Это НЕ пользовательский токен (users.get вернул пустоту).", "r"))
        print(c("    Похоже, получен токен сообщества или сервисный ключ.", "r"))
        return False
    who = resp[0]
    print(c(f"  ✓ Пользовательский токен, владелец: {who.get('first_name','')} "
            f"{who.get('last_name','')} (id {who.get('id')})", "g"))

    if group_id:
        w = http(f"https://api.vk.com/method/wall.get?owner_id=-{group_id}"
                 f"&count=1&access_token={token}&v={API_V}")
        if "error" in w:
            e = w["error"]
            print(c(f"  ✗ Стена группы недоступна: [{e.get('error_code')}] {e.get('error_msg')}", "r"))
            print(c("    Нужны права wall и groups, а аккаунт должен быть админом группы.", "r"))
            return False
        print(c(f"  ✓ Стена группы читается (постов: {w['response'].get('count')})", "g"))
    return True


def write_env(token):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for f in ENV_FILES:
        if not f.is_file():
            print(c(f"  ⚠️  нет файла {f} — пропускаю", "y"))
            continue
        shutil.copy(f, f.with_name(f.name + f".bak-{stamp}"))
        text = f.read_text(encoding="utf-8", errors="replace")
        if re.search(r"^VK_USER_TOKEN=.*$", text, re.M):
            text = re.sub(r"^VK_USER_TOKEN=.*$", "VK_USER_TOKEN=" + token, text, flags=re.M)
        else:
            text = text.rstrip("\n") + "\nVK_USER_TOKEN=" + token + "\n"
        f.write_text(text, encoding="utf-8")
        print(c(f"  ✓ записан: {f}", "g") + c(f"  (бэкап .bak-{stamp})", "d"))


def final_check():
    print("\n  Боевая проверка vk.js…")
    wd = HOME / "openclaw-factory/agents/smm"
    r = subprocess.run(["node", "scripts/vk.js", "pending"], cwd=wd,
                       capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out:
        print("  " + "\n  ".join(out.splitlines()[:15]))
    if r.returncode == 10:
        print(c("\n  ✓ ГОТОВО. Неотвеченных комментариев нет (код 10 — тишина).", "g"))
    elif r.returncode == 0:
        print(c("\n  ✓ ГОТОВО. Есть неотвеченные комментарии — smm их разберёт.", "g"))
    else:
        print(c(f"\n  ✗ vk.js вернул код {r.returncode}. Покажи вывод выше.", "r"))


def extract_from_url(url, key):
    """Достаёт параметр и из #фрагмента, и из ?query."""
    frag = urllib.parse.urlparse(url).fragment
    query = urllib.parse.urlparse(url).query
    for part in (frag, query):
        if part:
            vals = urllib.parse.parse_qs(part).get(key)
            if vals:
                return vals[0]
    m = re.search(rf"[#&?]{key}=([^&\s]+)", url)
    return m.group(1) if m else None


def flow_implicit(client_id):
    url = ("https://oauth.vk.com/authorize?"
           + urllib.parse.urlencode({
               "client_id": client_id,
               "display": "page",
               "redirect_uri": REDIRECT,
               "scope": "wall,groups,offline",
               "response_type": "token",
               "v": API_V,
           }))
    print("\n" + c("  ШАГ 1.", "b") + " Открой эту ссылку в браузере и нажми «Разрешить»:\n")
    print("  " + url + "\n")
    try:
        subprocess.run(["open", url], check=False)
        print(c("  (ссылка уже открыта в браузере)", "d"))
    except Exception:
        pass
    print("\n" + c("  ШАГ 2.", "b") + " Откроется пустая страница. Скопируй ВСЮ адресную строку\n"
          "         целиком и вставь сюда:\n")
    got = ask("  Адрес: ")
    token = extract_from_url(got, "access_token")
    if not token:
        if "code=" in got:
            print(c("\n  ✗ В адресе пришёл code=, а не access_token=.", "r"))
            print("    Значит приложение требует VK ID. Перезапусти и выбери путь 2.")
        else:
            print(c("\n  ✗ Не нашёл access_token в этом адресе.", "r"))
        return None
    return token


def flow_pkce(client_id):
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_hex(8)

    url = ("https://id.vk.com/authorize?"
           + urllib.parse.urlencode({
               "response_type": "code",
               "client_id": client_id,
               "code_challenge": challenge,
               "code_challenge_method": "S256",
               "redirect_uri": REDIRECT,
               "scope": "wall groups offline",
               "state": state,
           }))
    print("\n" + c("  ШАГ 1.", "b") + " Открой ссылку и подтверди доступ:\n")
    print("  " + url + "\n")
    try:
        subprocess.run(["open", url], check=False)
        print(c("  (ссылка уже открыта в браузере)", "d"))
    except Exception:
        pass
    print("\n" + c("  ШАГ 2.", "b") + " Скопируй ВСЮ адресную строку после подтверждения:\n")
    got = ask("  Адрес: ")

    code = extract_from_url(got, "code")
    device_id = extract_from_url(got, "device_id")
    if not code:
        print(c("\n  ✗ Не нашёл code в адресе.", "r"))
        return None

    print("\n  Меняю код на токен…")
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": verifier,
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "state": state,
    }
    if device_id:
        payload["device_id"] = device_id

    r = http("https://id.vk.com/oauth2/auth", data=payload)
    token = r.get("access_token")
    if not token:
        print(c("  ✗ Обмен не удался. Ответ VK ID:", "r"))
        print("    " + json.dumps(r, ensure_ascii=False)[:400])
        return None

    # VK ID выдаёт access_token на 1 час — без refresh_token схема нежизнеспособна
    refresh = r.get("refresh_token")
    expires = r.get("expires_in")
    if expires:
        print(c(f"  ⚠️  Токен живёт {expires} с (~{int(expires)//60} мин)", "y"))
    if refresh:
        _stash_refresh(refresh, client_id, device_id)
        print(c("  ✓ refresh_token сохранён — vk.js сможет продлевать доступ сам", "g"))
    else:
        print(c("  ⚠️  refresh_token не пришёл: токен протухнет через час и не продлится", "y"))
    return token


def _stash_refresh(refresh, client_id, device_id):
    """Кладёт refresh_token и сопутствующее рядом с токеном, в оба .env."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    pairs = {
        "VK_REFRESH_TOKEN": refresh,
        "VK_APP_ID": client_id,
    }
    if device_id:
        pairs["VK_DEVICE_ID"] = device_id
    for f in ENV_FILES:
        if not f.is_file():
            continue
        shutil.copy(f, f.with_name(f.name + f".bak-refresh-{stamp}"))
        text = f.read_text(encoding="utf-8", errors="replace")
        for k, v in pairs.items():
            if re.search(rf"^{k}=.*$", text, re.M):
                text = re.sub(rf"^{k}=.*$", f"{k}={v}", text, flags=re.M)
            else:
                text = text.rstrip("\n") + f"\n{k}={v}\n"
        f.write_text(text, encoding="utf-8")


def main():
    print("\n" + c("  Получение пользовательского токена ВК", "b"))
    print(c("  ─────────────────────────────────────", "d"))
    print("\n  Нужен ID приложения — число из адреса vk.com/editapp?id=" + c("ЧИСЛО", "y"))
    print(c("  Это НЕ «Защищённый ключ» и НЕ «Сервисный ключ».", "d"))

    client_id = ask("\n  ID приложения (только число): ")
    if not client_id.isdigit():
        print(c("  ✗ Должно быть число, например 51234567", "r"))
        sys.exit(1)

    print("\n  Каким путём получать токен?")
    print("    " + c("1", "y") + " — простой, старый (implicit). Попробуй сначала его")
    print("    " + c("2", "y") + " — VK ID / PKCE, официальный текущий")
    choice = ask("\n  Выбор [1/2]: ") or "1"

    token = flow_implicit(client_id) if choice == "1" else flow_pkce(client_id)
    if not token:
        sys.exit(1)

    if not verify(token, read_group_id()):
        print(c("\n  Файлы не тронуты — записывать нерабочий токен не стал.", "y"))
        sys.exit(1)

    print()
    write_env(token)
    final_check()
    print()


if __name__ == "__main__":
    main()
