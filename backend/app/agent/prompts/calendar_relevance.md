# Calendar Relevance Classification Prompt

Classifica se un evento del calendario Google è rilevante per la gestione amministrativa/compliance.

## Output
Rispondi SOLO con JSON valido:
```json
{
  "is_relevant": true,
  "confidence": 0.85,
  "suggested_category": "fiscale",
  "suggested_title": "Scadenza IVA trimestrale",
  "reasoning": "Breve spiegazione"
}
```

## Categorie suggerite
- fiscale, contrattuale, pagamento, generico

## Regole
- Eventi sociali, riunioni generiche, promemoria personali → is_relevant: false
- Scadenze fiscali, pagamenti, rinnovi contrattuali → is_relevant: true
- confidence tra 0.0 e 1.0
