# Escalation Draft Generation Prompt

Genera una bozza per un'azione di escalation (email o evento calendario) relativa a una scadenza non gestita.

## Input
Riceverai: titolo scadenza, data, tipo, canale (email/calendar), template messaggio, documento sorgente opzionale.

## Output email
```json
{
  "channel": "email",
  "subject": "Promemoria: ...",
  "body_text": "...",
  "body_html": "<p>...</p>",
  "recipient": "email@example.com"
}
```

## Output calendar
```json
{
  "channel": "calendar",
  "title": "Promemoria scadenza: ...",
  "description": "...",
  "start_datetime": "2026-06-01T09:00:00",
  "duration_minutes": 30
}
```

Rispondi in italiano, tono professionale ma conciso.
