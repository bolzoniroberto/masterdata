import XLSX from 'xlsx'
import { getDb } from '../db/init'

// Exact 26 headers in original order — NEVER modify this
const COLUMN_ORDER = [
  'Unità Organizzativa',
  'CDCCOSTO',
  'TxCodFiscale',
  'DESCRIZIONE',
  'Titolare',
  'LIVELLO',
  'Codice',
  "UNITA' OPERATIVA PADRE ",
  'RUOLI OltreV',
  'RUOLI',
  'Viaggiatore',
  'Segr_Redaz',
  'Approvatore',
  'Cassiere',
  'Visualizzatori',
  'Segretario',
  'Controllore',
  'Amministrazione',
  'SegreteriA Red. Ass.ta',
  'SegretariO Ass.to',
  'Controllore Ass.to',
  'RuoliAFC',
  'RuoliHR',
  'AltriRuoli',
  'Sede_TNS',
  'GruppoSind'
]

type XlsRow = Record<string, string | number | null>

function strOrEmpty(val: string | null): string {
  return val ?? ''
}

function makeStrutturaRow(s: Record<string, unknown>): XlsRow {
  return {
    'Unità Organizzativa': strOrEmpty(s.unita_organizzativa as string),
    'CDCCOSTO': strOrEmpty(s.cdc_costo as string),
    'TxCodFiscale': '',   // strutture hanno CF vuoto
    'DESCRIZIONE': strOrEmpty(s.descrizione as string),
    'Titolare': strOrEmpty(s.titolare as string),
    'LIVELLO': strOrEmpty(s.livello as string),
    'Codice': strOrEmpty(s.codice as string),
    "UNITA' OPERATIVA PADRE ": strOrEmpty(s.codice_padre as string),
    'RUOLI OltreV': strOrEmpty(s.ruoli_oltre_v as string),
    'RUOLI': strOrEmpty(s.ruoli as string),
    'Viaggiatore': strOrEmpty(s.viaggiatore as string),
    'Segr_Redaz': strOrEmpty(s.segr_redaz as string),
    'Approvatore': strOrEmpty(s.approvatore as string),
    'Cassiere': strOrEmpty(s.cassiere as string),
    'Visualizzatori': strOrEmpty(s.visualizzatori as string),
    'Segretario': strOrEmpty(s.segretario as string),
    'Controllore': strOrEmpty(s.controllore as string),
    'Amministrazione': strOrEmpty(s.amministrazione as string),
    'SegreteriA Red. Ass.ta': strOrEmpty(s.segr_red_assistita as string),
    'SegretariO Ass.to': strOrEmpty(s.segretario_assistito as string),
    'Controllore Ass.to': strOrEmpty(s.controllore_assistito as string),
    'RuoliAFC': strOrEmpty(s.ruoli_afc as string),
    'RuoliHR': strOrEmpty(s.ruoli_hr as string),
    'AltriRuoli': strOrEmpty(s.altri_ruoli as string),
    'Sede_TNS': strOrEmpty(s.sede_tns as string),
    'GruppoSind': strOrEmpty(s.gruppo_sind as string)
  }
}

function makeDipendenteRow(d: Record<string, unknown>): XlsRow {
  // CDCCOSTO: restituisce come number se era numeric, altrimenti stringa
  const cdcVal: string | number =
    d.cdc_costo_is_numeric && d.cdc_costo
      ? parseFloat(String(d.cdc_costo))
      : strOrEmpty(d.cdc_costo as string)

  return {
    'Unità Organizzativa': strOrEmpty(d.unita_organizzativa as string),
    'CDCCOSTO': cdcVal,
    'TxCodFiscale': strOrEmpty(d.codice_fiscale as string),
    'DESCRIZIONE': '',
    'Titolare': strOrEmpty(d.titolare as string),
    'LIVELLO': strOrEmpty(d.livello as string),
    // codice_nel_file preserves original Codice (may differ from CF for 4 special records)
    'Codice': strOrEmpty((d.codice_nel_file as string) ?? (d.codice_fiscale as string)),
    "UNITA' OPERATIVA PADRE ": strOrEmpty(d.codice_struttura as string),
    'RUOLI OltreV': strOrEmpty(d.ruoli_oltre_v as string),
    'RUOLI': strOrEmpty(d.ruoli as string),
    'Viaggiatore': strOrEmpty(d.viaggiatore as string),
    'Segr_Redaz': strOrEmpty(d.segr_redaz as string),
    'Approvatore': strOrEmpty(d.approvatore as string),
    'Cassiere': strOrEmpty(d.cassiere as string),
    'Visualizzatori': strOrEmpty(d.visualizzatori as string),
    'Segretario': strOrEmpty(d.segretario as string),
    'Controllore': strOrEmpty(d.controllore as string),
    'Amministrazione': strOrEmpty(d.amministrazione as string),
    'SegreteriA Red. Ass.ta': strOrEmpty(d.segr_red_assistita as string),
    'SegretariO Ass.to': strOrEmpty(d.segretario_assistito as string),
    'Controllore Ass.to': strOrEmpty(d.controllore_assistito as string),
    'RuoliAFC': strOrEmpty(d.ruoli_afc as string),
    'RuoliHR': strOrEmpty(d.ruoli_hr as string),
    'AltriRuoli': strOrEmpty(d.altri_ruoli as string),
    'Sede_TNS': strOrEmpty(d.sede_tns as string),
    'GruppoSind': strOrEmpty(d.gruppo_sind as string)
  }
}

function rowsToSheet(rows: XlsRow[]): XLSX.WorkSheet {
  const ws = XLSX.utils.json_to_sheet(rows, {
    header: COLUMN_ORDER,
    skipHeader: false
  })
  return ws
}

export function exportXls(filePath: string): void {
  const db = getDb()

  // 1. Strutture attive, ordinate per Codice
  const strutture = db
    .prepare('SELECT * FROM strutture WHERE deleted_at IS NULL ORDER BY codice ASC')
    .all() as Record<string, unknown>[]

  // 2. Dipendenti attivi, ordinati per codice_fiscale
  const dipendenti = db
    .prepare('SELECT * FROM dipendenti WHERE deleted_at IS NULL ORDER BY codice_fiscale ASC')
    .all() as Record<string, unknown>[]

  // Build DB_TNS: strutture first, then dipendenti
  const dbTnsRows: XlsRow[] = [
    ...strutture.map(makeStrutturaRow),
    ...dipendenti.map(makeDipendenteRow)
  ]

  // Build TNS Strutture: only strutture
  const struttureRows: XlsRow[] = strutture.map(makeStrutturaRow)

  // Build TNS Personale: only dipendenti
  const personaleRows: XlsRow[] = dipendenti.map(makeDipendenteRow)

  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, rowsToSheet(dbTnsRows), 'DB_TNS')
  XLSX.utils.book_append_sheet(wb, rowsToSheet(personaleRows), 'TNS Personale')
  XLSX.utils.book_append_sheet(wb, rowsToSheet(struttureRows), 'TNS Strutture')

  XLSX.writeFile(wb, filePath, { bookType: 'xls', type: 'file' })

  // Write export log
  const logDb = getDb()
  const fileName = filePath.split('/').pop() ?? filePath
  logDb.prepare(`
    INSERT INTO change_log (entity_type, entity_id, entity_label, action, field_name, old_value, new_value)
    VALUES ('system', 'export', NULL, 'EXPORT', NULL, NULL, ?)
  `).run(fileName)
}
