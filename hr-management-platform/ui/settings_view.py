"""
Vista Impostazioni - Gestione Viste Personalizzate
Permette di creare, modificare ed eliminare viste custom per la Vista Tabellare
"""
import streamlit as st
import json
from pathlib import Path
import pandas as pd


def load_views_config():
    """Carica configurazione viste dal JSON"""
    config_path = Path("config/custom_views.json")

    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Configurazione di default
        return {"viste": []}


def save_views_config(config):
    """Salva configurazione viste nel JSON"""
    config_path = Path("config/custom_views.json")
    config_path.parent.mkdir(exist_ok=True)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_all_columns():
    """Ottieni tutte le colonne disponibili dal dataframe"""
    if 'personale_df' in st.session_state:
        return list(st.session_state.personale_df.columns)
    else:
        # Fallback: leggi da file Excel se disponibile
        return []


def show_settings_view():
    """
    Vista principale Impostazioni con gestione viste personalizzate
    """
    st.markdown("## ⚙️ Impostazioni")
    st.caption("Gestisci le viste personalizzate per la Vista Tabellare")

    # Carica configurazione
    config = load_views_config()
    viste = config.get('viste', [])

    # Inizializza session state
    if 'editing_view_id' not in st.session_state:
        st.session_state.editing_view_id = None
    if 'creating_new_view' not in st.session_state:
        st.session_state.creating_new_view = False

    # === HEADER AZIONI ===
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### 📋 Viste Disponibili")

    with col2:
        if st.button("➕ Nuova Vista", type="primary", use_container_width=True):
            st.session_state.creating_new_view = True
            st.session_state.editing_view_id = None
            st.rerun()

    st.markdown("---")

    # === LISTA VISTE ===
    if not st.session_state.creating_new_view and st.session_state.editing_view_id is None:
        show_views_list(viste)

    # === EDITOR VISTA (creazione o modifica) ===
    elif st.session_state.creating_new_view:
        show_view_editor(None, viste)

    elif st.session_state.editing_view_id:
        # Trova vista da modificare
        vista_to_edit = next(
            (v for v in viste if v['id'] == st.session_state.editing_view_id),
            None
        )
        if vista_to_edit:
            show_view_editor(vista_to_edit, viste)
        else:
            st.error("Vista non trovata")
            st.session_state.editing_view_id = None
            st.rerun()


def show_views_list(viste):
    """
    Mostra lista viste con azioni modifica/elimina
    """
    if not viste:
        st.info("📭 Nessuna vista configurata. Clicca '➕ Nuova Vista' per iniziare.")
        return

    # Raggruppa viste: sistema vs custom
    viste_sistema = [v for v in viste if v.get('bloccata', False)]
    viste_custom = [v for v in viste if not v.get('bloccata', False)]

    # === VISTE DI SISTEMA ===
    if viste_sistema:
        st.markdown("#### 🔒 Viste di Sistema (Non eliminabili)")

        for vista in viste_sistema:
            with st.container():
                col1, col2, col3, col4 = st.columns([0.5, 3, 1, 1])

                with col1:
                    st.markdown(f"<h2 style='margin:0'>{vista['icona']}</h2>", unsafe_allow_html=True)

                with col2:
                    st.markdown(f"**{vista['nome']}**")
                    st.caption(f"{len(vista.get('colonne', []))} colonne")

                with col3:
                    if st.button("👁️ Dettagli", key=f"view_vista_{vista['id']}", use_container_width=True):
                        with st.expander(f"Dettagli: {vista['nome']}", expanded=True):
                            st.markdown(f"**ID:** `{vista['id']}`")
                            st.markdown(f"**Icona:** {vista['icona']}")
                            st.markdown(f"**Colonne ({len(vista.get('colonne', []))}):**")
                            st.write(vista.get('colonne', []))

                with col4:
                    st.button("🔒 Bloccata", disabled=True, use_container_width=True)

                st.markdown("---")

    # === VISTE PERSONALIZZATE ===
    if viste_custom:
        st.markdown("#### ⭐ Viste Personalizzate")

        for vista in viste_custom:
            with st.container():
                col1, col2, col3, col4 = st.columns([0.5, 3, 1, 1])

                with col1:
                    st.markdown(f"<h2 style='margin:0'>{vista['icona']}</h2>", unsafe_allow_html=True)

                with col2:
                    st.markdown(f"**{vista['nome']}**")
                    st.caption(f"{len(vista.get('colonne', []))} colonne")

                with col3:
                    if st.button("✏️ Modifica", key=f"edit_{vista['id']}", use_container_width=True):
                        st.session_state.editing_view_id = vista['id']
                        st.session_state.creating_new_view = False
                        st.rerun()

                with col4:
                    if st.button("🗑️ Elimina", key=f"delete_{vista['id']}", use_container_width=True):
                        delete_view(vista['id'])

                st.markdown("---")

    elif not viste_sistema:
        st.info("📭 Nessuna vista personalizzata. Clicca '➕ Nuova Vista' per crearne una.")


def show_view_editor(vista=None, existing_viste=None):
    """
    Editor per creare o modificare una vista

    Args:
        vista: Vista da modificare (None per nuova vista)
        existing_viste: Lista viste esistenti per validazione
    """
    is_new = vista is None

    st.markdown(f"### {'➕ Crea Nuova Vista' if is_new else f'✏️ Modifica Vista: {vista[\"nome\"]}'}")

    # === FORM EDITOR ===
    with st.form("view_editor_form"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome Vista *",
                value=vista['nome'] if vista else "",
                placeholder="Es: Dati Retribuzione",
                help="Nome descrittivo della vista"
            )

        with col2:
            icona = st.text_input(
                "Icona (Emoji) *",
                value=vista['icona'] if vista else "📋",
                placeholder="📋",
                max_chars=2,
                help="Emoji da mostrare nel tab"
            )

        st.markdown("---")
        st.markdown("#### 📋 Selezione Colonne")

        # Ottieni tutte le colonne disponibili
        all_columns = get_all_columns()

        if not all_columns:
            st.warning("⚠️ Nessuna colonna disponibile. Carica prima i dati.")
            st.form_submit_button("Annulla", on_click=cancel_edit)
            return

        # Colonne attualmente selezionate
        selected_cols = vista.get('colonne', []) if vista else []

        # === COLONNE DISPONIBILI (raggruppate per ambito) ===
        st.markdown("##### Seleziona Colonne")

        # Raggruppa colonne per ambito (usando le viste di sistema come riferimento)
        config = load_views_config()
        sistema_viste = [v for v in config.get('viste', []) if v.get('bloccata', False)]

        # Crea tabs per ambiti
        if sistema_viste:
            tab_names = [f"{v['icona']} {v['nome']}" for v in sistema_viste] + ["🔍 Tutte"]
            tabs = st.tabs(tab_names)

            temp_selected = selected_cols.copy()

            for idx, tab in enumerate(tabs[:-1]):  # Escludi ultimo tab "Tutte"
                with tab:
                    ambito_vista = sistema_viste[idx]
                    ambito_cols = [c for c in ambito_vista.get('colonne', []) if c in all_columns]

                    if not ambito_cols:
                        st.caption("Nessuna colonna in questo ambito")
                        continue

                    # Checkbox per ogni colonna
                    for col in ambito_cols:
                        checked = col in temp_selected
                        if st.checkbox(col, value=checked, key=f"col_{ambito_vista['id']}_{col}"):
                            if col not in temp_selected:
                                temp_selected.append(col)
                        else:
                            if col in temp_selected:
                                temp_selected.remove(col)

            # Tab "Tutte le colonne"
            with tabs[-1]:
                st.caption(f"Totale: {len(all_columns)} colonne")

                search_col = st.text_input("🔍 Cerca colonna", key="search_all_cols")

                filtered_cols = [c for c in all_columns if search_col.lower() in c.lower()] if search_col else all_columns

                for col in filtered_cols[:50]:  # Limita a 50 per performance
                    checked = col in temp_selected
                    if st.checkbox(col, value=checked, key=f"col_all_{col}"):
                        if col not in temp_selected:
                            temp_selected.append(col)
                    else:
                        if col in temp_selected:
                            temp_selected.remove(col)

                if len(filtered_cols) > 50:
                    st.caption(f"Mostrate prime 50 di {len(filtered_cols)} colonne. Usa la ricerca per trovare altre.")

            selected_cols = temp_selected

        else:
            # Fallback: mostra tutte le colonne senza raggruppamento
            selected_cols = st.multiselect(
                "Colonne da includere",
                options=all_columns,
                default=selected_cols
            )

        st.markdown("---")

        # === COLONNE SELEZIONATE (con riordino simulato) ===
        st.markdown("##### 📌 Colonne Selezionate")

        if selected_cols:
            st.caption(f"{len(selected_cols)} colonne selezionate")

            # Mostra colonne selezionate con possibilità di rimuovere
            cols_to_remove = []

            for i, col in enumerate(selected_cols):
                col1, col2, col3 = st.columns([0.5, 4, 1])

                with col1:
                    st.markdown(f"**{i+1}**")

                with col2:
                    st.markdown(f"`{col}`")

                with col3:
                    if st.button("❌", key=f"remove_col_{i}", help="Rimuovi"):
                        cols_to_remove.append(col)

            # Rimuovi colonne marcate
            for col in cols_to_remove:
                selected_cols.remove(col)

            st.info("💡 Tip: L'ordine delle colonne sarà quello mostrato qui sopra")

        else:
            st.warning("⚠️ Seleziona almeno una colonna")

        st.markdown("---")

        # === BOTTONI AZIONE ===
        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button(
                "💾 Salva Vista",
                type="primary",
                use_container_width=True
            )

        with col2:
            cancelled = st.form_submit_button(
                "❌ Annulla",
                use_container_width=True
            )

        # === VALIDAZIONE E SALVATAGGIO ===
        if submitted:
            # Validazione
            if not nome:
                st.error("❌ Il nome della vista è obbligatorio")
                return

            if not icona:
                st.error("❌ L'icona è obbligatoria")
                return

            if not selected_cols:
                st.error("❌ Seleziona almeno una colonna")
                return

            # Genera ID univoco
            if is_new:
                import re
                view_id = re.sub(r'[^a-z0-9_]', '_', nome.lower())

                # Verifica unicità ID
                if any(v['id'] == view_id for v in existing_viste):
                    view_id = f"{view_id}_{len(existing_viste)}"
            else:
                view_id = vista['id']

            # Crea/aggiorna vista
            new_vista = {
                "id": view_id,
                "nome": nome,
                "icona": icona,
                "colonne": selected_cols,
                "bloccata": False
            }

            # Salva configurazione
            config = load_views_config()

            if is_new:
                config['viste'].append(new_vista)
            else:
                # Aggiorna vista esistente
                for i, v in enumerate(config['viste']):
                    if v['id'] == view_id:
                        config['viste'][i] = new_vista
                        break

            save_views_config(config)

            st.success(f"✅ Vista '{nome}' salvata con successo!")
            st.session_state.creating_new_view = False
            st.session_state.editing_view_id = None
            st.rerun()

        if cancelled:
            cancel_edit()


def delete_view(view_id):
    """Elimina una vista personalizzata"""
    config = load_views_config()

    # Trova e rimuovi vista
    config['viste'] = [v for v in config['viste'] if v['id'] != view_id]

    save_views_config(config)

    st.success(f"✅ Vista eliminata")
    st.rerun()


def cancel_edit():
    """Annulla creazione/modifica vista"""
    st.session_state.creating_new_view = False
    st.session_state.editing_view_id = None
    st.rerun()
