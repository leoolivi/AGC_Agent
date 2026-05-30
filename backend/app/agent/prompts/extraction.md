# Field Extraction Prompt

Estrai i campi richiesti dal documento. Per ogni campo fornisci il valore e un confidence score (0.0-1.0).

Se un campo non è presente nel documento, imposta value a null e confidence a 0.0.

Rispondi SOLO con JSON: {"fields": {"campo": {"value": ..., "confidence": 0.XX}, ...}}
