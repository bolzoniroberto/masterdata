"""
Dashboard UI - Statistiche e alert anomalie
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from services.validator import DataValidator
from services.merger import DBTNSMerger
from ui.styles import render_critical_alert, render_warning_alert

def show_dashboard():
    """Mostra dashboard con statistiche e alert"""

    st.caption("Panoramica generale: dipendenti, strutture, ruoli e anomalie")

    # Get dataframes with safety checks
    personale_df = st.session_state.get('personale_df')
    strutture_df = st.session_state.get('strutture_df')
    db_tns_df = st.session_state.get('db_tns_df')
    db = st.session_state.get('database_handler')

    # Safety check - redirect if no data
    if personale_df is None or strutture_df is None:
        st.warning("⚠️ Nessun dato disponibile. Importa un file Excel per iniziare.")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Avvia Configurazione Guidata", type="primary", use_container_width=True):
                from ui.wizard_onboarding_modal import get_onboarding_wizard
                get_onboarding_wizard().activate()
                st.rerun()
        return

    # === METRICHE PRINCIPALI ===
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="👥 Dipendenti",
            value=len(personale_df),
            help="Totale record in TNS Personale"
        )

    with col2:
        st.metric(
            label="🏗️ Strutture",
            value=len(strutture_df),
            help="Totale unità organizzative"
        )
    
    with col3:
        if db_tns_df is not None:
            st.metric(
                label="📋 DB_TNS",
                value=len(db_tns_df),
                help="Record totali nel merge"
            )
        else:
            st.metric(
                label="📋 DB_TNS",
                value="Non generato",
                help="Usa sezione 'Genera DB_TNS'"
            )
    
    with col4:
        # Calcola posizioni organizzative totali
        # Conta righe con ID presente (sia vacanti che occupate)
        if 'ID' in personale_df.columns:
            total_positions = personale_df['ID'].notna().sum()
            # Conta posizioni vacanti (ID presente ma senza CF)
            if 'TxCodFiscale' in personale_df.columns:
                vacant_positions = personale_df[
                    personale_df['ID'].notna() &
                    personale_df['TxCodFiscale'].isna()
                ].shape[0]
                occupied_positions = total_positions - vacant_positions
                help_text = f"Posizioni totali: {total_positions} ({occupied_positions} occupate, {vacant_positions} vacanti)"
            else:
                help_text = "Posizioni organizzative con ID"
        else:
            total_positions = 0
            help_text = "Colonna ID non trovata"

        st.metric(
            label="📍 Posizioni",
            value=total_positions,
            help=help_text
        )
    
    # === MODIFICHE RECENTI (ultimi 24h) ===

    try:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT change_severity, COUNT(*) as count
            FROM audit_log
            WHERE timestamp >= datetime('now', '-1 day')
            GROUP BY change_severity
        """)
        recent_changes = dict(cursor.fetchall())
        cursor.close()

        if recent_changes:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🔴 CRITICAL", recent_changes.get('CRITICAL', 0))
            with col2:
                st.metric("🟠 HIGH", recent_changes.get('HIGH', 0))
            with col3:
                st.metric("🟡 MEDIUM", recent_changes.get('MEDIUM', 0))
            with col4:
                st.metric("⚪ LOW", recent_changes.get('LOW', 0))

            total_recent = sum(recent_changes.values())
            if total_recent > 0:
                if st.button("📖 Vedi Dettagli Storico", use_container_width=True):
                    st.session_state.page = "🔍 Confronto & Storico"
                    st.rerun()
        else:
            st.info("✅ Nessuna modifica nelle ultime 24 ore")
    except Exception as e:
        st.warning(f"⚠️ Impossibile caricare modifiche recenti: {str(e)}")

    # === ALERT ANOMALIE ===
    
    # Controlla anomalie
    anomalies = []
    
    # 1. Record incompleti Personale
    incomplete_personale = DataValidator.find_incomplete_records_personale(personale_df)
    if len(incomplete_personale) > 0:
        anomalies.append({
            'tipo': 'error',
            'categoria': 'Personale',
            'messaggio': f"{len(incomplete_personale)} record incompleti (campi obbligatori mancanti)",
            'count': len(incomplete_personale),
            'data': incomplete_personale
        })
    
    # 2. Record incompleti Strutture
    incomplete_strutture = DataValidator.find_incomplete_records_strutture(strutture_df)
    if len(incomplete_strutture) > 0:
        anomalies.append({
            'tipo': 'error',
            'categoria': 'Strutture',
            'messaggio': f"{len(incomplete_strutture)} strutture incomplete",
            'count': len(incomplete_strutture),
            'data': incomplete_strutture
        })
    
    # 3. Codici duplicati Personale (WARNING: potrebbe essere legittimo in alcuni casi)
    has_dup_pers, dup_pers = DataValidator.check_duplicate_keys(personale_df, 'TxCodFiscale')
    if has_dup_pers:
        anomalies.append({
            'tipo': 'warning',  # Non bloccante: duplicati potrebbero essere legittimi
            'categoria': 'Personale',
            'messaggio': f"{len(dup_pers)} codici fiscali duplicati (verificare se legittimo)",
            'count': len(dup_pers),
            'data': dup_pers
        })
    
    # 4. Codici duplicati Strutture
    has_dup_strut, dup_strut = DataValidator.check_duplicate_keys(strutture_df, 'Codice')
    if has_dup_strut:
        anomalies.append({
            'tipo': 'error',
            'categoria': 'Strutture',
            'messaggio': f"{len(dup_strut)} codici duplicati",
            'count': len(dup_strut),
            'data': dup_strut
        })
    
    # 5. Strutture orfane (senza dipendenti)
    orphan_structures = DataValidator.find_orphan_structures(strutture_df, personale_df)
    if len(orphan_structures) > 0:
        anomalies.append({
            'tipo': 'warning',
            'categoria': 'Strutture',
            'messaggio': f"{len(orphan_structures)} strutture orfane (senza dipendenti assegnati)",
            'count': len(orphan_structures),
            'data': orphan_structures
        })
    
    # 6. Riferimenti a padri inesistenti
    all_codici_strutture = set(strutture_df['Codice'].dropna().unique())
    padri_personale = set(personale_df['UNITA\' OPERATIVA PADRE '].dropna().unique())
    padri_strutture = set(strutture_df['UNITA\' OPERATIVA PADRE '].dropna().unique())
    
    missing_refs_pers = padri_personale - all_codici_strutture
    missing_refs_strut = padri_strutture - all_codici_strutture
    
    if missing_refs_pers:
        anomalies.append({
            'tipo': 'error',
            'categoria': 'Personale',
            'messaggio': f"{len(missing_refs_pers)} riferimenti a padri inesistenti",
            'count': len(missing_refs_pers),
            'data': pd.DataFrame({'Padre inesistente': list(missing_refs_pers)})
        })
    
    if missing_refs_strut:
        anomalies.append({
            'tipo': 'error',
            'categoria': 'Strutture',
            'messaggio': f"{len(missing_refs_strut)} riferimenti a padri inesistenti",
            'count': len(missing_refs_strut),
            'data': pd.DataFrame({'Padre inesistente': list(missing_refs_strut)})
        })
    
    # === SMART EXPANDERS: Anomalie Critiche sempre visibili ===

    # Separa errori critici da warning
    errors = [a for a in anomalies if a['tipo'] == 'error']
    warnings = [a for a in anomalies if a['tipo'] == 'warning']

    if not anomalies:
        st.success("✅ Nessuna anomalia rilevata! Dati integri.")
    else:
        # ANOMALIE CRITICHE: Sempre visibili, background rosso
        if errors:
            st.markdown("### ❌ Anomalie Critiche")
            st.caption("Richieste azioni immediate per garantire integrità dati")

            for anomaly in errors:
                # Usa render_critical_alert da styles.py
                render_critical_alert(
                    f"**{anomaly['categoria']}**: {anomaly['messaggio']}",
                    details=None  # Non mostriamo dettagli inline per evitare troppo spazio
                )

                # Mostra tabella dati sotto l'alert (compatta)
                st.dataframe(
                    anomaly['data'],
                    use_container_width=True,
                    height=min(200, len(anomaly['data']) * 35 + 50),
                    hide_index=True
                )

                # Link azione diretta se possibile
                if anomaly['categoria'] == 'Personale':
                    st.caption("💡 Vai a **Gestione Personale** per correggere")
                elif anomaly['categoria'] == 'Strutture':
                    st.caption("💡 Vai a **Gestione Strutture** per correggere")

        # ANOMALIE WARNING: Expander collapsed con badge contatore
        if warnings:
            st.markdown("### ⚠️ Anomalie Warning")
            st.caption("Situazioni non critiche che potrebbero richiedere attenzione")

            for anomaly in warnings:
                # Usa render_warning_alert da styles.py
                with st.expander(
                    f"⚠️ {anomaly['categoria']}: {anomaly['messaggio']} ({anomaly['count']} record)",
                    expanded=False
                ):
                    st.dataframe(
                        anomaly['data'],
                        use_container_width=True,
                        height=min(300, len(anomaly['data']) * 35 + 50),
                        hide_index=True
                    )
    
    # === GRAFICI STATISTICHE (in expander collapsed) ===
    with st.expander("📈 Statistiche Distribuzione", expanded=False):
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("#### Distribuzione Dipendenti per Sede")

            # Conta per sede
            sede_counts = personale_df['Sede_TNS'].value_counts().reset_index()
            sede_counts.columns = ['Sede', 'Count']

            if len(sede_counts) > 0:
                fig_sede = px.bar(
                    sede_counts,
                    x='Sede',
                    y='Count',
                    title='',
                    labels={'Count': 'N° Dipendenti', 'Sede': 'Sede'}
                )
                st.plotly_chart(fig_sede, use_container_width=True, key="chart_sede_distribution")
            else:
                st.info("Nessun dato Sede disponibile")

        with col_right:
            st.markdown("#### Distribuzione per Unità Organizzativa (Top 10)")

            # Conta per unità org
            uo_counts = personale_df['Unità Organizzativa'].value_counts().head(10).reset_index()
            uo_counts.columns = ['Unità', 'Count']

            if len(uo_counts) > 0:
                fig_uo = px.bar(
                    uo_counts,
                    x='Count',
                    y='Unità',
                    orientation='h',
                    title='',
                    labels={'Count': 'N° Dipendenti', 'Unità': ''}
                )
                st.plotly_chart(fig_uo, use_container_width=True, key="chart_uo_distribution")
            else:
                st.info("Nessun dato Unità Organizzativa")
    
    # === GERARCHIA STRUTTURE (in expander collapsed) ===

    with st.expander("🌳 Gerarchia Strutture", expanded=False):
        # Statistiche gerarchia
        max_depth = calculate_max_depth(strutture_df)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Profondità massima", max_depth, help="Livelli massimi di gerarchia")
        with col2:
            leaves = count_leaf_structures(strutture_df)
            st.metric("Strutture foglia", leaves, help="Strutture senza figli")
        with col3:
            # Calcola strutture root (senza padre)
            root_count = strutture_df['UNITA\' OPERATIVA PADRE '].isna().sum()
            st.metric("Strutture root", root_count, help="Strutture senza padre")

        # Sunburst chart gerarchia (sample top levels)
        if st.checkbox("Mostra grafico gerarchia (top 3 livelli)", value=False):
            hierarchy_data = build_hierarchy_for_sunburst(strutture_df, max_depth=3)
            if hierarchy_data:
                fig_hierarchy = px.sunburst(
                    hierarchy_data,
                    names='name',
                    parents='parent',
                    title='Gerarchia Strutture Organizzative (primi 3 livelli)'
                )
                st.plotly_chart(fig_hierarchy, use_container_width=True, key="chart_hierarchy_sunburst")
    
    # === DB_TNS STATS ===
    if db_tns_df is not None:
        
        stats = DBTNSMerger.get_statistics(db_tns_df)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Record totali", stats['total_records'])
        with col2:
            st.metric("Strutture", stats['strutture_count'])
        with col3:
            st.metric("Personale", stats['personale_count'])
        with col4:
            st.metric("Codici duplicati", stats['duplicate_codes'])

def calculate_max_depth(strutture_df: pd.DataFrame) -> int:
    """Calcola profondità massima albero strutture"""
    
    # Costruisci mappa padre -> figli
    children_map = {}
    for _, row in strutture_df.iterrows():
        codice = row['Codice']
        padre = row['UNITA\' OPERATIVA PADRE ']
        if pd.notna(padre):
            if padre not in children_map:
                children_map[padre] = []
            children_map[padre].append(codice)
    
    # DFS per calcolare profondità
    def get_depth(codice, visited=None):
        if visited is None:
            visited = set()
        
        if codice in visited:  # Ciclo
            return 0
        
        visited.add(codice)
        
        if codice not in children_map:
            return 1
        
        max_child_depth = 0
        for child in children_map[codice]:
            max_child_depth = max(max_child_depth, get_depth(child, visited.copy()))
        
        return 1 + max_child_depth
    
    # Trova root e calcola profondità massima
    roots = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '].isna()]['Codice'].tolist()
    max_depth = 0
    
    for root in roots:
        depth = get_depth(root)
        max_depth = max(max_depth, depth)
    
    return max_depth

def count_leaf_structures(strutture_df: pd.DataFrame) -> int:
    """Conta strutture foglia (senza figli)"""
    all_codes = set(strutture_df['Codice'].dropna().unique())
    parents = set(strutture_df['UNITA\' OPERATIVA PADRE '].dropna().unique())
    
    # Foglie = codici mai usati come padre
    leaves = all_codes - parents
    return len(leaves)

def build_hierarchy_for_sunburst(strutture_df: pd.DataFrame, max_depth: int = 3) -> list:
    """Costruisce dati per sunburst chart (primi N livelli)"""
    
    # Costruisci lista con name, parent
    hierarchy = []
    
    # Root
    roots = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '].isna()]
    for _, row in roots.iterrows():
        hierarchy.append({
            'name': row['DESCRIZIONE'] or row['Codice'],
            'parent': ''
        })
    
    # BFS per primi N livelli
    visited = set()
    current_level = [r['Codice'] for _, r in roots.iterrows()]
    
    for level in range(max_depth - 1):
        next_level = []
        
        for parent_code in current_level:
            if parent_code in visited:
                continue
            visited.add(parent_code)
            
            # Trova figli
            children = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == parent_code]
            
            for _, child in children.iterrows():
                child_name = child['DESCRIZIONE'] or child['Codice']
                parent_name = strutture_df[strutture_df['Codice'] == parent_code].iloc[0]['DESCRIZIONE']
                if pd.isna(parent_name):
                    parent_name = parent_code
                
                hierarchy.append({
                    'name': child_name,
                    'parent': parent_name
                })
                
                next_level.append(child['Codice'])
        
        current_level = next_level
        if not current_level:
            break
    
    return hierarchy
