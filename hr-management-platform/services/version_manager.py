"""
Version Manager - Gestione versioni database e restore
Permette di creare snapshot e ripristinare versioni precedenti
"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd
from services.database import DatabaseHandler


class VersionManager:
    """
    Gestisce versioni database come snapshot recuperabili.

    Ogni import crea uno snapshot che può essere ripristinato.
    Gli snapshot includono:
    - Dati completi (personale + strutture)
    - Metadata (timestamp, filename, user note, counts)
    - Link a import_version_id per tracciabilità
    """

    def __init__(self, db_handler: DatabaseHandler, snapshots_dir: Path):
        """
        Inizializza version manager.

        Args:
            db_handler: Istanza DatabaseHandler
            snapshots_dir: Directory per salvare snapshot JSON
        """
        self.db = db_handler
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, import_version_id: int,
                       source_filename: str, user_note: Optional[str] = None,
                       certified: bool = False, description: Optional[str] = None) -> str:
        """
        Crea snapshot completo dello stato attuale database.

        Args:
            import_version_id: ID della versione import
            source_filename: Nome file Excel origine
            user_note: Nota opzionale utente
            certified: Se True, è una milestone certificata. Se False, è un checkpoint veloce
            description: Descrizione dettagliata (usata per milestone)

        Returns:
            Path al file snapshot creato
        """
        # Export dati completi da database
        personale_df, strutture_df = self.db.export_to_dataframe()

        # Crea snapshot metadata
        snapshot_data = {
            'metadata': {
                'import_version_id': import_version_id,
                'timestamp': datetime.now().isoformat(),
                'source_filename': source_filename,
                'user_note': user_note or '',
                'certified': certified,
                'description': description or '',
                'personale_count': len(personale_df),
                'strutture_count': len(strutture_df)
            },
            'personale': personale_df.to_dict('records'),
            'strutture': strutture_df.to_dict('records')
        }

        # Salva snapshot su file JSON
        snapshot_filename = f"snapshot_{import_version_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        snapshot_path = self.snapshots_dir / snapshot_filename

        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2, default=str)

        print(f"✅ Snapshot creato: {snapshot_path}")
        return str(snapshot_path)

    def list_snapshots(self) -> List[Dict]:
        """
        Lista tutti gli snapshot disponibili.

        Returns:
            Lista dizionari con info snapshot, ordinati per timestamp DESC
        """
        snapshots = []

        for snapshot_file in self.snapshots_dir.glob("snapshot_*.json"):
            try:
                with open(snapshot_file, 'r', encoding='utf-8') as f:
                    snapshot_data = json.load(f)
                    metadata = snapshot_data['metadata']

                    snapshots.append({
                        'file_path': str(snapshot_file),
                        'filename': snapshot_file.name,
                        'import_version_id': metadata['import_version_id'],
                        'timestamp': metadata['timestamp'],
                        'source_filename': metadata['source_filename'],
                        'user_note': metadata['user_note'],
                        'personale_count': metadata['personale_count'],
                        'strutture_count': metadata['strutture_count']
                    })
            except Exception as e:
                print(f"⚠️ Errore lettura snapshot {snapshot_file}: {str(e)}")
                continue

        # Ordina per timestamp DESC
        snapshots.sort(key=lambda x: x['timestamp'], reverse=True)
        return snapshots

    def restore_snapshot(self, snapshot_file_path: str,
                        create_backup: bool = True) -> Tuple[bool, str]:
        """
        Ripristina database da uno snapshot.

        ATTENZIONE: Questa operazione sovrascrive i dati attuali!

        Args:
            snapshot_file_path: Path al file snapshot da ripristinare
            create_backup: Se True, crea backup dello stato attuale prima di restore

        Returns:
            Tuple (success, message)
        """
        try:
            # 1. Carica snapshot
            with open(snapshot_file_path, 'r', encoding='utf-8') as f:
                snapshot_data = json.load(f)

            metadata = snapshot_data['metadata']
            personale_records = snapshot_data['personale']
            strutture_records = snapshot_data['strutture']

            # 2. Crea backup stato attuale (se richiesto)
            if create_backup:
                backup_note = f"Backup automatico prima restore da snapshot {metadata['import_version_id']}"
                self.create_snapshot(
                    import_version_id=-1,  # ID speciale per backup automatici
                    source_filename="AUTO_BACKUP",
                    user_note=backup_note
                )

            # 3. Converti in DataFrames
            personale_df = pd.DataFrame(personale_records)
            strutture_df = pd.DataFrame(strutture_records)

            # 4. Begin new import version per restore
            restore_note = f"RESTORE da snapshot {metadata['import_version_id']} ({metadata['source_filename']})"
            if metadata['user_note']:
                restore_note += f" - Nota originale: {metadata['user_note']}"

            version_id = self.db.begin_import_version(
                source_filename=f"RESTORE_{metadata['source_filename']}",
                user_note=restore_note
            )

            # 5. Import dati da snapshot (sovrascrive DB)
            p_count, s_count = self.db.import_from_dataframe(personale_df, strutture_df)

            # 6. Complete import version
            changes_summary = json.dumps({
                'operation': 'RESTORE',
                'restored_from_version': metadata['import_version_id'],
                'restored_timestamp': metadata['timestamp']
            })

            self.db.complete_import_version(version_id, p_count, s_count, changes_summary)

            message = (f"✅ Database ripristinato con successo!\n"
                      f"Versione ripristinata: #{metadata['import_version_id']}\n"
                      f"Data snapshot: {metadata['timestamp']}\n"
                      f"Record importati: {p_count} personale, {s_count} strutture")

            return True, message

        except Exception as e:
            return False, f"❌ Errore ripristino snapshot: {str(e)}"

    def delete_snapshot(self, snapshot_file_path: str) -> Tuple[bool, str]:
        """
        Elimina uno snapshot.

        Args:
            snapshot_file_path: Path al file snapshot da eliminare

        Returns:
            Tuple (success, message)
        """
        try:
            snapshot_path = Path(snapshot_file_path)
            if snapshot_path.exists():
                snapshot_path.unlink()
                return True, f"✅ Snapshot eliminato: {snapshot_path.name}"
            else:
                return False, f"❌ Snapshot non trovato: {snapshot_path}"
        except Exception as e:
            return False, f"❌ Errore eliminazione snapshot: {str(e)}"

    def get_snapshot_size_mb(self, snapshot_file_path: str) -> float:
        """Ottieni dimensione snapshot in MB"""
        path = Path(snapshot_file_path)
        if path.exists():
            return path.stat().st_size / (1024 * 1024)
        return 0.0

    def cleanup_old_snapshots(self, keep_last_n: int = 50) -> int:
        """
        Pulisce snapshot vecchi, mantenendo solo gli ultimi N.

        Args:
            keep_last_n: Numero di snapshot da mantenere

        Returns:
            Numero di snapshot eliminati
        """
        snapshots = self.list_snapshots()

        if len(snapshots) <= keep_last_n:
            return 0

        to_delete = snapshots[keep_last_n:]
        deleted_count = 0

        for snapshot in to_delete:
            success, _ = self.delete_snapshot(snapshot['file_path'])
            if success:
                deleted_count += 1

        return deleted_count

    # === CHECKPOINT & MILESTONE HELPERS ===

    def create_checkpoint(self, note: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Crea checkpoint veloce (auto-nota se vuota).

        Checkpoint = snapshot veloce, non certificato, per salvataggi frequenti.

        Args:
            note: Nota opzionale. Se None, usa auto-nota con timestamp

        Returns:
            Tuple (success, message, snapshot_path)
        """
        try:
            # Auto-nota se non fornita
            if not note:
                note = f"Checkpoint {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            # Begin import version
            version_id = self.db.begin_import_version(
                source_filename="CHECKPOINT",
                user_note=note
            )

            # Export dati attuali
            personale_df, strutture_df = self.db.export_to_dataframe()
            p_count = len(personale_df)
            s_count = len(strutture_df)

            # Complete version (checkpoint = certified=False)
            changes_summary = json.dumps({
                'type': 'checkpoint',
                'personale_count': p_count,
                'strutture_count': s_count
            })

            # Update version con certified=False
            cursor = self.db.conn.cursor()
            cursor.execute("""
                UPDATE import_versions
                SET personale_count = ?,
                    strutture_count = ?,
                    changes_summary = ?,
                    completed = 1,
                    completed_at = CURRENT_TIMESTAMP,
                    certified = 0
                WHERE id = ?
            """, (p_count, s_count, changes_summary, version_id))
            self.db.conn.commit()
            cursor.close()

            # Create snapshot
            snapshot_path = self.create_snapshot(
                import_version_id=version_id,
                source_filename="CHECKPOINT",
                user_note=note,
                certified=False
            )

            message = f"✅ Checkpoint #{version_id} creato: {p_count} personale, {s_count} strutture"
            return True, message, snapshot_path

        except Exception as e:
            return False, f"❌ Errore creazione checkpoint: {str(e)}", None

    def create_milestone(self, note: str, description: str) -> Tuple[bool, str, Optional[str]]:
        """
        Crea milestone certificata (nota obbligatoria).

        Milestone = snapshot ufficiale, certificato, con descrizione completa.

        Args:
            note: Nota obbligatoria (titolo milestone)
            description: Descrizione dettagliata cambiamenti

        Returns:
            Tuple (success, message, snapshot_path)
        """
        try:
            if not note or not description:
                return False, "❌ Nota e descrizione sono obbligatorie per milestone", None

            # Begin import version
            version_id = self.db.begin_import_version(
                source_filename="MILESTONE",
                user_note=note
            )

            # Export dati attuali
            personale_df, strutture_df = self.db.export_to_dataframe()
            p_count = len(personale_df)
            s_count = len(strutture_df)

            # Complete version (milestone = certified=True)
            changes_summary = json.dumps({
                'type': 'milestone',
                'description': description,
                'personale_count': p_count,
                'strutture_count': s_count
            })

            # Update version con certified=True e description
            cursor = self.db.conn.cursor()
            cursor.execute("""
                UPDATE import_versions
                SET personale_count = ?,
                    strutture_count = ?,
                    changes_summary = ?,
                    completed = 1,
                    completed_at = CURRENT_TIMESTAMP,
                    certified = 1,
                    description = ?
                WHERE id = ?
            """, (p_count, s_count, changes_summary, description, version_id))
            self.db.conn.commit()
            cursor.close()

            # Create snapshot
            snapshot_path = self.create_snapshot(
                import_version_id=version_id,
                source_filename="MILESTONE",
                user_note=note,
                certified=True,
                description=description
            )

            message = f"🏁 Milestone #{version_id} certificata: {note}"
            return True, message, snapshot_path

        except Exception as e:
            return False, f"❌ Errore creazione milestone: {str(e)}", None

    def compare_versions(self, version_a_id: int, version_b_id: int) -> pd.DataFrame:
        """
        Genera diff tra 2 versioni (snapshot).

        Args:
            version_a_id: ID import_version della versione A
            version_b_id: ID import_version della versione B

        Returns:
            DataFrame con diff (record, campo, valore_a, valore_b, tipo_cambio)
        """
        # Trova snapshot files
        snapshots = self.list_snapshots()
        snapshot_a = next((s for s in snapshots if s['import_version_id'] == version_a_id), None)
        snapshot_b = next((s for s in snapshots if s['import_version_id'] == version_b_id), None)

        if not snapshot_a or not snapshot_b:
            raise ValueError(f"Snapshot non trovato per versione {version_a_id} o {version_b_id}")

        # Carica snapshot
        with open(snapshot_a['file_path'], 'r', encoding='utf-8') as f:
            data_a = json.load(f)
        with open(snapshot_b['file_path'], 'r', encoding='utf-8') as f:
            data_b = json.load(f)

        # Converti in DataFrames
        personale_a = pd.DataFrame(data_a['personale'])
        strutture_a = pd.DataFrame(data_a['strutture'])
        personale_b = pd.DataFrame(data_b['personale'])
        strutture_b = pd.DataFrame(data_b['strutture'])

        # Genera diff
        diff_records = []

        # Diff Personale (chiave: TxCodFiscale)
        cf_a = set(personale_a['TxCodFiscale'].dropna())
        cf_b = set(personale_b['TxCodFiscale'].dropna())

        # Aggiunti
        for cf in (cf_b - cf_a):
            diff_records.append({
                'tipo': 'Personale',
                'tipo_cambio': 'Aggiunto',
                'record': cf,
                'campo': '-',
                'valore_a': '',
                'valore_b': str(personale_b[personale_b['TxCodFiscale'] == cf].iloc[0]['Titolare'])
            })

        # Eliminati
        for cf in (cf_a - cf_b):
            diff_records.append({
                'tipo': 'Personale',
                'tipo_cambio': 'Eliminato',
                'record': cf,
                'campo': '-',
                'valore_a': str(personale_a[personale_a['TxCodFiscale'] == cf].iloc[0]['Titolare']),
                'valore_b': ''
            })

        # Modificati
        for cf in (cf_a & cf_b):
            row_a = personale_a[personale_a['TxCodFiscale'] == cf].iloc[0]
            row_b = personale_b[personale_b['TxCodFiscale'] == cf].iloc[0]

            for col in personale_a.columns:
                if col in ['TxCodFiscale', 'created_at', 'updated_at']:
                    continue
                val_a = str(row_a.get(col, ''))
                val_b = str(row_b.get(col, ''))
                if val_a != val_b:
                    diff_records.append({
                        'tipo': 'Personale',
                        'tipo_cambio': 'Modificato',
                        'record': cf,
                        'campo': col,
                        'valore_a': val_a,
                        'valore_b': val_b
                    })

        # Diff Strutture (chiave: Codice) - SOLO se non vuoto
        if len(strutture_a) > 0 and len(strutture_b) > 0:
            codici_a = set(strutture_a['Codice'].dropna())
            codici_b = set(strutture_b['Codice'].dropna())

            # Aggiunti
            for codice in (codici_b - codici_a):
                diff_records.append({
                    'tipo': 'Struttura',
                    'tipo_cambio': 'Aggiunto',
                    'record': codice,
                    'campo': '-',
                    'valore_a': '',
                    'valore_b': str(strutture_b[strutture_b['Codice'] == codice].iloc[0]['DESCRIZIONE'])
                })

            # Eliminati
            for codice in (codici_a - codici_b):
                diff_records.append({
                    'tipo': 'Struttura',
                    'tipo_cambio': 'Eliminato',
                    'record': codice,
                    'campo': '-',
                    'valore_a': str(strutture_a[strutture_a['Codice'] == codice].iloc[0]['DESCRIZIONE']),
                    'valore_b': ''
                })

            # Modificati
            for codice in (codici_a & codici_b):
                row_a = strutture_a[strutture_a['Codice'] == codice].iloc[0]
                row_b = strutture_b[strutture_b['Codice'] == codice].iloc[0]

                for col in strutture_a.columns:
                    if col in ['Codice', 'created_at', 'updated_at']:
                        continue
                    val_a = str(row_a.get(col, ''))
                    val_b = str(row_b.get(col, ''))
                    if val_a != val_b:
                        diff_records.append({
                            'tipo': 'Struttura',
                            'tipo_cambio': 'Modificato',
                            'record': codice,
                            'campo': col,
                            'valore_a': val_a,
                            'valore_b': val_b
                        })

        return pd.DataFrame(diff_records)
