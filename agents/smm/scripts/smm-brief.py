#!/usr/bin/env python3
"""Сводка по контент-плану СММ без участия LLM.

Разбирает markdown-таблицы контент-плана, находит просроченные и ближайшие
посты, проверяет наличие материалов в shared-каталогах.

Вывод: JSON в stdout.
Код возврата: 10 — всё спокойно (нечего показывать), 0 — есть о чём доложить.
"""
import json
import os
import re
import sys
from datetime import date, timedelta

HOME = os.path.expanduser("~")
PLAN = os.environ.get(
    "SMM_PLAN", os.path.join(HOME, "openclaw-factory/agents/smm/memory/content-plan.md")
)
SHARED = os.environ.get(
    "SMM_SHARED", os.path.join(HOME, ".openclaw/media/shared/smm")
)
OVERDUE_WINDOW_DAYS = int(os.environ.get("SMM_OVERDUE_DAYS", "14"))
LOOKAHEAD_DAYS = int(os.environ.get("SMM_LOOKAHEAD_DAYS", "3"))

ROW = re.compile(r"^\|\s*(\d{2})\.(\d{2})\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|")


def parse_rows(text, today):
    rows = []
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if not m:
            continue
        dd, mm, _day, kind, topic, status = (
            m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
        )
        try:
            d = date(today.year, int(mm), int(dd))
        except ValueError:
            continue
        rows.append({
            "date": d.isoformat(),
            "type": kind.strip(),
            "topic": topic.strip(),
            "status": status.strip(),
        })
    return rows


def has_materials(topic_date):
    """Есть ли текст и обложки для даты."""
    stamp = topic_date  # YYYY-MM-DD
    posts = os.path.join(SHARED, "posts")
    images = os.path.join(SHARED, "images")
    text = any(stamp in f for f in os.listdir(posts)) if os.path.isdir(posts) else False
    covers = 0
    if os.path.isdir(images):
        covers = sum(1 for f in os.listdir(images) if stamp in f)
    return {"text": text, "covers": covers}


def main():
    today = date.today()
    if not os.path.exists(PLAN):
        print(json.dumps({"error": f"нет файла плана: {PLAN}"}, ensure_ascii=False))
        return 1

    rows = parse_rows(open(PLAN, encoding="utf-8").read(), today)

    overdue, upcoming, waiting = [], [], []
    for r in rows:
        d = date.fromisoformat(r["date"])
        st = r["status"].lower()
        if "опубликован" in st:
            continue
        r["materials"] = has_materials(r["date"])
        if "ждём" in st or "ждем" in st or "⚠" in r["status"]:
            if today - timedelta(days=OVERDUE_WINDOW_DAYS) <= d <= today + timedelta(days=LOOKAHEAD_DAYS):
                waiting.append(r)
        elif d < today and d >= today - timedelta(days=OVERDUE_WINDOW_DAYS):
            r["days_late"] = (today - d).days
            overdue.append(r)
        elif today <= d <= today + timedelta(days=LOOKAHEAD_DAYS):
            r["days_left"] = (d - today).days
            upcoming.append(r)

    out = {"today": today.isoformat(), "overdue": overdue,
           "upcoming": upcoming, "waiting": waiting}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if (overdue or upcoming or waiting) else 10


if __name__ == "__main__":
    sys.exit(main())
