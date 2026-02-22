"""
Template prompt SEMPLIFICATO per Ollama (versione compatta per migliori performance)
"""

SYSTEM_PROMPT_SIMPLE = """
Converti comandi HR in JSON. Output SEMPRE valido JSON con questi campi:
{
  "success": true,
  "message": "testo risposta",
  "operation": "query",
  "record_type": "personale",
  "changes": []
}

Operations: query, add_record, update_record, delete_record, batch_update
Record types: personale (con CF), strutture (senza CF)

Se comando poco chiaro: operation="query", message="chiedi chiarimenti"
"""

EXAMPLES_SIMPLE = """
ESEMPIO 1: "Mostra dipendenti senza sede"
{"success": true, "message": "Query dipendenti senza sede", "operation": "query", "record_type": "personale", "changes": []}

ESEMPIO 2: "Aggiungi dipendente Mario Rossi, CF RSSMRA80A01H501Z, codice M001"
{"success": true, "message": "Aggiungo Mario Rossi", "operation": "add_record", "record_type": "personale", "changes": [{"filter_criteria": {}, "after_values": {"TxCodFiscale": "RSSMRA80A01H501Z", "Titolare": "Mario Rossi", "Codice": "M001"}, "description": "Aggiungi Mario Rossi", "risk_level": "low"}]}
"""


def get_simple_system_prompt():
    """Ritorna versione semplificata system prompt"""
    return SYSTEM_PROMPT_SIMPLE


def get_simple_examples():
    """Ritorna esempi semplificati"""
    return EXAMPLES_SIMPLE
