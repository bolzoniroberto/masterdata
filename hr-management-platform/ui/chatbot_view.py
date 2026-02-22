"""
Vista Streamlit: Assistente Bot Conversazionale HR.
Interfaccia chat per modificare dati usando linguaggio naturale.
"""
import streamlit as st
import pandas as pd
import config
from services.ollama_client import OllamaClient
from services.command_parser import CommandParser
from services.batch_operations import BatchOperations
from models.bot_models import BotResponse, ChangeProposal

def show_chatbot_view():
    """
    Mostra interfaccia bot conversazionale.

    Workflow:
    1. Verifica Ollama disponibile
    2. Chat history con messaggi user/assistant
    3. Input comando → parse → BotResponse
    4. Preview modifiche con checkbox
    5. Apply modifiche selezionate
    6. Proponi salvataggio
    """
    st.caption("Modifica i dati HR usando linguaggio naturale")

    # Inizializza Ollama client e parser in session state
    if 'ollama_client' not in st.session_state:
        st.session_state.ollama_client = OllamaClient(
            base_url=config.OLLAMA_BASE_URL,
            model=config.OLLAMA_MODEL,
            timeout=config.OLLAMA_TIMEOUT
        )

    if 'command_parser' not in st.session_state:
        st.session_state.command_parser = CommandParser(
            st.session_state.ollama_client
        )

    # Verifica disponibilità Ollama
    available, msg = st.session_state.ollama_client.check_availability()

    if not available:
        st.error(f"❌ {msg}")
        st.info("""
**Setup Ollama (richiesto per usare il bot):**

1. **Installazione:**
   ```bash
   curl https://ollama.ai/install.sh | sh
   ```

2. **Avvio server:**
   ```bash
   ollama serve
   ```

3. **Scarica modello (llama3 raccomandato):**
   ```bash
   ollama pull llama3
   ```

4. **Verifica installazione:**
   ```bash
   ollama list
   ```

Il bot sarà disponibile dopo aver completato questi step. Ricarica la pagina.
        """)
        return
    else:
        st.success(f"✅ {msg}")

    # Inizializza chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Inizializza pending changes
    if 'pending_changes' not in st.session_state:
        st.session_state.pending_changes = []

    # Inizializza flag show_save_prompt
    if 'show_save_prompt' not in st.session_state:
        st.session_state.show_save_prompt = False

    # === SEZIONE CHAT HISTORY ===

    # Container per messaggi chat
    chat_container = st.container()

    with chat_container:
        # Mostra history
        for turn in st.session_state.chat_history:
            # Messaggio utente
            with st.chat_message("user"):
                st.write(turn['user_input'])

            # Risposta bot
            with st.chat_message("assistant"):
                st.write(turn['bot_message'])

                # Mostra modifiche applicate se presenti
                if turn.get('changes_applied'):
                    st.success(f"✅ {len(turn['changes_applied'])} modifiche applicate")

    # Input utente
    user_input = st.chat_input(
        "Scrivi comando... (es. 'aggiungi dipendente Mario Rossi con CF RSSMRA80...')"
    )

    if user_input:
        # Mostra messaggio user immediatamente
        with st.chat_message("user"):
            st.write(user_input)

        # Processa comando
        with st.spinner("🤔 Elaborazione comando..."):
            response = st.session_state.command_parser.parse_command(
                user_input,
                st.session_state.personale_df,
                st.session_state.strutture_df
            )

        # Mostra risposta bot
        with st.chat_message("assistant"):
            # Messaggio testuale
            if response.success:
                st.success(response.message)
            else:
                st.error(response.message)

            # Se ci sono modifiche, mostra info
            if response.changes:
                st.session_state.pending_changes = response.changes
                st.info(f"📋 {len(response.changes)} modifiche proposte - vedi sotto per confermare")

            # Se è una query con risultato, mostra risultato
            elif response.query_result:
                with st.expander("🔍 Risultato Query", expanded=True):
                    st.json(response.query_result)

        # Aggiungi a history
        st.session_state.chat_history.append({
            'user_input': user_input,
            'bot_message': response.message,
            'changes_applied': []
        })

        # Rerun per mostrare modifiche pending
        st.rerun()

    # === SEZIONE PREVIEW MODIFICHE ===
    if st.session_state.pending_changes:

        # Crea DataFrame per preview tabellare
        preview_data = []
        for change in st.session_state.pending_changes:
            preview_data.append({
                'Seleziona': change.selected,
                'Operazione': change.operation.value,
                'Descrizione': change.description,
                'Record Impattati': change.affected_records_count,
                'Rischio': change.risk_level,
                'change_id': change.change_id  # Hidden (per mapping)
            })

        preview_df = pd.DataFrame(preview_data)

        # Data editor con checkbox
        edited_preview = st.data_editor(
            preview_df.drop('change_id', axis=1),
            use_container_width=True,
            height=min(400, len(preview_df) * 35 + 38),
            disabled=['Operazione', 'Descrizione', 'Record Impattati', 'Rischio'],
            column_config={
                'Seleziona': st.column_config.CheckboxColumn(
                    'Seleziona',
                    help="Seleziona modifiche da applicare",
                    default=True
                ),
                'Operazione': st.column_config.TextColumn('Operazione', width='small'),
                'Descrizione': st.column_config.TextColumn('Descrizione', width='large'),
                'Record Impattati': st.column_config.NumberColumn('N. Record', width='small'),
                'Rischio': st.column_config.TextColumn('Rischio', width='small')
            },
            hide_index=True
        )

        # Aggiorna selezione checkbox nei ChangeProposal
        for i, change in enumerate(st.session_state.pending_changes):
            change.selected = edited_preview.iloc[i]['Seleziona']

        # Dettagli before/after in expander
        with st.expander("🔍 Dettagli Modifiche (Before → After)"):
            for idx, change in enumerate(st.session_state.pending_changes):
                if change.selected:
                    st.markdown(f"**{idx+1}. {change.description}**")
                    st.caption(f"Change ID: `{change.change_id}` | Risk: {change.risk_level}")

                    col1, col2 = st.columns(2)

                    with col1:
                        if change.before_values:
                            st.json(change.before_values)
                        else:
                            st.info("N/A (nuovo record)")

                    with col2:
                        st.json(change.after_values)

        # Bottoni azione
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            selected_count = sum(1 for c in st.session_state.pending_changes if c.selected)
            if selected_count > 0:
                st.metric("Modifiche selezionate", selected_count)
            else:
                st.warning("Nessuna modifica selezionata")

        with col2:
            if st.button("❌ Annulla", type="secondary", use_container_width=True):
                st.session_state.pending_changes = []
                st.rerun()

        with col3:
            if st.button("✅ Applica", type="primary", use_container_width=True):
                selected_changes = [
                    c for c in st.session_state.pending_changes if c.selected
                ]

                if not selected_changes:
                    st.warning("Seleziona almeno una modifica")
                else:
                    # Applica modifiche
                    with st.spinner("⚙️ Applicazione modifiche..."):
                        # Determina target DataFrame
                        record_type = selected_changes[0].record_type.value

                        if record_type == "personale":
                            df_result, errors = BatchOperations.apply_changes(
                                st.session_state.personale_df,
                                selected_changes,
                                validate=True
                            )
                            if not errors:
                                st.session_state.personale_df = df_result
                        else:
                            df_result, errors = BatchOperations.apply_changes(
                                st.session_state.strutture_df,
                                selected_changes,
                                validate=True
                            )
                            if not errors:
                                st.session_state.strutture_df = df_result

                        # Mostra risultato
                        if errors:
                            st.error(f"⚠️ {len(errors)} errori validazione:")
                            for err in errors[:10]:  # Limita a 10
                                if err['change_id'] == 'validation':
                                    st.error(err['error'])
                                elif err['change_id'] == 'warning':
                                    st.warning(err['error'])
                                else:
                                    st.error(f"Change {err['change_id'][:8]}: {err['error']}")

                            # Se ci sono errori bloccanti, non procedere
                            if any(e['change_id'] == 'validation' for e in errors):
                                st.error("❌ Modifiche non applicate a causa di errori validazione")
                            else:
                                # Solo warning, applica comunque
                                st.success(f"✅ {len(selected_changes)} modifiche applicate (con warning)")

                                # Update history
                                if st.session_state.chat_history:
                                    st.session_state.chat_history[-1]['changes_applied'] = [
                                        c.change_id for c in selected_changes
                                    ]

                                # Clear pending
                                st.session_state.pending_changes = []

                                # Abilita prompt salvataggio
                                st.session_state.show_save_prompt = True

                                st.rerun()

                        else:
                            st.success(f"✅ {len(selected_changes)} modifiche applicate con successo!")

                            # Update history
                            if st.session_state.chat_history:
                                st.session_state.chat_history[-1]['changes_applied'] = [
                                    c.change_id for c in selected_changes
                                ]

                            # Clear pending
                            st.session_state.pending_changes = []

                            # Abilita prompt salvataggio
                            st.session_state.show_save_prompt = True

                            st.rerun()

    # === BANNER SALVATAGGIO POST-APPLY ===
    if st.session_state.get('show_save_prompt', False):
        st.warning("⚠️ **Le modifiche sono applicate in memoria ma non ancora salvate su file!**")

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("💾 Salva su File Excel", type="primary", use_container_width=True):
                try:
                    with st.spinner("💾 Salvataggio in corso..."):
                        saved_path = st.session_state.excel_handler.save_data(
                            st.session_state.personale_df,
                            st.session_state.strutture_df,
                            st.session_state.db_tns_df,
                            create_backup=True
                        )

                    st.success(f"✅ Dati salvati con successo!")
                    st.info(f"📁 File: {saved_path}")
                    st.info("📦 Backup automatico creato in data/backups/")

                    # Disabilita prompt
                    st.session_state.show_save_prompt = False

                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Errore salvataggio: {str(e)}")

        with col2:
            if st.button("⏭️ Continua Senza Salvare", type="secondary", use_container_width=True):
                st.session_state.show_save_prompt = False
                st.rerun()

    # === SUGGERIMENTI USO ===
    if not st.session_state.chat_history and not st.session_state.pending_changes:
        st.markdown("### 💡 Esempi di Comandi")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
**Aggiungi dipendente:**
- "Aggiungi dipendente Mario Rossi, CF RSSMRA80A01H501Z, codice MARIO001, unità Marketing"

**Modifica singolo:**
- "Cambia la sede di Mario Rossi (CF RSSMRA80A01H501Z) in Napoli"
- "Aggiorna il centro di costo del dipendente MARIO001 a CDC_001"
            """)

        with col2:
            st.markdown("""
**Operazioni batch:**
- "Sposta tutti i dipendenti della sede Milano a Roma"
- "Assegna gruppo sindacale CGIL a tutti i dipendenti dell'unità HR"

**Query:**
- "Mostra dipendenti senza sede assegnata"
- "Quanti dipendenti ci sono a Milano?"
            """)

        st.info("""
**Tips:**
- Sii specifico: includi CF per identificare dipendenti univocamente
- Per batch: usa filtri chiari ("tutti i dipendenti di [sede/unità]")
- Rivedi sempre la preview prima di applicare modifiche
- Il bot chiederà chiarimenti se il comando è ambiguo
        """)
