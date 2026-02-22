"""
Wrapper per Ollama API locale.
Gestisce comunicazione con server Ollama e generazione risposte LLM.
"""
import requests
import json
from typing import Optional, Dict, Any, Tuple


class OllamaClient:
    """
    Client per Ollama API locale.

    Ollama deve essere installato e in esecuzione su localhost:11434.
    Verifica disponibilità con check_availability() prima di usare generate().
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        timeout: int = 60
    ):
        """
        Inizializza client Ollama.

        Args:
            base_url: URL base Ollama API (default: http://localhost:11434)
            model: Nome modello da usare (default: llama3)
            timeout: Timeout richieste in secondi (default: 60)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout

    def check_availability(self) -> Tuple[bool, str]:
        """
        Verifica disponibilità Ollama server e modello.

        Returns:
            Tuple (is_available, message):
                - is_available: True se server e modello disponibili
                - message: Messaggio descrittivo (success o errore)

        Examples:
            >>> client = OllamaClient()
            >>> available, msg = client.check_availability()
            >>> if available:
            ...     print(f"✅ {msg}")
            ... else:
            ...     print(f"❌ {msg}")
        """
        try:
            # Check server raggiungibile
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )

            if response.status_code != 200:
                return False, f"Ollama server non raggiungibile (HTTP {response.status_code})"

            # Check modello disponibile
            models_data = response.json()
            models = models_data.get('models', [])

            if not models:
                return False, "Nessun modello installato. Esegui: ollama pull llama3"

            # Estrai nomi modelli (rimuovi tag versione)
            model_names = [m['name'].split(':')[0] for m in models]

            if self.model not in model_names:
                available = ", ".join(model_names[:5])  # Primi 5
                if len(model_names) > 5:
                    available += f", ... (+{len(model_names)-5})"
                return False, (
                    f"Modello '{self.model}' non trovato.\n"
                    f"Modelli disponibili: {available}\n"
                    f"Per installare: ollama pull {self.model}"
                )

            return True, f"Ollama OK - modello '{self.model}' disponibile"

        except requests.exceptions.ConnectionError:
            return False, (
                "Ollama non installato o non avviato.\n"
                "Installazione: curl https://ollama.ai/install.sh | sh\n"
                "Avvio: ollama serve"
            )
        except requests.exceptions.Timeout:
            return False, "Timeout connessione Ollama (server non risponde)"
        except Exception as e:
            return False, f"Errore verifica Ollama: {str(e)}"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        format: str = "json"
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Genera risposta da Ollama con output strutturato.

        Args:
            prompt: Prompt utente (user message)
            system_prompt: System prompt opzionale (istruzioni sistema)
            temperature: Temperatura generazione (0.0-1.0). Default 0.1 per output deterministico
            format: Formato output. "json" per JSON strutturato, "" per testo libero

        Returns:
            Tuple (success, parsed_data, error_message):
                - success: True se generazione OK
                - parsed_data: Dict con risposta parsed (se format="json") o {"text": ...}
                - error_message: Messaggio errore (vuoto se success=True)

        Examples:
            >>> client = OllamaClient()
            >>> success, data, error = client.generate(
            ...     prompt="Traduci 'ciao' in inglese",
            ...     format="json"
            ... )
            >>> if success:
            ...     print(data)
            ... else:
            ...     print(f"Errore: {error}")
        """
        try:
            # Costruisci payload richiesta
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,  # Risposta non streaming
                "format": format,
                "options": {
                    "temperature": temperature,
                }
            }

            # Aggiungi system prompt se presente
            if system_prompt:
                payload["system"] = system_prompt

            # Chiamata API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code != 200:
                return False, None, f"Errore HTTP {response.status_code}: {response.text[:200]}"

            # Parse risposta
            result = response.json()
            response_text = result.get('response', '')

            if not response_text:
                return False, None, "Risposta vuota da Ollama"

            # Parse JSON se richiesto
            if format == "json":
                try:
                    parsed = json.loads(response_text)
                    return True, parsed, ""
                except json.JSONDecodeError as e:
                    return False, None, (
                        f"JSON non valido da LLM: {str(e)}\n"
                        f"Risposta: {response_text[:300]}..."
                    )
            else:
                # Ritorna testo come dict
                return True, {"text": response_text}, ""

        except requests.exceptions.Timeout:
            return False, None, (
                f"Timeout dopo {self.timeout}s. "
                "Il comando potrebbe essere troppo complesso. Semplifica la richiesta."
            )
        except requests.exceptions.ConnectionError:
            return False, None, (
                "Connessione persa con Ollama. "
                "Verifica che il server sia ancora in esecuzione: ollama serve"
            )
        except Exception as e:
            return False, None, f"Errore generazione: {type(e).__name__}: {str(e)}"

    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """
        Ottiene informazioni sul modello corrente.

        Returns:
            Dict con info modello o None se errore
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": self.model},
                timeout=5
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception:
            return None
