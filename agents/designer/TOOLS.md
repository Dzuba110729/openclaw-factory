# TOOLS.md — Designer

## LaoZhang API

- **Key:** `$LAOZHANG_API_KEY` (прописан в `~/.openclaw/agents/designer/.env`)
- **Base URL:** https://api.laozhang.ai/v1
- **Image models:** `dall-e-3`, `gpt-image-1`, `gpt-4o-image`, `flux-kontext-pro`, `gemini-3-pro-image-preview`
- **Generations endpoint:** `POST /v1/images/generations`

## Saving Generated Images

⚠️ **CRITICAL — Where to save images:**

OpenClaw only allows sending files from specific directories. Always save images to ONE of:
1. `/tmp/openclaw/filename.png` — for temporary work
2. `~/.openclaw/media/shared/` — for files to share with other agents or send to user

❌ **NEVER use** `/tmp/filename.png` — regular `/tmp` is BLOCKED, use `/tmp/openclaw/` instead
❌ **NEVER save to** project folders like `projects/` for the purpose of sending

After generating, always copy to an allowed path before sending:
```bash
mkdir -p /tmp/openclaw && cp /path/to/generated.png /tmp/openclaw/image.png
```

## Sending Images to User

⚠️ **CRITICAL: MEDIA: tags with absolute paths are BLOCKED by security. Use CLI instead.**

To attach an image in Telegram — use exec to run this command:
```bash
openclaw message send --channel telegram --account designer --target {{OWNER_TG_ID}} --media /path/to/image.png --message "caption text"
```

Rules:
- Use the full absolute path to the file (`/tmp/openclaw/...`, etc.)
- Caption goes in `--message`
- Multiple files: run the command once per file
- Also works with https:// URLs as `--media` value

❌ **NEVER use** `MEDIA:/...` tags — absolute paths in MEDIA: are BLOCKED
❌ **NEVER use** `MEDIA:~/...` tags — tilde paths are also BLOCKED
✅ **ALWAYS use** `openclaw message send --media /path` via exec

## SMM Shared Folder

Path: `~/.openclaw/media/shared/smm/`

When making a cover or image for a VK post — save a copy to:
`images/cover-YYYY-MM-DD-тема.png`

```bash
mkdir -p ~/.openclaw/media/shared/smm/images
cp /tmp/openclaw/image.png ~/.openclaw/media/shared/smm/images/cover-2026-03-23-тема.png
```

SMM will pick it up from there without extra transfers.

## Quick Send

One command — sends immediately:
```bash
openclaw message send --channel telegram --account designer --target {{OWNER_TG_ID}} --media /tmp/openclaw/image.png --message "Готово!"
```

**Send IMMEDIATELY after generation** — don't wait until end of task.
