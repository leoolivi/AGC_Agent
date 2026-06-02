# Risky Clause Detection Prompt

Analizza il seguente contratto e identifica clausole potenzialmente rischiose.

## Categorie da rilevare
- `rinnovo_automatico`: clausole di rinnovo tacito o automatico
- `penale`: penali, multe, sanzioni contrattuali
- `limitazione_responsabilita`: limitazioni di responsabilità o esclusioni di garanzia
- `recesso`: condizioni di recesso o disdetta
- `esclusiva`: clausole di esclusiva
- `non_concorrenza`: vincoli di non concorrenza

## Severità
- `alto`: rischio significativo per l'azienda
- `medio`: richiede attenzione
- `basso`: informativo

## Output
Rispondi SOLO con JSON valido:
```json
{
  "clauses": [
    {
      "category": "rinnovo_automatico",
      "severity": "alto",
      "clause_text": "testo esatto della clausola",
      "page_number": 3,
      "paragraph_ref": "Art. 5.2",
      "plain_language_explanation": "Spiegazione in linguaggio semplice (max 200 caratteri)",
      "confidence_score": 0.92
    }
  ]
}
```

Se non trovi clausole rischiose, restituisci `{"clauses": []}`.
