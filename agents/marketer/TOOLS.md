# TOOLS.md — Marketer

## Sending Files & Images to User

⚠️ **CRITICAL: MEDIA: tags with absolute paths are BLOCKED. Use CLI instead.**

To send a file in Telegram — use exec to run:
```bash
openclaw message send --channel telegram --account marketer --target {{OWNER_TG_ID}} --media /path/to/file.pdf --message "caption"
```

Works with: PNG, JPG, PDF, CSV, XLSX, MP4 and any local file path.

❌ **NEVER use** `MEDIA:/...` — absolute paths in MEDIA: tags are BLOCKED
❌ **NEVER use** `MEDIA:~/...` — tilde paths are BLOCKED
✅ **ALWAYS use** `openclaw message send --media /path` via exec

Multiple files: run the command once per file.

## SMM Shared Folder

Path: `~/.openclaw/media/shared/smm/`

Put here:
- **Контент-план** → `content-plan/content-plan-YYYY-MM.md`
- **Задачи на посты** → `tasks/task-YYYY-MM-DD-тема.md`

```bash
# Сохранить контент-план:
cat > ~/.openclaw/media/shared/smm/content-plan/content-plan-2026-03.md << 'END'
[контент-план здесь]
END

# Сохранить задачу на пост:
cat > ~/.openclaw/media/shared/smm/tasks/task-2026-03-23-тема.md << 'END'
[задача здесь]
END
```

## Quick Send

One command — sends file immediately:
```bash
openclaw message send --channel telegram --account marketer --target {{OWNER_TG_ID}} --media /tmp/openclaw/file.pdf --message "Готово!"
```

**Send IMMEDIATELY after generating** — don't wait.
