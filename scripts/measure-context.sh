#!/bin/bash
# Замер системного промпта агента. Использование: measure-context.sh <agentId> [метка]
AGENT="${1:?нужен agentId}"
LABEL="${2:-adhoc}"
OUT="${OPENCLAW_MEASURE_DIR:-$HOME/.openclaw/logs/measure}"
mkdir -p "$OUT"
SID="MEASURE-$AGENT-$(date +%s)"
JSON=$(openclaw agent --agent "$AGENT" --session-id "$SID" --thinking off \
        --message "пинг" --json --timeout 120 2>/dev/null)
export MEASURE_AGENT="$AGENT" MEASURE_LABEL="$LABEL" MEASURE_OUT="$OUT"
echo "$JSON" | python3 -c '
import sys,json,os,datetime
try: d=json.load(sys.stdin)
except Exception as e: print("ОШИБКА разбора ответа:",e); sys.exit(1)
r=d.get("result",{}).get("meta",{}).get("systemPromptReport")
u=d.get("result",{}).get("meta",{}).get("agentMeta",{}).get("usage",{})
if not r: print("нет systemPromptReport"); sys.exit(1)
sp=r["systemPrompt"]; sk=r["skills"]
files=sum(f["injectedChars"] for f in r["injectedWorkspaceFiles"])
agent=os.environ["MEASURE_AGENT"]; label=os.environ["MEASURE_LABEL"]
row=dict(ts=datetime.datetime.now().isoformat(timespec="seconds"),agent=agent,label=label,
         promptChars=sp["chars"],skillChars=sk["promptChars"],skillCount=len(sk["entries"]),
         fileChars=files,fileCount=len([f for f in r["injectedWorkspaceFiles"] if not f["missing"]]),
         cacheWrite=u.get("cacheWrite"),cacheRead=u.get("cacheRead"))
print("%-12s %-14s промпт %6d симв | скиллы %5d (%2d шт) | файлы %5d (%d) | cacheWrite %s"%(
      agent,label,row["promptChars"],row["skillChars"],row["skillCount"],row["fileChars"],row["fileCount"],row["cacheWrite"]))
with open(os.path.join(os.environ["MEASURE_OUT"],"context-history.jsonl"),"a") as f:
    f.write(json.dumps(row,ensure_ascii=False)+"\n")
'
