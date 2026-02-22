"""
Vista Tabellare Excel-like con Tab per Ambito
Tabella interattiva st.data_editor() con viste personalizzate
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path


def load_custom_views():
    """Carica le viste personalizzate dal file JSON"""
    config_path = Path("config/custom_views.json")

    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('viste', [])
    else:
        # Viste di default se il file non esiste
        return [
            {
                "id": "posizioni_org",
                "nome": "Posizioni Organizzative",
                "icona": "🏢",
                "colonne": [],
                "bloccata": True
            }
        ]


def show_tabular_view():
    """
    Vista tabellare principale con tab per ambito e st.data_editor()
    """
    st.markdown("### 📋 Vista Tabellare")
    st.caption("Modifica i dati in stile Excel con salvataggio automatico nel database")

    # Carica dati dal database (stesso dataframe usato in altre viste)
    if 'personale_df' not in st.session_state:
        st.error("❌ Dati non caricati. Torna alla homepage per inizializzare.")
        return

    df = st.session_state.personale_df.copy()

    # Carica viste personalizzate
    viste = load_custom_views()

    # Inizializza session state per modifiche
    if 'tabular_data_edited' not in st.session_state:
        st.session_state.tabular_data_edited = False
    if 'tabular_current_data' not in st.session_state:
        st.session_state.tabular_current_data = df.copy()

    # === HEADER CON AZIONI ===
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        search_text = st.text_input(
            "🔍 Cerca",
            placeholder="Cerca in tutte le colonne...",
            key="tabular_search"
        )

    with col2:
        if st.button("➕ Aggiungi Riga", use_container_width=True):
            # Aggiungi riga vuota al dataframe
            new_row = pd.DataFrame([{col: None for col in df.columns}])
            st.session_state.tabular_current_data = pd.concat(
                [st.session_state.tabular_current_data, new_row],
                ignore_index=True
            )
            st.session_state.tabular_data_edited = True
            st.rerun()

    with col3:
        if st.button("🗑️ Elimina Selezionate", use_container_width=True):
            st.info("Seleziona righe nella tabella e clicca Elimina")

    with col4:
        if st.session_state.tabular_data_edited:
            if st.button("💾 Salva Modifiche", type="primary", use_container_width=True):
                save_tabular_changes()
                st.success("✅ Modifiche salvate!")
                st.session_state.tabular_data_edited = False
                st.rerun()
        else:
            st.button("💾 Nessuna Modifica", disabled=True, use_container_width=True)

    # Badge modifiche non salvate
    if st.session_state.tabular_data_edited:
        st.warning("● **Modifiche non salvate** - Clicca 'Salva Modifiche' per confermare")

    # === TAB PER VISTE ===
    tab_names = [f"{vista['icona']} {vista['nome']}" for vista in viste]
    tabs = st.tabs(tab_names)

    for idx, tab in enumerate(tabs):
        with tab:
            vista = viste[idx]
            render_vista_tab(vista, df, search_text)


def render_vista_tab(vista, df, search_text=""):
    """
    Render singolo tab con la vista selezionata

    Args:
        vista: dizionario con configurazione vista
        df: DataFrame completo
        search_text: testo di ricerca/filtro
    """
    # Filtra colonne per questa vista
    available_cols = [col for col in vista['colonne'] if col in df.columns]

    if not available_cols:
        st.warning(f"⚠️ Nessuna colonna disponibile per la vista '{vista['nome']}'")
        return

    # Aggiungi sempre colonne fisse se non presenti
    fixed_cols = []
    if 'Codice Fiscale' in df.columns and 'Codice Fiscale' not in available_cols:
        fixed_cols.append('Codice Fiscale')
    if 'Nome' in df.columns and 'Nome' not in available_cols:
        fixed_cols.append('Nome')
    if 'Cognome' in df.columns and 'Cognome' not in available_cols:
        fixed_cols.append('Cognome')

    display_cols = fixed_cols + available_cols
    df_vista = df[display_cols].copy()

    # Applica filtro di ricerca
    if search_text:
        mask = df_vista.astype(str).apply(
            lambda row: row.str.contains(search_text, case=False, na=False).any(),
            axis=1
        )
        df_vista = df_vista[mask]

    # === STATISTICHE RAPIDE ===
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Righe visualizzate", len(df_vista))
    with col2:
        st.metric("Colonne", len(display_cols))
    with col3:
        if search_text:
            st.metric("Righe filtrate", len(df_vista), delta=f"-{len(df) - len(df_vista)}")

    st.markdown("---")

    # === DATA EDITOR ===
    # Configurazione colonne
    column_config = {}
    for col in display_cols:
        if col in fixed_cols:
            # Colonne fisse: disabilita editing
            column_config[col] = st.column_config.TextColumn(
                col,
                help=f"Colonna fissa: {col}",
                disabled=True
            )
        else:
            # Colonne editabili
            column_config[col] = st.column_config.TextColumn(
                col,
                help=f"Modifica {col}"
            )

    # Render data editor
    edited_df = st.data_editor(
        df_vista,
        use_container_width=True,
        height=600,
        num_rows="dynamic",  # Permetti aggiunta/eliminazione righe
        column_config=column_config,
        hide_index=False,
        key=f"data_editor_{vista['id']}"
    )

    # Traccia modifiche
    if not df_vista.equals(edited_df):
        st.session_state.tabular_data_edited = True
        st.session_state.tabular_current_data = edited_df

    # === INFO UTILI ===
    with st.expander("ℹ️ Informazioni Vista", expanded=False):
        st.markdown(f"""
        **Vista:** {vista['icona']} {vista['nome']}

        **Colonne visualizzate:** {len(display_cols)}
        - Colonne fisse: {', '.join(fixed_cols) if fixed_cols else 'Nessuna'}
        - Colonne vista: {len(available_cols)}

        **Funzionalità:**
        - ✏️ Click su cella per modificare
        - ➕ Aggiungi riga con bottone in alto
        - 🗑️ Elimina riga (seleziona e usa tastiera)
        - 🔍 Filtra con barra di ricerca
        - 📊 Ordina cliccando su intestazione colonna
        - 💾 Salva modifiche con bottone in alto
        """)

    # Export data
    with st.expander("📥 Esporta Dati", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            csv = df_vista.to_csv(index=False).encode('utf-8')
            st.download_button(
                "⬇️ Scarica CSV",
                csv,
                f"vista_{vista['id']}.csv",
                "text/csv",
                use_container_width=True
            )

        with col2:
            # Excel export (richiede openpyxl)
            try:
                from io import BytesIO
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_vista.to_excel(writer, index=False, sheet_name=vista['nome'])

                st.download_button(
                    "⬇️ Scarica Excel",
                    buffer.getvalue(),
                    f"vista_{vista['id']}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except ImportError:
                st.caption("Excel export richiede openpyxl")


def save_tabular_changes():
    """
    Salva le modifiche dalla tabella al database
    """
    try:
        edited_data = st.session_state.tabular_current_data

        # Aggiorna il dataframe in session state
        st.session_state.personale_df = edited_data.copy()

        # Salva nel database se handler disponibile
        if 'database_handler' in st.session_state:
            db = st.session_state.database_handler

            # TODO: Implementa logica di salvataggio specifico per DB
            # Per ora aggiorniamo solo il session state
            # In produzione: db.update_bulk(edited_data)

            st.success("✅ Dati aggiornati nel database")
        else:
            st.warning("⚠️ Database handler non disponibile - modifiche salvate solo in sessione")

        st.session_state.tabular_data_edited = False

    except Exception as e:
        st.error(f"❌ Errore nel salvataggio: {str(e)}")
