"""
DB_ORG Import View

UI for importing the complete DB_ORG Excel file (135 columns).
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile

from services.db_org_import_service import get_db_org_import_service

def render_db_org_import_view():
    """Render DB_ORG import interface"""

    # Info box
    st.info("""
    📋 **Formato file atteso:**
    - File Excel (.xls, .xlsx, .xlsm)
    - Foglio: **DB_ORG**
    - 135 colonne attive organizzate in 6 ambiti:
      1. Organizzativo (A-AC)
      2. Anagrafico/Retributivo (AF-BH)
      3. TNS Travel (BS-CV)
      4. Gerarchie IT (CW-DG)
      5. SGSL Safety (121-126)
      6. GDPR Privacy (127-132)

    💡 **Struttura dati:**
    - Ogni riga con **ID** (colonna AB) rappresenta una **posizione organizzativa**
    - Se la posizione ha **Codice Fiscale** → dipendente assegnato
    - Se la posizione NON ha **Codice Fiscale** → posizione vacante (da importare comunque)
    - Solo le righe senza ID e senza CF vengono ignorate
    """)

    # Step 1: Upload File
    st.markdown("### 📂 Step 1: Carica File Excel")

    # Controlla se c'è un file già caricato dal primo upload
    pre_uploaded_file = st.session_state.get('uploaded_db_org_file', None)

    if pre_uploaded_file:
        st.info(f"📄 File già caricato: **{pre_uploaded_file.name}** ({pre_uploaded_file.size / 1024:.1f} KB)")
        st.caption("File caricato dal primo upload. Puoi procedere con la mappatura o caricare un file diverso.")

        if st.button("🔄 Usa file diverso", use_container_width=True):
            st.session_state.uploaded_db_org_file = None
            st.rerun()

        uploaded_file = pre_uploaded_file
    else:
        uploaded_file = st.file_uploader(
            "Seleziona file DB_ORG",
            type=['xls', 'xlsx', 'xlsm'],
            help="File Excel con foglio DB_ORG"
        )

    if uploaded_file is not None:
        st.success(f"✅ File caricato: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

        # Save to temp file
        import os
        file_extension = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = Path(tmp.name)

        # Step 2: Preview & Validate
        st.markdown("### 📊 Step 2: Anteprima e Validazione")

        try:
            # Read Excel to preview
            with st.spinner("Lettura file in corso..."):
                df = pd.read_excel(tmp_path, sheet_name='DB_ORG', nrows=10)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("📊 Colonne Totali", len(df.columns))

            with col2:
                # Count rows (full file)
                df_full = pd.read_excel(tmp_path, sheet_name='DB_ORG')
                st.metric("👥 Righe Totali", len(df_full))

            with col3:
                st.metric("✅ File Valido", "Pronto per mappatura")

            # === STEP 2.5: MAPPATURA COLONNE ===
            st.markdown("---")
            st.markdown("### 🔗 Step 2.5: Mappatura Colonne")
            st.caption("Associa le colonne del tuo file Excel alle colonne richieste dal sistema")

            # Definisci colonne obbligatorie e opzionali del sistema
            mandatory_columns = {
                'ID': {
                    'description': 'Identificativo univoco posizione organizzativa (chiave primaria)',
                    'excel_col': 'AB',
                    'required': True
                },
                'TxCodFiscale': {
                    'description': 'Codice Fiscale dipendente (se posizione occupata)',
                    'excel_col': 'Varia',
                    'required': False
                },
                'Titolare': {
                    'description': 'Nome e cognome titolare posizione',
                    'excel_col': 'Varia',
                    'required': False
                },
                'Unità Organizzativa': {
                    'description': 'Unità organizzativa primo livello',
                    'excel_col': 'B',
                    'required': True
                },
                'Unità Organizzativa 2': {
                    'description': 'Unità organizzativa secondo livello',
                    'excel_col': 'C',
                    'required': False
                },
                'ReportsTo': {
                    'description': 'Riferimento gerarchico superiore',
                    'excel_col': 'AC',
                    'required': False
                },
                'Cognome': {
                    'description': 'Cognome dipendente',
                    'excel_col': 'Varia',
                    'required': False
                },
                'Nome': {
                    'description': 'Nome dipendente',
                    'excel_col': 'Varia',
                    'required': False
                }
            }

            # Inizializza mapping in session state se non esiste
            if 'column_mapping' not in st.session_state:
                st.session_state.column_mapping = {}

            # Auto-detect: cerca match esatti tra colonne file e colonne sistema
            excel_columns = list(df_full.columns)
            excel_columns_lower = {col.lower(): col for col in excel_columns}

            # Auto-mappa colonne con match esatto (case-insensitive)
            auto_mapped = {}
            for sys_col in mandatory_columns.keys():
                if sys_col.lower() in excel_columns_lower:
                    auto_mapped[sys_col] = excel_columns_lower[sys_col.lower()]
                elif sys_col in excel_columns:
                    auto_mapped[sys_col] = sys_col

            # Merge con mapping esistente (priorità a quello manuale)
            for sys_col in mandatory_columns.keys():
                if sys_col not in st.session_state.column_mapping and sys_col in auto_mapped:
                    st.session_state.column_mapping[sys_col] = auto_mapped[sys_col]

            # Mostra interfaccia mappatura
            st.info(f"📋 **{len(auto_mapped)} colonne auto-mappate** su {len(mandatory_columns)} totali")

            # Tabella mappatura con dropdown
            col_header1, col_header2, col_header3, col_header4 = st.columns([2, 3, 2, 1])
            with col_header1:
                st.markdown("**Colonna Sistema**")
            with col_header2:
                st.markdown("**Descrizione**")
            with col_header3:
                st.markdown("**Colonna File Excel**")
            with col_header4:
                st.markdown("**Tipo**")

            st.markdown("---")

            # Crea dropdown per ogni colonna sistema
            missing_required = []

            for sys_col, info in mandatory_columns.items():
                col1, col2, col3, col4 = st.columns([2, 3, 2, 1])

                with col1:
                    required_marker = "🔴" if info['required'] else "⚪"
                    st.markdown(f"{required_marker} **{sys_col}**")

                with col2:
                    st.caption(info['description'])
                    if info['excel_col'] != 'Varia':
                        st.caption(f"*Colonna Excel tipica: {info['excel_col']}*")

                with col3:
                    # Dropdown per selezionare colonna del file
                    current_mapping = st.session_state.column_mapping.get(sys_col, None)

                    # Opzioni dropdown: "-- Non mappata --" + tutte le colonne Excel
                    options = ["-- Non mappata --"] + excel_columns

                    # Trova indice corrente
                    if current_mapping and current_mapping in excel_columns:
                        default_index = excel_columns.index(current_mapping) + 1
                    else:
                        default_index = 0

                    selected = st.selectbox(
                        f"Mappa {sys_col}",
                        options=options,
                        index=default_index,
                        key=f"map_{sys_col}",
                        label_visibility="collapsed"
                    )

                    # Aggiorna mapping
                    if selected == "-- Non mappata --":
                        if sys_col in st.session_state.column_mapping:
                            del st.session_state.column_mapping[sys_col]
                        if info['required']:
                            missing_required.append(sys_col)
                    else:
                        st.session_state.column_mapping[sys_col] = selected

                with col4:
                    if info['required']:
                        st.markdown("🔴 **OBB**")
                    else:
                        st.markdown("⚪ *Opz*")

            st.markdown("---")

            # Verifica completezza mapping obbligatorio
            if missing_required:
                st.error(f"❌ Colonne obbligatorie non mappate: {', '.join(missing_required)}")
                st.warning("⚠️ Devi mappare tutte le colonne obbligatorie (🔴) prima di procedere")
                return  # Stop qui se manca mapping obbligatorio
            else:
                st.success(f"✅ Tutte le {sum(1 for c in mandatory_columns.values() if c['required'])} colonne obbligatorie sono mappate!")

            # Mostra riepilogo mapping
            with st.expander("📋 Riepilogo Mappatura", expanded=False):
                mapping_df = pd.DataFrame([
                    {
                        'Colonna Sistema': sys_col,
                        'Colonna Excel': st.session_state.column_mapping.get(sys_col, '-- Non mappata --'),
                        'Obbligatoria': '🔴 Sì' if info['required'] else '⚪ No'
                    }
                    for sys_col, info in mandatory_columns.items()
                ])
                st.dataframe(mapping_df, use_container_width=True, hide_index=True)

            # Azioni mappatura
            col_act1, col_act2, col_act3 = st.columns(3)

            with col_act1:
                if st.button("💾 Salva Mappatura", use_container_width=True, help="Salva questa mappatura per futuri import"):
                    # Salva mapping in config file
                    import json

                    config_dir = Path("config")
                    config_dir.mkdir(exist_ok=True)

                    mapping_file = config_dir / "column_mapping.json"
                    with open(mapping_file, 'w', encoding='utf-8') as f:
                        json.dump(st.session_state.column_mapping, f, indent=2, ensure_ascii=False)

                    st.success("✅ Mappatura salvata!")

            with col_act2:
                if st.button("📥 Carica Mappatura", use_container_width=True, help="Carica mappatura salvata"):
                    import json

                    mapping_file = Path("config") / "column_mapping.json"
                    if mapping_file.exists():
                        with open(mapping_file, 'r', encoding='utf-8') as f:
                            saved_mapping = json.load(f)
                            st.session_state.column_mapping = saved_mapping
                            st.success("✅ Mappatura caricata!")
                            st.rerun()
                    else:
                        st.warning("⚠️ Nessuna mappatura salvata trovata")

            with col_act3:
                if st.button("🔄 Reset Mappatura", use_container_width=True, help="Ripristina mappatura automatica"):
                    st.session_state.column_mapping = {}
                    st.success("✅ Mappatura resettata!")
                    st.rerun()

            # Continua con la validazione usando il mapping
            with col3:
                # Check basato sul mapping
                missing_required = [col for col in mandatory_columns.keys()
                                  if mandatory_columns[col]['required']
                                  and col not in st.session_state.column_mapping]

                missing_recommended = [col for col in mandatory_columns.keys()
                                     if not mandatory_columns[col]['required']
                                     and col not in st.session_state.column_mapping]

                if missing_required:
                    st.metric("❌ Mapping Incompleto", len(missing_required), delta=f"-{len(missing_required)}", delta_color="inverse")
                elif missing_recommended:
                    st.metric("⚠️ Colonne Consigliate Mancanti", len(missing_recommended), delta=f"-{len(missing_recommended)}", delta_color="inverse")
                else:
                    st.metric("✅ Struttura Valida", "OK")

            # Preview data

            # Show only key columns for preview
            preview_cols = []
            for col in ['TxCodFiscale', 'Titolare', 'Cognome', 'Nome', 'Area', 'Sede', 'Qualifica', 'RAL']:
                if col in df.columns:
                    preview_cols.append(col)

            if preview_cols:
                st.dataframe(df[preview_cols], use_container_width=True)
            else:
                st.dataframe(df.head(10), use_container_width=True)

            # Validation summary

            checks = []

            # Check 1: Required columns
            if not missing_required:
                checks.append("✅ Tutte le colonne obbligatorie presenti")
            else:
                checks.append(f"❌ Colonne obbligatorie mancanti: {', '.join(missing_required)}")

            if missing_recommended:
                checks.append(f"⚠️ Colonne consigliate mancanti: {', '.join(missing_recommended)}")

            # Check 2: Duplicate CF
            if 'TxCodFiscale' in df_full.columns:
                # Count unique CF that appear more than once
                cf_counts = df_full['TxCodFiscale'].value_counts()
                duplicate_cfs = cf_counts[cf_counts > 1]

                # Check if duplicates are legitimate (AD/CEO can have 2 CF)
                legitimate_duplicates = []
                if len(duplicate_cfs) > 0:
                    for cf in duplicate_cfs.index:
                        # Get rows with this CF
                        cf_rows = df_full[df_full['TxCodFiscale'] == cf]
                        # Check if it's AD/CEO (usually has "CEO", "AD", or specific role)
                        titolari = cf_rows['Titolare'].values if 'Titolare' in cf_rows.columns else []
                        qualifiche = cf_rows['Qualifica'].values if 'Qualifica' in cf_rows.columns else []

                        # Check if any row indicates CEO/AD role
                        is_ad = any(
                            'CEO' in str(t).upper() or 'AMMINISTRATORE DELEGATO' in str(t).upper()
                            for t in titolari
                        ) or any(
                            'DIRIGENTE' in str(q).upper() and len(cf_rows) == 2
                            for q in qualifiche
                        )

                        if is_ad:
                            legitimate_duplicates.append(cf)

                # Filter out legitimate duplicates
                actual_duplicates = [cf for cf in duplicate_cfs.index if cf not in legitimate_duplicates]

                if len(actual_duplicates) == 0:
                    checks.append("✅ Nessun Codice Fiscale duplicato")
                    if len(legitimate_duplicates) > 0:
                        checks.append(f"ℹ️ {len(legitimate_duplicates)} CF legittimamente duplicati (AD/CEO)")
                else:
                    checks.append(f"⚠️ {len(actual_duplicates)} Codice Fiscale duplicati rilevati")
                    if len(legitimate_duplicates) > 0:
                        checks.append(f"ℹ️ {len(legitimate_duplicates)} CF legittimamente duplicati (AD/CEO)")

            # Check 3: Righe completamente vuote (senza CF E senza ID)
            if 'ID' in df_full.columns:
                # Righe veramente vuote: senza CF E senza ID
                truly_empty_rows = df_full[
                    df_full['TxCodFiscale'].isna() &
                    df_full['ID'].isna()
                ].shape[0]

                # Posizioni organizzative: senza CF MA con ID
                vacant_positions = df_full[
                    df_full['TxCodFiscale'].isna() &
                    df_full['ID'].notna()
                ].shape[0]

                if truly_empty_rows == 0:
                    checks.append("✅ Nessuna riga completamente vuota")
                else:
                    checks.append(f"ℹ️ {truly_empty_rows} righe completamente vuote (verranno ignorate)")

                if vacant_positions > 0:
                    checks.append(f"✅ {vacant_positions} posizioni organizzative vacanti (senza dipendente ma con ID - verranno importate)")
            else:
                # Fallback se colonna ID non presente
                empty_rows = df_full[df_full['TxCodFiscale'].isna()].shape[0]
                if empty_rows == 0:
                    checks.append("✅ Nessuna riga vuota")
                else:
                    checks.append(f"ℹ️ {empty_rows} righe senza CF (alcune potrebbero essere posizioni vacanti)")

            for check in checks:
                st.markdown(f"- {check}")

            # Step 3: Import Configuration
            st.markdown("### ⚙️ Step 3: Configurazione Import")

            import_note = st.text_area(
                "💬 Nota Import (opzionale)",
                placeholder="es. Import mensile DB_ORG gennaio 2026",
                help="Descrivi il contenuto o scopo di questo import"
            )

            # === TIPO IMPORT ===
            st.markdown("#### 📋 Tipo di Import")

            st.info("""
            **ℹ️ Logica del File:**
            - Ogni riga con **ID** (colonna AB) è una **posizione organizzativa** valida
            - **Con Codice Fiscale/Titolare** → posizione occupata da un dipendente
            - **Senza Codice Fiscale/Titolare** → posizione vacante (ma **da importare comunque**)
            - Solo le righe completamente vuote (senza ID e senza CF) vengono ignorate

            **Esempio:** "Responsabile Vendite" con ID ma senza dipendente = posizione da importare
            """)

            import_type = st.radio(
                "Seleziona cosa importare:",
                options=[
                    "Tutti i Dati (Dipendenti + Posizioni Organizzative)",
                    "Solo Posizioni Organizzative (senza Titolare, con ID)",
                    "Solo Dipendenti (con Titolare)"
                ],
                index=0,
                help="Le Posizioni Organizzative sono righe senza Titolare ma con ID in colonna AB"
            )

            # Show statistics based on filter
            if 'ID' in df_full.columns and 'Titolare' in df_full.columns:
                # Calculate counts
                posizioni_org = df_full[df_full['Titolare'].isna() & df_full['ID'].notna()]
                dipendenti = df_full[df_full['Titolare'].notna()]

                col_a, col_b, col_c = st.columns(3)

                with col_a:
                    st.metric(
                        "🏢 Posizioni Org",
                        len(posizioni_org),
                        help="Righe senza Titolare ma con ID"
                    )

                with col_b:
                    st.metric(
                        "👤 Dipendenti",
                        len(dipendenti),
                        help="Righe con Titolare"
                    )

                with col_c:
                    if import_type == "Tutti i Dati (Dipendenti + Posizioni Organizzative)":
                        st.metric("📊 Righe da importare", len(posizioni_org) + len(dipendenti))
                    elif import_type == "Solo Posizioni Organizzative (senza Titolare, con ID)":
                        st.metric("📊 Righe da importare", len(posizioni_org))
                    else:
                        st.metric("📊 Righe da importare", len(dipendenti))

            st.markdown("---")

            # === ANTEPRIMA FILTRO ===
            with st.expander("👁️ Anteprima righe che verranno importate", expanded=False):
                preview_df = df_full.copy()

                if import_type == "Solo Posizioni Organizzative (senza Titolare, con ID)":
                    if 'ID' in preview_df.columns and 'Titolare' in preview_df.columns:
                        preview_df = preview_df[
                            preview_df['Titolare'].isna() &
                            preview_df['ID'].notna()
                        ]

                elif import_type == "Solo Dipendenti (con Titolare)":
                    if 'Titolare' in preview_df.columns:
                        preview_df = preview_df[preview_df['Titolare'].notna()]

                # Show preview
                preview_cols = []
                for col in ['ID', 'TxCodFiscale', 'Titolare', 'Cognome', 'Nome', 'Area', 'Sede']:
                    if col in preview_df.columns:
                        preview_cols.append(col)

                if len(preview_df) > 0:
                    st.dataframe(
                        preview_df[preview_cols].head(20),
                        use_container_width=True,
                        height=400
                    )
                    if len(preview_df) > 20:
                        st.caption(f"Mostrate prime 20 di {len(preview_df)} righe")
                else:
                    st.warning("⚠️ Nessuna riga corrisponde al filtro selezionato")

            # Options
            col1, col2 = st.columns(2)

            with col1:
                import_employees = st.checkbox("Importa Dipendenti", value=True)
            with col2:
                import_roles = st.checkbox("Importa Ruoli TNS", value=True)

            # Step 4: Confirm Import
            st.markdown("### ✅ Step 4: Conferma Import")

            if missing_required:
                st.error(f"❌ Impossibile procedere: colonna obbligatoria mancante: {', '.join(missing_required)}")
                st.error("💡 La colonna 'ID' è essenziale per identificare le posizioni organizzative")
                st.stop()

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("🚀 Avvia Import", type="primary", use_container_width=True):
                    with st.spinner("Import in corso... Questo può richiedere alcuni minuti."):
                        try:
                            # === APPLICA MAPPATURA COLONNE ===
                            # NON rinominiamo il DataFrame - passiamo i nomi originali
                            # e aggiorniamo la mappatura interna del servizio
                            df_to_import = df_full.copy()

                            # Crea reverse mapping: System col -> Excel col
                            # (per aggiornare il column_mappings del servizio)
                            reverse_mapping = {
                                sys_col: excel_col
                                for sys_col, excel_col in st.session_state.column_mapping.items()
                            }

                            st.info(f"🔗 Mappatura pronta: {len(reverse_mapping)} colonne configurate")

                            # Debug: mostra mappatura
                            with st.expander("🔍 Debug: Mappatura colonne", expanded=False):
                                st.write("Sistema → Excel:")
                                for sys_col, excel_col in reverse_mapping.items():
                                    st.write(f"  {sys_col} ← {excel_col}")

                                st.write("\nPrime 3 righe (nomi originali):")
                                st.dataframe(df_to_import.head(3), use_container_width=True)

                            # === APPLICA FILTRI ===
                            # Usa i nomi EXCEL (originali) per i filtri
                            excel_id_col = reverse_mapping.get('ID')
                            excel_titolare_col = reverse_mapping.get('Titolare')

                            if import_type == "Solo Posizioni Organizzative (senza Titolare, con ID)":
                                # Filter: righe senza Titolare MA con ID
                                if excel_id_col and excel_titolare_col:
                                    if excel_id_col in df_to_import.columns and excel_titolare_col in df_to_import.columns:
                                        df_to_import = df_to_import[
                                            df_to_import[excel_titolare_col].isna() &
                                            df_to_import[excel_id_col].notna()
                                        ]
                                        st.info(f"🏢 Importando solo {len(df_to_import)} Posizioni Organizzative...")
                                    else:
                                        st.error(f"❌ Colonne '{excel_id_col}' o '{excel_titolare_col}' non trovate nel file")
                                        st.stop()
                                else:
                                    st.error("❌ Mapping 'ID' o 'Titolare' non configurato")
                                    st.stop()

                            elif import_type == "Solo Dipendenti (con Titolare)":
                                # Filter: righe con Titolare
                                if excel_titolare_col and excel_titolare_col in df_to_import.columns:
                                    df_to_import = df_to_import[df_to_import[excel_titolare_col].notna()]
                                    st.info(f"👤 Importando solo {len(df_to_import)} Dipendenti...")
                                else:
                                    st.error(f"❌ Colonna '{excel_titolare_col}' non trovata o non mappata")
                                    st.stop()

                            else:
                                # Import all
                                st.info(f"📊 Importando tutte le {len(df_to_import)} righe...")

                            # === RINOMINA COLONNE PER IL SERVIZIO ===
                            # Il servizio si aspetta nomi standard (chiavi del suo column_mappings)
                            # Mappiamo: Excel user col → Standard col name
                            standard_rename = {}
                            for sys_col, excel_col in reverse_mapping.items():
                                # sys_col è il nome che l'utente ha scelto (es: "ID", "Titolare")
                                # Questi sono già i nomi standard che il servizio si aspetta!
                                standard_rename[excel_col] = sys_col

                            # Rinomina con nomi standard
                            df_to_import = df_to_import.rename(columns=standard_rename)

                            st.success(f"✅ Colonne rinominate per import: {len(standard_rename)}")

                            # Save filtered dataframe to temporary file
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_filtered:
                                df_to_import.to_excel(tmp_filtered.name, sheet_name='DB_ORG', index=False)
                                tmp_filtered_path = Path(tmp_filtered.name)

                            # Execute import
                            import_service = get_db_org_import_service()

                            results = import_service.import_db_org_file(
                                excel_path=tmp_filtered_path,
                                sheet_name='DB_ORG',
                                import_note=import_note
                            )

                            # Show results
                            if results['success']:
                                st.success("✅ Import completato con successo!")

                                # Statistics
                                st.markdown("### 📊 Riepilogo Import")

                                col1, col2, col3, col4 = st.columns(4)

                                with col1:
                                    st.metric("👥 Dipendenti", results['employees_imported'])
                                with col2:
                                    st.metric("🏢 Strutture", results['org_units_imported'])
                                with col3:
                                    st.metric("🌳 Gerarchie", results['hierarchies_assigned'])
                                with col4:
                                    st.metric("🎭 Ruoli", results['roles_assigned'])

                                st.balloons()

                                # Reload app
                                if st.button("🔄 Vai alla Dashboard", use_container_width=True):
                                    st.session_state.current_page = "📊 Dashboard DB_ORG"
                                    st.rerun()

                            else:
                                st.error(f"❌ Import fallito: {results.get('message', 'Errore sconosciuto')}")

                                # Mostra dettagli errore
                                if 'errors' in results and results['errors']:
                                    st.warning("**Errori rilevati:**")
                                    for error in results['errors'][:10]:
                                        st.markdown(f"- {error}")

                                # Mostra traceback se presente
                                if 'traceback' in results:
                                    with st.expander("🔍 Traceback completo"):
                                        st.code(results['traceback'])

                        except Exception as e:
                            st.error(f"❌ Errore durante import: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())

            with col2:
                if st.button("❌ Annulla", use_container_width=True):
                    st.info("Import annullato")
                    st.rerun()

        except Exception as e:
            st.error(f"❌ Errore lettura file: {str(e)}")

    else:
        st.info("👆 Carica un file Excel per iniziare")

    # Help section
    with st.expander("❓ Aiuto & FAQ"):
        st.markdown("""
        **Q: Quale file devo caricare?**
        A: Il file Excel "20250610_ORGANIGRAMMA_TEMPLATE generale.xlsm" o equivalente
           con il foglio "DB_ORG" contenente i 135 campi attivi.

        **Q: Cosa succede ai dati esistenti?**
        A: L'import è additivo. I dipendenti esistenti (stesso CF) non vengono duplicati,
           mentre i nuovi vengono aggiunti.

        **Q: Posso annullare l'import?**
        A: Una volta avviato, l'import completa in transazione. Se fallisce, viene
           eseguito rollback automatico. Puoi sempre usare le versioni per ripristinare.

        **Q: Quanto tempo richiede?**
        A: Circa 1-2 minuti per 5,000 dipendenti.

        **Q: Cosa succede se il file ha errori?**
        A: L'import viene validato prima dell'esecuzione. Se ci sono errori critici,
           l'import non parte. Errori minori su singole righe vengono skippati e loggati.
        """)

if __name__ == "__main__":
    render_db_org_import_view()
