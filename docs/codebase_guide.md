# Codebase Guide

## Agent overview
- `ChatAgentGraph` = guardrail → context → LLM → parse `TOOL:` lines → execute atomic tools → response.
- Context = last 10 documents + active deadlines + pending inbox, built via SQLAlchemy.
- Guardrails = `GuardrailLayer` blocks unsafe input / output per `guardrails/constitution.md`.

## Atomic tools (`backend/app/agent/tools/atomic.py`)
| Tool | Args | Effect |
|------|------|--------|
| `crea_scadenza` | titolo | data | Creates `Deadline` DB row; optional Google Calendar event.
| `crea_bozza_email` | destinatario | oggetto | corpo | Creates `EmailDraft` DB row, stores HTML body.
| `crea_notifica` | titolo | messaggio | livello | Creates `Notification` DB row.
| `cerca_documenti` | query | Returns document list (read‑only).
| `leggi_email` | query (opzionale) | Reads Gmail inbox (requires Google link).
| `importa_da_drive` | nome | Imports file from Drive (requires Google link).

## Adding new tool
1. Append line to `TOOL_DEFINITIONS` (same `TOOL:` format).
2. Add branch in `execute_tool` mapping name → helper.
3. Implement async helper using `_get_session()` and appropriate model.
4. Return human‑readable string for response.

## Extending context
Edit `_build_context` in `chat_agent.py`:
- add queries, modify limits, format sections.

## Guardrails
- Edit `guardrails/constitution.md` for policy changes.
- Update `guardrails/blacklist.yaml` for keyword blocks.

## Status‑line badge
Add to `~/.claude/settings.json`:
```json
{ "statusLine": { "type": "command", "command": "bash \"/Users/olivi/.claude/plugins/cache/caveman/caveman/84cc3c14fa1e/hooks/caveman-statusline.sh\"" } }
```