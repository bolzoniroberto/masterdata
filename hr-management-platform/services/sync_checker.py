"""
Servizio per la verifica di consistenza tra database e file Excel.
"""
import pandas as pd
from pathlib import Path
from typing import List, Tuple

from models.sync_models import PersonMismatch, SyncCheckResult
from services.database import DatabaseHandler
from services.excel_handler import ExcelHandler


class SyncChecker:
    """Gestisce la verifica di consistenza tra DB e file Excel."""

    def __init__(self, db_handler: DatabaseHandler):
        """
        Inizializza il checker.

        Args:
            db_handler: Istanza di DatabaseHandler per accedere al DB
        """
        self.db_handler = db_handler

    def check_consistency(
        self,
        excel_path: str,
        excel_sheet_name: str = 'TNS Personale'
    ) -> SyncCheckResult:
        """
        Esegue la verifica completa di consistenza.

        Workflow:
        1. Carica Excel personale (gestendo 26 o 57 colonne)
        2. Carica DB personale
        3. Confronta completezza (presenza persone)
        4. Confronta coerenza responsabili
        5. Ritorna SyncCheckResult

        Args:
            excel_path: Percorso al file Excel
            excel_sheet_name: Nome del foglio Excel (default: 'TNS Personale')

        Returns:
            SyncCheckResult con tutti i dettagli della verifica

        Raises:
            FileNotFoundError: Se il file Excel non esiste
            ValueError: Se il foglio non esiste o colonne obbligatorie mancanti
        """
        # 1. Carica dati Excel
        excel_df = self._load_excel_personale(excel_path, excel_sheet_name)

        # 2. Carica dati DB
        db_df = self._load_db_personale()

        # 3. Verifica completezza
        missing_in_db = self._check_missing_in_db(excel_df, db_df)
        missing_in_excel = self._check_missing_in_excel(excel_df, db_df)

        # 4. Verifica coerenza responsabili
        resp_missing, resp_not_approver = self._check_responsabili_consistency(
            excel_df, db_df
        )

        # 5. Costruisci risultato
        result = SyncCheckResult(
            excel_file=Path(excel_path).name,
            excel_row_count=len(excel_df),
            db_row_count=len(db_df),
            missing_in_db=missing_in_db,
            missing_in_excel=missing_in_excel,
            responsabile_missing=resp_missing,
            responsabile_not_approver=resp_not_approver,
            missing_in_db_count=len(missing_in_db),
            missing_in_excel_count=len(missing_in_excel),
            responsabile_issues_count=len(resp_missing) + len(resp_not_approver),
            total_issues=len(missing_in_db) + len(missing_in_excel) +
                        len(resp_missing) + len(resp_not_approver)
        )

        return result

    def _load_excel_personale(
        self,
        excel_path: str,
        sheet_name: str
    ) -> pd.DataFrame:
        """
        Carica il foglio Personale dal file Excel.

        Gestisce file con 26 colonne (standard) o 57 colonne (puntuale).
        Normalizza i nomi delle colonne e filtra solo le persone (CF non nullo).

        Args:
            excel_path: Percorso al file Excel
            sheet_name: Nome del foglio

        Returns:
            DataFrame con i dati Personale

        Raises:
            FileNotFoundError: Se il file non esiste
            ValueError: Se colonne obbligatorie mancanti
        """
        # Verifica esistenza file
        if not Path(excel_path).exists():
            raise FileNotFoundError(f"File Excel non trovato: {excel_path}")

        # Carica con ExcelHandler
        handler = ExcelHandler(excel_path)

        try:
            # Carica il foglio specifico
            df = pd.read_excel(excel_path, sheet_name=sheet_name, engine='openpyxl')
        except ValueError as e:
            raise ValueError(f"Foglio '{sheet_name}' non trovato nel file: {e}")

        # Normalizza nomi colonne (trim spaces)
        df.columns = df.columns.str.strip()

        # Verifica colonne obbligatorie
        required_cols = ['TxCodFiscale', 'Titolare']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"Colonne obbligatorie mancanti nel foglio '{sheet_name}': {missing_cols}"
            )

        # Filtra solo persone (CF non nullo)
        df_personale = df[df['TxCodFiscale'].notna() & (df['TxCodFiscale'] != '')].copy()

        # Normalizza valori stringa (trim spaces)
        for col in df_personale.select_dtypes(include=['object']).columns:
            df_personale[col] = df_personale[col].astype(str).str.strip()

        # Sostituisci 'nan' con None
        df_personale = df_personale.replace('nan', None)

        return df_personale

    def _load_db_personale(self) -> pd.DataFrame:
        """
        Carica i dati Personale dal database.

        Returns:
            DataFrame con i dati Personale dal DB
        """
        personale_df, _ = self.db_handler.export_to_dataframe()
        return personale_df

    def _check_missing_in_db(
        self,
        excel_df: pd.DataFrame,
        db_df: pd.DataFrame
    ) -> List[PersonMismatch]:
        """
        Trova persone presenti in Excel ma non nel DB.

        Args:
            excel_df: DataFrame Excel
            db_df: DataFrame DB

        Returns:
            Lista di PersonMismatch per persone mancanti nel DB
        """
        mismatches = []

        # Set di CF presenti nel DB
        db_cf_set = set(db_df['TxCodFiscale'].dropna().unique())

        # Trova CF in Excel ma non in DB
        for _, row in excel_df.iterrows():
            cf = row.get('TxCodFiscale')
            if cf and cf not in db_cf_set:
                mismatch = PersonMismatch(
                    TxCodFiscale=cf,
                    codice=row.get('Codice'),
                    titolare=row.get('Titolare', 'N/D'),
                    unita_organizzativa=row.get('Unità Organizzativa'),
                    issue_type='missing_in_db',
                    details=f"Persona presente in Excel ma non trovata nel DB"
                )
                mismatches.append(mismatch)

        return mismatches

    def _check_missing_in_excel(
        self,
        excel_df: pd.DataFrame,
        db_df: pd.DataFrame
    ) -> List[PersonMismatch]:
        """
        Trova persone presenti nel DB ma non in Excel.

        Questo non è necessariamente un errore, ma un'informazione utile.

        Args:
            excel_df: DataFrame Excel
            db_df: DataFrame DB

        Returns:
            Lista di PersonMismatch per persone mancanti in Excel
        """
        mismatches = []

        # Set di CF presenti in Excel
        excel_cf_set = set(excel_df['TxCodFiscale'].dropna().unique())

        # Trova CF in DB ma non in Excel
        for _, row in db_df.iterrows():
            cf = row.get('TxCodFiscale')
            if cf and cf not in excel_cf_set:
                mismatch = PersonMismatch(
                    TxCodFiscale=cf,
                    codice=row.get('Codice'),
                    titolare=row.get('Titolare', 'N/D'),
                    unita_organizzativa=row.get('Unità_Organizzativa'),
                    issue_type='missing_in_excel',
                    details=f"Persona presente nel DB ma non trovata in Excel"
                )
                mismatches.append(mismatch)

        return mismatches

    def _check_responsabili_consistency(
        self,
        excel_df: pd.DataFrame,
        db_df: pd.DataFrame
    ) -> Tuple[List[PersonMismatch], List[PersonMismatch]]:
        """
        Verifica la coerenza dei responsabili.

        Controlla che:
        1. Ogni responsabile assegnato esista nel DB
        2. Ogni responsabile abbia il flag Approvatore=SÌ

        Args:
            excel_df: DataFrame Excel
            db_df: DataFrame DB

        Returns:
            Tuple di (responsabili_missing, responsabili_not_approver)
        """
        responsabili_missing = []
        responsabili_not_approver = []

        # Verifica presenza colonna "Primo responsabile"
        if 'Primo responsabile' not in excel_df.columns:
            # File senza campo responsabile, skip check
            return (responsabili_missing, responsabili_not_approver)

        # Crea dizionario DB: Codice -> (Titolare, Approvatore)
        db_dict = {}
        for _, row in db_df.iterrows():
            codice = row.get('Codice')
            if codice:
                db_dict[codice] = {
                    'titolare': row.get('Titolare', 'N/D'),
                    'approvatore': row.get('Approvatore', '')
                }

        # Per ogni persona con responsabile
        for _, row in excel_df.iterrows():
            resp_codice = row.get('Primo responsabile')

            # Skip se responsabile non assegnato
            if not resp_codice or pd.isna(resp_codice) or resp_codice == '':
                continue

            resp_codice = str(resp_codice).strip()
            if not resp_codice:
                continue

            # Check 1: Responsabile esiste nel DB?
            if resp_codice not in db_dict:
                mismatch = PersonMismatch(
                    TxCodFiscale=row.get('TxCodFiscale'),
                    codice=row.get('Codice'),
                    titolare=row.get('Titolare', 'N/D'),
                    unita_organizzativa=row.get('Unità Organizzativa'),
                    issue_type='responsabile_missing',
                    details=f"Responsabile '{resp_codice}' non trovato nel DB",
                    responsabile_codice=resp_codice,
                    responsabile_nome=row.get('Descrizione primo responsabile', 'N/D')
                )
                responsabili_missing.append(mismatch)
                continue  # Skip check 2 se responsabile non esiste

            # Check 2: Responsabile ha flag Approvatore=SÌ?
            resp_info = db_dict[resp_codice]
            resp_approvatore = resp_info.get('approvatore', '')

            if resp_approvatore != 'SÌ':
                mismatch = PersonMismatch(
                    TxCodFiscale=row.get('TxCodFiscale'),
                    codice=row.get('Codice'),
                    titolare=row.get('Titolare', 'N/D'),
                    unita_organizzativa=row.get('Unità Organizzativa'),
                    issue_type='responsabile_not_approver',
                    details=f"Responsabile '{resp_codice}' esiste ma non ha flag Approvatore=SÌ",
                    responsabile_codice=resp_codice,
                    responsabile_nome=resp_info.get('titolare', 'N/D'),
                    responsabile_approvatore_flag=resp_approvatore if resp_approvatore else 'NO'
                )
                responsabili_not_approver.append(mismatch)

        return (responsabili_missing, responsabili_not_approver)
