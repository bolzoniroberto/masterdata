"""
Parser comandi linguaggio naturale → operazioni strutturate.
Usa Ollama LLM per interpretare comandi utente e generare modifiche proposte.
"""
import pandas as pd
import json
import uuid
from typing import Dict, Any, List
from services.ollama_client import OllamaClient
from models.bot_models import (
    OperationType,
    RecordType,
    BotResponse,
    ChangeProposal
)
from prompts.system_prompts_simple import (
    get_simple_system_prompt,
    get_simple_examples
)


class CommandParser:
    """
    Parser comandi NL per operazioni HR.

    Workflow:
    1. User input → build context (stats DataFrame)
    2. Generate prompt con examples
    3. Call Ollama LLM
    4. Parse JSON response
    5. Convert to BotResponse con ChangeProposal validati
    """

    def __init__(self, ollama_client: OllamaClient):
        """
        Inizializza parser.

        Args:
            ollama_client: Client Ollama configurato
        """
        self.client = ollama_client

    def parse_command(
        self,
        user_input: str,
        personale_df: pd.DataFrame,
        strutture_df: pd.DataFrame
    ) -> BotResponse:
        """
        Interpreta comando utente e genera BotResponse con modifiche proposte.

        Args:
            user_input: Comando linguaggio naturale
            personale_df: DataFrame personale corrente
            strutture_df: DataFrame strutture corrente

        Returns:
            BotResponse con lista ChangeProposal o query_result

        Examples:
            >>> parser = CommandParser(ollama_client)
            >>> response = parser.parse_command(
            ...     "Sposta tutti i dipendenti di Milano a Roma",
            ...     personale_df,
            ...     strutture_df
            ... )
            >>> print(response.message)
            >>> print(len(response.changes))
        """
        # Costruisci contesto dati SEMPLIFICATO per LLM
        context = self._build_simple_context(personale_df, strutture_df)

        # Costruisci prompt SEMPLIFICATO
        prompt = self._build_simple_prompt(user_input, context)

        # Chiamata Ollama con prompt semplificato
        success, parsed, error = self.client.generate(
            prompt=prompt,
            system_prompt=get_simple_system_prompt(),
            temperature=0.1,
            format="json"
        )

        if not success:
            return BotResponse(
                success=False,
                message=f"Errore interpretazione comando: {error}",
                operation=OperationType.QUERY,
                changes=[]
            )

        # Verifica che parsed sia un dict valido
        if not parsed or not isinstance(parsed, dict):
            return BotResponse(
                success=False,
                message=f"Risposta LLM non valida. Il modello non ha generato JSON strutturato. Prova a riformulare il comando in modo più semplice.",
                operation=OperationType.QUERY,
                changes=[]
            )

        # Converti risposta JSON in BotResponse strutturato
        try:
            return self._convert_to_bot_response(
                parsed,
                personale_df,
                strutture_df
            )
        except Exception as e:
            # Log errore con dettagli per debug
            import traceback
            error_detail = traceback.format_exc()
            return BotResponse(
                success=False,
                message=f"Errore parsing risposta LLM: {str(e)}. Il comando potrebbe essere troppo complesso. Prova con un comando più semplice.",
                operation=OperationType.QUERY,
                changes=[]
            )

    def _build_context(
        self,
        personale_df: pd.DataFrame,
        strutture_df: pd.DataFrame
    ) -> str:
        """
        Costruisce contesto dati per prompt LLM.

        Include statistiche e sample data per aiutare LLM a capire
        i dati disponibili e fare stime accurate.

        Args:
            personale_df: DataFrame personale
            strutture_df: DataFrame strutture

        Returns:
            String formattata con contesto
        """
        # Statistiche base
        stats = {
            "personale_count": len(personale_df),
            "strutture_count": len(strutture_df),
        }

        # Sedi disponibili (top 10)
        if 'Sede_TNS' in personale_df.columns:
            sedi = personale_df['Sede_TNS'].dropna().unique().tolist()
            stats["sedi_disponibili"] = sedi[:10]
            if len(sedi) > 10:
                stats["sedi_disponibili"].append(f"... (+{len(sedi)-10} altre)")

        # Unità organizzative (top 10)
        if 'Unità Organizzativa' in personale_df.columns:
            uo = personale_df['Unità Organizzativa'].dropna().unique().tolist()
            stats["unita_organizzative"] = uo[:10]
            if len(uo) > 10:
                stats["unita_organizzative"].append(f"... (+{len(uo)-10} altre)")

        # Sample codici strutture (primi 5)
        if 'Codice' in strutture_df.columns:
            codici_strutt = strutture_df['Codice'].dropna().tolist()
            stats["sample_codici_strutture"] = codici_strutt[:5]

        # Sample CF personale (primi 3, per privacy)
        if 'TxCodFiscale' in personale_df.columns:
            cf_sample = personale_df['TxCodFiscale'].dropna().tolist()
            stats["sample_cf_personale"] = cf_sample[:3]

        # Campi disponibili
        fields_info = {
            "campi_personale": personale_df.columns.tolist(),
            "campi_strutture": strutture_df.columns.tolist()
        }

        return f"""
CONTESTO DATI ATTUALI:
{json.dumps(stats, indent=2, ensure_ascii=False)}

CAMPI DISPONIBILI:
{json.dumps(fields_info, indent=2, ensure_ascii=False)}
"""

    def _build_simple_context(
        self,
        personale_df: pd.DataFrame,
        strutture_df: pd.DataFrame
    ) -> str:
        """Costruisce contesto SEMPLIFICATO per ridurre lunghezza prompt"""
        return f"""
Dati disponibili:
- {len(personale_df)} dipendenti (Personale)
- {len(strutture_df)} strutture organizzative
"""

    def _build_simple_prompt(self, user_input: str, context: str) -> str:
        """Costruisce prompt SEMPLIFICATO per LLM"""
        return f"""
{context}

{get_simple_examples()}

COMANDO UTENTE: "{user_input}"

Genera JSON con operation, message, record_type, changes[].
"""

    def _convert_to_bot_response(
        self,
        parsed: Dict[str, Any],
        personale_df: pd.DataFrame,
        strutture_df: pd.DataFrame
    ) -> BotResponse:
        """
        Converte JSON Ollama in BotResponse validato con ChangeProposal reali.

        Esegue filtri su DataFrame per ottenere before_values reali
        e creare ChangeProposal accurati.

        Args:
            parsed: Dict JSON da Ollama
            personale_df: DataFrame personale
            strutture_df: DataFrame strutture

        Returns:
            BotResponse validato con ChangeProposal

        Raises:
            KeyError: Se JSON manca campi obbligatori
            ValueError: Se operation/record_type non validi
        """
        # Valida campi obbligatori
        if 'operation' not in parsed:
            raise KeyError("Campo 'operation' mancante in risposta LLM")
        if 'message' not in parsed:
            raise KeyError("Campo 'message' mancante in risposta LLM")

        # Parse operation
        try:
            operation = OperationType(parsed['operation'])
        except ValueError:
            # Fallback a QUERY per operazioni non riconosciute
            operation = OperationType.QUERY

        # Parse record_type (default: personale)
        record_type_str = parsed.get('record_type', 'personale')
        try:
            record_type = RecordType(record_type_str)
        except ValueError:
            record_type = RecordType.PERSONALE

        # Determina DataFrame target
        target_df = personale_df if record_type == RecordType.PERSONALE else strutture_df

        # Crea ChangeProposal validati
        changes = []
        for change_data in parsed.get('changes', []):
            # Esegui filtro per ottenere before_values reali
            filter_crit = change_data.get('filter_criteria', {})
            matched_records = self._apply_filter(target_df, filter_crit)

            # Se operazione batch e molti record, crea UN change aggregato
            if len(matched_records) > 10 and operation == OperationType.BATCH_UPDATE:
                # Change aggregato per batch grandi
                change = ChangeProposal(
                    change_id=str(uuid.uuid4()),
                    operation=operation,
                    record_type=record_type,
                    filter_criteria=filter_crit,
                    affected_records_count=len(matched_records),
                    before_values=change_data.get('before_values', {}),
                    after_values=change_data.get('after_values', {}),
                    description=change_data.get(
                        'description',
                        f"Modifica batch: {len(matched_records)} record"
                    ),
                    risk_level=change_data.get('risk_level', 'high'),
                    selected=True,
                    validation_status="valid"
                )
                changes.append(change)

            elif operation == OperationType.ADD_RECORD:
                # Add: nessun before_values
                change = ChangeProposal(
                    change_id=str(uuid.uuid4()),
                    operation=operation,
                    record_type=record_type,
                    filter_criteria={},
                    affected_records_count=1,
                    before_values=None,
                    after_values=change_data.get('after_values', {}),
                    description=change_data.get('description', 'Aggiungi record'),
                    risk_level=change_data.get('risk_level', 'low'),
                    selected=True,
                    validation_status="valid"
                )
                changes.append(change)

            else:
                # Update/Delete: un change per ogni record matched
                for idx, row in matched_records.iterrows():
                    change = ChangeProposal(
                        change_id=str(uuid.uuid4()),
                        operation=operation,
                        record_type=record_type,
                        filter_criteria=filter_crit,
                        affected_records_count=len(matched_records),
                        before_values=row.to_dict(),
                        after_values={
                            **row.to_dict(),
                            **change_data.get('after_values', {})
                        },
                        description=change_data.get(
                            'description',
                            f"Modifica record {idx}"
                        ),
                        risk_level=change_data.get('risk_level', 'low'),
                        selected=True,
                        validation_status="valid"
                    )
                    changes.append(change)

                    # Limita a 100 changes per performance UI
                    if len(changes) >= 100:
                        break

        return BotResponse(
            success=parsed.get('success', True),
            message=parsed.get('message', 'Operazione identificata'),
            operation=operation,
            changes=changes,
            query_result=parsed.get('query_result', None)
        )

    def _apply_filter(
        self,
        df: pd.DataFrame,
        criteria: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Applica filtri a DataFrame per identificare record target.

        Supporta:
        - Uguaglianza: {"campo": "valore"}
        - Liste (IN): {"campo": ["valore1", "valore2"]}
        - Null check: {"campo": None}

        Args:
            df: DataFrame da filtrare
            criteria: Dict con criteri filtro

        Returns:
            DataFrame filtrato

        Examples:
            >>> df_filtered = parser._apply_filter(
            ...     personale_df,
            ...     {"Sede_TNS": "Milano"}
            ... )
        """
        if not criteria:
            return df

        mask = pd.Series([True] * len(df), index=df.index)

        for field, value in criteria.items():
            if field not in df.columns:
                # Campo non esiste, skip
                continue

            if value is None:
                # Null check
                mask &= df[field].isna()
            elif isinstance(value, list):
                # IN clause
                mask &= df[field].isin(value)
            else:
                # Equality
                mask &= (df[field] == value)

        return df[mask]
