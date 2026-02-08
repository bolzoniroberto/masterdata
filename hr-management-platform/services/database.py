"""
Service per gestione SQLite database - Persistenza dati primaria
Database-centric architecture: SQLite source of truth + session state cache
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd
import config


class DatabaseHandler:
    """
    Gestisce operazioni CRUD su SQLite con raw queries.

    Schema:
    - personale: dipendenti con ruoli approvazione (TxCodFiscale unique, not null)
    - strutture: organigramma (Codice unique, not null)
    - audit_log: traccia INSERT/UPDATE/DELETE con before/after values
    - db_tns: cache del merge Strutture + Personale

    Indici su: TxCodFiscale, Codice, UO, Sede, padre per performance
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Inizializza handler database.

        Args:
            db_path: Path al database SQLite. Se None, usa config.DB_PATH
        """
        self.db_path = db_path or config.DB_PATH
        self.db_path = Path(self.db_path)

        # Assicura che la directory esista
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connessione al database
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Dict-like rows
        self.conn.execute("PRAGMA foreign_keys = ON")

    def init_db(self):
        """Crea schema database se non esiste"""
        cursor = self.conn.cursor()

        try:
            # === TABELLA PERSONALE ===
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS personale (
                TxCodFiscale TEXT PRIMARY KEY NOT NULL,
                Titolare TEXT,
                Codice TEXT UNIQUE NOT NULL,
                Unità_Organizzativa TEXT,
                CDCCOSTO TEXT,
                DESCRIZIONE TEXT,
                LIVELLO TEXT,
                UNITA_OPERATIVA_PADRE TEXT,
                RUOLI_OltreV TEXT,
                RUOLI TEXT,
                Viaggiatore TEXT,
                Segr_Redaz TEXT,
                Approvatore TEXT,
                Cassiere TEXT,
                Visualizzatori TEXT,
                Segretario TEXT,
                Controllore TEXT,
                Amministrazione TEXT,
                SegreteriA_Red_Assista TEXT,
                SegretariO_Assista TEXT,
                Controllore_Assita TEXT,
                RuoliAFC TEXT,
                RuoliHR TEXT,
                AltriRuoli TEXT,
                Sede_TNS TEXT,
                GruppoSind TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # === TABELLA STRUTTURE ===
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS strutture (
                Codice TEXT PRIMARY KEY NOT NULL,
                DESCRIZIONE TEXT,
                Unità_Organizzativa TEXT,
                CDCCOSTO TEXT,
                LIVELLO TEXT,
                UNITA_OPERATIVA_PADRE TEXT,
                RUOLI_OltreV TEXT,
                RUOLI TEXT,
                Viaggiatore TEXT,
                Segr_Redaz TEXT,
                Approvatore TEXT,
                Cassiere TEXT,
                Visualizzatori TEXT,
                Segretario TEXT,
                Controllore TEXT,
                Amministrazione TEXT,
                SegreteriA_Red_Assista TEXT,
                SegretariO_Assista TEXT,
                Controllore_Assita TEXT,
                RuoliAFC TEXT,
                RuoliHR TEXT,
                AltriRuoli TEXT,
                Sede_TNS TEXT,
                GruppoSind TEXT,
                TxCodFiscale TEXT DEFAULT NULL,
                Titolare TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # === TABELLA AUDIT LOG ===
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                table_name TEXT NOT NULL,
                operation TEXT NOT NULL,
                record_key TEXT NOT NULL,
                before_values TEXT,
                after_values TEXT,
                user_action TEXT DEFAULT 'system'
            )
            """)

            # === TABELLA DB_TNS (cache) ===
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS db_tns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Codice TEXT,
                TxCodFiscale TEXT,
                Titolare TEXT,
                Unità_Organizzativa TEXT,
                CDCCOSTO TEXT,
                DESCRIZIONE TEXT,
                LIVELLO TEXT,
                UNITA_OPERATIVA_PADRE TEXT,
                RUOLI_OltreV TEXT,
                RUOLI TEXT,
                Viaggiatore TEXT,
                Segr_Redaz TEXT,
                Approvatore TEXT,
                Cassiere TEXT,
                Visualizzatori TEXT,
                Segretario TEXT,
                Controllore TEXT,
                Amministrazione TEXT,
                SegreteriA_Red_Assista TEXT,
                SegretariO_Assista TEXT,
                Controllore_Assita TEXT,
                RuoliAFC TEXT,
                RuoliHR TEXT,
                AltriRuoli TEXT,
                Sede_TNS TEXT,
                GruppoSind TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # === TABELLA IMPORT_VERSIONS (versioning) ===
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS import_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_filename TEXT NOT NULL,
                user_note TEXT,
                personale_count INTEGER,
                strutture_count INTEGER,
                changes_summary TEXT,
                completed BOOLEAN DEFAULT 0,
                completed_at TIMESTAMP
            )
            """)

            # === INDICI PER PERFORMANCE ===
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_personale_cf ON personale(TxCodFiscale)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_personale_codice ON personale(Codice)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_personale_uo ON personale(Unità_Organizzativa)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_personale_sede ON personale(Sede_TNS)")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strutture_codice ON strutture(Codice)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strutture_uo ON strutture(Unità_Organizzativa)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strutture_padre ON strutture(UNITA_OPERATIVA_PADRE)")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_log(table_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_import_timestamp ON import_versions(timestamp)")

            self.conn.commit()
            print(f"✅ Database initialized: {self.db_path}")

        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Errore inizializzazione database: {str(e)}")
        finally:
            cursor.close()

    # === IMPORT VERSIONING ===

    def begin_import_version(self, source_filename: str, user_note: Optional[str] = None) -> int:
        """
        Inizia una nuova versione di import.

        Args:
            source_filename: Nome del file Excel importato
            user_note: Nota opzionale utente

        Returns:
            ID della nuova versione import creata
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO import_versions (source_filename, user_note, completed)
                VALUES (?, ?, 0)
            """, (source_filename, user_note))
            self.conn.commit()
            version_id = cursor.lastrowid
            print(f"✅ Import version #{version_id} iniziata: {source_filename}")
            return version_id
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Errore creazione import version: {str(e)}")
        finally:
            cursor.close()

    def complete_import_version(self, import_version_id: int,
                               personale_count: int, strutture_count: int,
                               changes_summary: str) -> None:
        """
        Completa una versione di import con statistiche.

        Args:
            import_version_id: ID versione da completare
            personale_count: Numero record personale importati
            strutture_count: Numero record strutture importati
            changes_summary: JSON summary delle modifiche (severity counts)
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                UPDATE import_versions
                SET completed = 1, completed_at = CURRENT_TIMESTAMP,
                    personale_count = ?, strutture_count = ?, changes_summary = ?
                WHERE id = ?
            """, (personale_count, strutture_count, changes_summary, import_version_id))
            self.conn.commit()
            print(f"✅ Import version #{import_version_id} completata")
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Errore completamento import version: {str(e)}")
        finally:
            cursor.close()

    def get_import_versions(self, limit: int = 50) -> List[Dict]:
        """
        Ottieni lista delle versioni di import.

        Args:
            limit: Numero massimo versioni da restituire

        Returns:
            Lista dizionari con info versioni
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM import_versions
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"⚠️ Errore lettura import versions: {str(e)}")
            return []
        finally:
            cursor.close()

    # === PERSONALE CRUD ===

    def insert_personale(self, record_dict: Dict) -> bool:
        """
        Inserisci un record dipendente nel database.

        Args:
            record_dict: Dizionario con tutti i campi personale

        Returns:
            True se inserimento riuscito
        """
        cursor = self.conn.cursor()

        try:
            # Normalizza nomi campi da Excel a DB
            db_record = self._normalize_record_to_db(record_dict)

            # Costruisci dinamicamente INSERT
            columns = ', '.join(db_record.keys())
            placeholders = ', '.join(['?' for _ in db_record])
            values = tuple(db_record.values())

            cursor.execute(
                f"INSERT INTO personale ({columns}) VALUES ({placeholders})",
                values
            )

            # Log audit
            self._log_audit('INSERT', 'personale',
                          record_dict.get('TxCodFiscale', 'N/A'),
                          before=None, after=db_record)

            self.conn.commit()
            return True

        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            raise ValueError(f"Errore inserimento personale (duplicate key?): {str(e)}")
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Errore inserimento personale: {str(e)}")
        finally:
            cursor.close()

    def update_personale(self, tx_cod_fiscale: str, updates: Dict) -> bool:
        """
        Aggiorna un record dipendente.

        Args:
            tx_cod_fiscale: Codice fiscale del dipendente da aggiornare
            updates: Dizionario con i campi da aggiornare

        Returns:
            True se aggiornamento riuscito
        """
        cursor = self.conn.cursor()

        try:
            # Normalizza nomi campi
            db_updates = self._normalize_record_to_db(updates)

            # Leggi before state per audit
            cursor.execute("SELECT * FROM personale WHERE TxCodFiscale = ?",
                         (tx_cod_fiscale,))
            before = dict(cursor.fetchone() or {})

            if not before:
                raise ValueError(f"Personale con CF {tx_cod_fiscale} non trovato")

            # Costruisci UPDATE
            set_clause = ', '.join([f"{k} = ?" for k in db_updates.keys()])
            values = list(db_updates.values()) + [tx_cod_fiscale]

            cursor.execute(
                f"UPDATE personale SET {set_clause} WHERE TxCodFiscale = ?",
                values
            )

            # Log audit
            after = before.copy()
            after.update(db_updates)
            self._log_audit('UPDATE', 'personale', tx_cod_fiscale,
                          before=before, after=after)

            self.conn.commit()
            return True

        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Errore aggiornamento personale: {str(e)}")
        finally:
            cursor.close()

    def get_personale_all(self) -> List[Dict]:
        """Leggi tutti i record dipendenti"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM personale ORDER BY Titolare")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()

    def get_personale_by_cf(self, tx_cod_fiscale: str) -> Optional[Dict]:
        """Leggi un dipendente per codice fiscale"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM personale WHERE TxCodFiscale = ?",
                         (tx_cod_fiscale,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()

    def delete_personale(self, tx_cod_fiscale: str) -> bool:
        """Elimina un record dipendente"""
        cursor = self.conn.cursor()
        try:
            # Log before deletion
            cursor.execute("SELECT * FROM personale WHERE TxCodFiscale = ?",
                         (tx_cod_fiscale,))
            before = dict(cursor.fetchone() or {})

            cursor.execute("DELETE FROM personale WHERE TxCodFiscale = ?",
                         (tx_cod_fiscale,))

            self._log_audit('DELETE', 'personale', tx_cod_fiscale,
                          before=before, after=None)

            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Errore eliminazione personale: {str(e)}")
        finally:
            cursor.close()

    # === STRUTTURE CRUD ===

    def insert_struttura(self, record_dict: Dict) -> bool:
        """Inserisci una struttura organizzativa"""
        cursor = self.conn.cursor()

        try:
            db_record = self._normalize_record_to_db(record_dict)

            columns = ', '.join(db_record.keys())
            placeholders = ', '.join(['?' for _ in db_record])
            values = tuple(db_record.values())

            cursor.execute(
                f"INSERT INTO strutture ({columns}) VALUES ({placeholders})",
                values
            )

            self._log_audit('INSERT', 'strutture',
                          record_dict.get('Codice', 'N/A'),
                          before=None, after=db_record)

            self.conn.commit()
            return True

        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            raise ValueError(f"Errore inserimento struttura (duplicate Codice?): {str(e)}")
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Errore inserimento struttura: {str(e)}")
        finally:
            cursor.close()

    def update_struttura(self, codice: str, updates: Dict) -> bool:
        """Aggiorna una struttura organizzativa"""
        cursor = self.conn.cursor()

        try:
            db_updates = self._normalize_record_to_db(updates)

            # Before state
            cursor.execute("SELECT * FROM strutture WHERE Codice = ?", (codice,))
            before = dict(cursor.fetchone() or {})

            if not before:
                raise ValueError(f"Struttura con Codice {codice} non trovata")

            # UPDATE
            set_clause = ', '.join([f"{k} = ?" for k in db_updates.keys()])
            values = list(db_updates.values()) + [codice]

            cursor.execute(
                f"UPDATE strutture SET {set_clause} WHERE Codice = ?",
                values
            )

            # Audit
            after = before.copy()
            after.update(db_updates)
            self._log_audit('UPDATE', 'strutture', codice,
                          before=before, after=after)

            self.conn.commit()
            return True

        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Errore aggiornamento struttura: {str(e)}")
        finally:
            cursor.close()

    def get_strutture_all(self) -> List[Dict]:
        """Leggi tutte le strutture"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM strutture ORDER BY DESCRIZIONE")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()

    def get_struttura_by_codice(self, codice: str) -> Optional[Dict]:
        """Leggi una struttura per codice"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM strutture WHERE Codice = ?", (codice,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()

    def delete_struttura(self, codice: str) -> bool:
        """Elimina una struttura"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM strutture WHERE Codice = ?", (codice,))
            before = dict(cursor.fetchone() or {})

            cursor.execute("DELETE FROM strutture WHERE Codice = ?", (codice,))

            self._log_audit('DELETE', 'strutture', codice,
                          before=before, after=None)

            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Errore eliminazione struttura: {str(e)}")
        finally:
            cursor.close()

    # === IMPORT/EXPORT DATAFRAMES ===

    def import_from_dataframe(self, personale_df: pd.DataFrame,
                             strutture_df: pd.DataFrame) -> Tuple[int, int]:
        """
        Importa dati da DataFrames Excel nel database.
        Cancella dati esistenti e reimposta.

        Args:
            personale_df: DataFrame TNS Personale
            strutture_df: DataFrame TNS Strutture

        Returns:
            Tuple (personale_count, strutture_count) record importati
        """
        cursor = self.conn.cursor()

        try:
            # Pulisci database (audit_log NON viene cancellato per persistenza storico)
            cursor.execute("DELETE FROM personale")
            cursor.execute("DELETE FROM strutture")
            cursor.execute("DELETE FROM db_tns")

            personale_count = 0
            strutture_count = 0

            # Importa Personale
            if personale_df is not None and len(personale_df) > 0:
                for _, row in personale_df.iterrows():
                    record_dict = row.to_dict()
                    # Sostituisci NaN con None
                    record_dict = {k: (None if pd.isna(v) else v)
                                  for k, v in record_dict.items()}

                    try:
                        self.insert_personale(record_dict)
                        personale_count += 1
                    except Exception as e:
                        print(f"⚠️ Skip personale record: {str(e)}")
                        continue

            # Importa Strutture
            if strutture_df is not None and len(strutture_df) > 0:
                for _, row in strutture_df.iterrows():
                    record_dict = row.to_dict()
                    record_dict = {k: (None if pd.isna(v) else v)
                                  for k, v in record_dict.items()}

                    try:
                        self.insert_struttura(record_dict)
                        strutture_count += 1
                    except Exception as e:
                        print(f"⚠️ Skip struttura record: {str(e)}")
                        continue

            self.conn.commit()
            print(f"✅ Import completato: {personale_count} personale, {strutture_count} strutture")
            return personale_count, strutture_count

        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Errore import dataframe: {str(e)}")
        finally:
            cursor.close()

    def export_to_dataframe(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Esporta dati database a DataFrames.

        Returns:
            Tuple (personale_df, strutture_df) con tutti i 26 campi in ordine standard
        """
        try:
            # Leggi personale
            personale_data = self.get_personale_all()
            if personale_data:
                personale_df = pd.DataFrame(personale_data)
            else:
                personale_df = pd.DataFrame(columns=self._get_excel_column_mapping().values())

            # Leggi strutture
            strutture_data = self.get_strutture_all()
            if strutture_data:
                strutture_df = pd.DataFrame(strutture_data)
            else:
                strutture_df = pd.DataFrame(columns=self._get_excel_column_mapping().values())

            # Normalizza nomi colonne da DB back a Excel
            personale_df = self._normalize_dataframe_from_db(personale_df)
            strutture_df = self._normalize_dataframe_from_db(strutture_df)

            return personale_df, strutture_df

        except Exception as e:
            raise Exception(f"Errore export dataframe: {str(e)}")

    # === AUDIT LOG ===

    def get_audit_log(self, limit: int = 100, table_name: Optional[str] = None) -> List[Dict]:
        """
        Leggi audit log.

        Args:
            limit: Max record da leggere
            table_name: Filtra per tabella (personale, strutture, etc.)

        Returns:
            Lista dizionari con audit records
        """
        cursor = self.conn.cursor()
        try:
            if table_name:
                cursor.execute(
                    "SELECT * FROM audit_log WHERE table_name = ? ORDER BY timestamp DESC LIMIT ?",
                    (table_name, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()

    # === HELPER METHODS ===

    def _normalize_record_to_db(self, record_dict: Dict) -> Dict:
        """Normalizza nomi colonne da Excel a DB (underscore per spazi)"""
        mapping = {
            'Unità Organizzativa': 'Unità_Organizzativa',
            'UNITA\' OPERATIVA PADRE ': 'UNITA_OPERATIVA_PADRE',
            'RUOLI OltreV': 'RUOLI_OltreV',
            'Segr_Redaz': 'Segr_Redaz',
            'SegreteriA Red. Ass.ta': 'SegreteriA_Red_Assista',
            'SegretariO Ass.to': 'SegretariO_Assista',
            'Controllore Ass.to': 'Controllore_Assita',
        }

        normalized = {}
        for key, value in record_dict.items():
            normalized_key = mapping.get(key, key)
            normalized[normalized_key] = value

        return normalized

    def _normalize_dataframe_from_db(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalizza nomi colonne da DB back a Excel (inverso di _normalize_record_to_db)"""
        mapping = {
            'Unità_Organizzativa': 'Unità Organizzativa',
            'UNITA_OPERATIVA_PADRE': 'UNITA\' OPERATIVA PADRE ',
            'RUOLI_OltreV': 'RUOLI OltreV',
            'SegreteriA_Red_Assista': 'SegreteriA Red. Ass.ta',
            'SegretariO_Assista': 'SegretariO Ass.to',
            'Controllore_Assita': 'Controllore Ass.to',
        }

        # Rename DB column names to Excel format
        df = df.rename(columns=mapping)
        return df

    def _get_excel_column_mapping(self) -> Dict[str, str]:
        """Mappa da nomi DB a nomi Excel standard"""
        return {
            'Unità_Organizzativa': 'Unità Organizzativa',
            'CDCCOSTO': 'CDCCOSTO',
            'TxCodFiscale': 'TxCodFiscale',
            'DESCRIZIONE': 'DESCRIZIONE',
            'Titolare': 'Titolare',
            'LIVELLO': 'LIVELLO',
            'Codice': 'Codice',
            'UNITA_OPERATIVA_PADRE': 'UNITA\' OPERATIVA PADRE ',
            'RUOLI_OltreV': 'RUOLI OltreV',
            'RUOLI': 'RUOLI',
            'Viaggiatore': 'Viaggiatore',
            'Segr_Redaz': 'Segr_Redaz',
            'Approvatore': 'Approvatore',
            'Cassiere': 'Cassiere',
            'Visualizzatori': 'Visualizzatori',
            'Segretario': 'Segretario',
            'Controllore': 'Controllore',
            'Amministrazione': 'Amministrazione',
            'SegreteriA_Red_Assista': 'SegreteriA Red. Ass.ta',
            'SegretariO_Assista': 'SegretariO Ass.to',
            'Controllore_Assita': 'Controllore Ass.to',
            'RuoliAFC': 'RuoliAFC',
            'RuoliHR': 'RuoliHR',
            'AltriRuoli': 'AltriRuoli',
            'Sede_TNS': 'Sede_TNS',
            'GruppoSind': 'GruppoSind',
        }

    def _log_audit(self, operation: str, table_name: str, record_key: str,
                  before: Optional[Dict] = None, after: Optional[Dict] = None,
                  import_version_id: Optional[int] = None,
                  field_name: Optional[str] = None):
        """Log operazione audit con versioning e severity classification"""
        import json

        cursor = self.conn.cursor()
        try:
            before_json = json.dumps(before, default=str) if before else None
            after_json = json.dumps(after, default=str) if after else None

            # Classifica severity della modifica
            severity = self._classify_change_severity(field_name, before, after)

            # Check if new columns exist (for backward compatibility)
            cursor.execute("PRAGMA table_info(audit_log)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'import_version_id' in columns and 'change_severity' in columns and 'field_name' in columns:
                # New schema with versioning
                cursor.execute("""
                INSERT INTO audit_log
                (table_name, operation, record_key, before_values, after_values,
                 import_version_id, change_severity, field_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (table_name, operation, record_key, before_json, after_json,
                      import_version_id, severity, field_name))
            else:
                # Old schema (backward compatible)
                cursor.execute("""
                INSERT INTO audit_log
                (table_name, operation, record_key, before_values, after_values)
                VALUES (?, ?, ?, ?, ?)
                """, (table_name, operation, record_key, before_json, after_json))

            self.conn.commit()
        except Exception as e:
            print(f"⚠️ Errore logging audit: {str(e)}")
        finally:
            cursor.close()

    def _classify_change_severity(self, field_name: Optional[str],
                                  before: Optional[Dict], after: Optional[Dict]) -> str:
        """
        Classifica la gravità di una modifica basata sul campo modificato.

        CRITICAL: Approvatore, Controllore, Cassiere, Viaggiatore
        HIGH: UNITA_OPERATIVA_PADRE, Codice, DESCRIZIONE
        MEDIUM: Titolare, Unità_Organizzativa, Sede_TNS, Segretario
        LOW: Altri campi
        """
        if not field_name:
            return 'MEDIUM'

        field_lower = field_name.replace('_', ' ').lower()

        # Campi critici per workflow approvazione
        critical_fields = ['approvatore', 'controllore', 'cassiere', 'viaggiatore']
        if any(cf in field_lower for cf in critical_fields):
            return 'CRITICAL'

        # Campi strutturali importanti
        high_fields = ['unita operativa padre', 'codice', 'descrizione']
        if any(hf in field_lower for hf in high_fields):
            return 'HIGH'

        # Campi informativi importanti
        medium_fields = ['titolare', 'unità organizzativa', 'sede', 'segretario']
        if any(mf in field_lower for mf in medium_fields):
            return 'MEDIUM'

        # Tutti gli altri campi
        return 'LOW'

    def close(self):
        """Chiudi connessione database"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()
