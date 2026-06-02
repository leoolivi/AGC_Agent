# Cross-Document Correlation Prompt

Analizza il documento corrente e confrontalo con i documenti correlati nel contesto.

## Tipi di correlazione
- `derivato_da`: il documento deriva da un altro (es. fattura da ordine)
- `versione_di`: il documento è una versione aggiornata di un altro
- `allegato_di`: il documento è un allegato di un altro
- `in_conflitto_con`: i documenti contengono dati contraddittori

## Output
Rispondi SOLO con JSON valido:
```json
{
  "correlations": [
    {
      "target_document_id": "uuid-del-documento-target",
      "correlation_type": "derivato_da",
      "confidence_score": 0.88,
      "source_passage": "testo nel documento sorgente",
      "target_passage": "testo nel documento target",
      "source_page": 1,
      "target_page": 2
    }
  ]
}
```

Regole:
- `confidence_score` tra 0.0 e 1.0
- Non correlare un documento con se stesso
- Segnala conflitti con `in_conflitto_con` solo se ci sono contraddizioni esplicite
