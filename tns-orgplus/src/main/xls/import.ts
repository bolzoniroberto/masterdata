import XLSX from 'xlsx'
import { getDb } from '../db/init'
import type Database from 'better-sqlite3'

export interface ImportReport {
  inserted: number
  updated: number
  unchanged: number
  errors: string[]
}

// The 26 exact headers in original order
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

type RawRow = Record<string, unknown>

function isDipendente(row: RawRow): boolean {
  const cf = String(row['TxCodFiscale'] ?? '').trim()
  return cf.length === 16
}

interface NormalizedCdc {
  value: string
  isNumeric: boolean
}

function normalizeCdc(raw: unknown): NormalizedCdc {
  if (raw === null || raw === undefined || raw === '') {
    return { value: '', isNumeric: false }
  }
  if (typeof raw === 'number') {
    // 16100.0 → "16100"
    return { value: String(Math.round(raw)), isNumeric: true }
  }
  return { value: String(raw).trim(), isNumeric: false }
}

function toStr(val: unknown): string | null {
  if (val === null || val === undefined || val === '') return null
  const s = String(val).trim()
  return s === '' ? null : s
}

function writeChangeLog(
  db: Database.Database,
  entityType: string,
  entityId: string,
  entityLabel: string | null,
  action: string,
  fieldName: string | null,
  oldValue: string | null,
  newValue: string | null
): void {
  db.prepare(`
    INSERT INTO change_log (entity_type, entity_id, entity_label, action, field_name, old_value, new_value)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(entityType, entityId, entityLabel, action, fieldName, oldValue, newValue)
}

export function importXls(filePath: string): ImportReport {
  const db = getDb()
  const report: ImportReport = { inserted: 0, updated: 0, unchanged: 0, errors: [] }

  let workbook: XLSX.WorkBook
  try {
    workbook = XLSX.readFile(filePath, { type: 'file', raw: false })
  } catch (e) {
    report.errors.push(`Impossibile leggere il file: ${e}`)
    return report
  }

  // Use DB_TNS as source of truth
  const sheetName = workbook.SheetNames.find(
    (n) => n.trim().toUpperCase() === 'DB_TNS'
  )
  if (!sheetName) {
    report.errors.push('Sheet DB_TNS non trovato nel file')
    return report
  }

  const sheet = workbook.Sheets[sheetName]
  const rows = XLSX.utils.sheet_to_json<RawRow>(sheet, {
    defval: '',
    raw: true // keep numbers as numbers for CDCCOSTO
  })

  if (rows.length === 0) {
    report.errors.push('Sheet DB_TNS vuoto')
    return report
  }

  // Prepare statements
  const insertStruttura = db.prepare(`
    INSERT INTO strutture (
      codice, codice_padre, descrizione, cdc_costo, titolare, livello,
      unita_organizzativa, ruoli_oltre_v, ruoli, viaggiatore, segr_redaz,
      approvatore, cassiere, visualizzatori, segretario, controllore,
      amministrazione, segr_red_assistita, segretario_assistito,
      controllore_assistito, ruoli_afc, ruoli_hr, altri_ruoli, sede_tns, gruppo_sind
    ) VALUES (
      @codice, @codice_padre, @descrizione, @cdc_costo, @titolare, @livello,
      @unita_organizzativa, @ruoli_oltre_v, @ruoli, @viaggiatore, @segr_redaz,
      @approvatore, @cassiere, @visualizzatori, @segretario, @controllore,
      @amministrazione, @segr_red_assistita, @segretario_assistito,
      @controllore_assistito, @ruoli_afc, @ruoli_hr, @altri_ruoli, @sede_tns, @gruppo_sind
    )
  `)

  const updateStruttura = db.prepare(`
    UPDATE strutture SET
      codice_padre = @codice_padre,
      descrizione = @descrizione,
      cdc_costo = @cdc_costo,
      titolare = @titolare,
      livello = @livello,
      unita_organizzativa = @unita_organizzativa,
      ruoli_oltre_v = @ruoli_oltre_v,
      ruoli = @ruoli,
      viaggiatore = @viaggiatore,
      segr_redaz = @segr_redaz,
      approvatore = @approvatore,
      cassiere = @cassiere,
      visualizzatori = @visualizzatori,
      segretario = @segretario,
      controllore = @controllore,
      amministrazione = @amministrazione,
      segr_red_assistita = @segr_red_assistita,
      segretario_assistito = @segretario_assistito,
      controllore_assistito = @controllore_assistito,
      ruoli_afc = @ruoli_afc,
      ruoli_hr = @ruoli_hr,
      altri_ruoli = @altri_ruoli,
      sede_tns = @sede_tns,
      gruppo_sind = @gruppo_sind,
      updated_at = CURRENT_TIMESTAMP,
      deleted_at = NULL
    WHERE codice = @codice
  `)

  const insertDipendente = db.prepare(`
    INSERT INTO dipendenti (
      codice_fiscale, codice_nel_file, unita_organizzativa, cdc_costo, cdc_costo_is_numeric,
      titolare, codice_struttura, livello, ruoli_oltre_v, ruoli, viaggiatore, segr_redaz,
      approvatore, cassiere, visualizzatori, segretario, controllore, amministrazione,
      segr_red_assistita, segretario_assistito, controllore_assistito,
      ruoli_afc, ruoli_hr, altri_ruoli, sede_tns, gruppo_sind
    ) VALUES (
      @codice_fiscale, @codice_nel_file, @unita_organizzativa, @cdc_costo, @cdc_costo_is_numeric,
      @titolare, @codice_struttura, @livello, @ruoli_oltre_v, @ruoli, @viaggiatore, @segr_redaz,
      @approvatore, @cassiere, @visualizzatori, @segretario, @controllore, @amministrazione,
      @segr_red_assistita, @segretario_assistito, @controllore_assistito,
      @ruoli_afc, @ruoli_hr, @altri_ruoli, @sede_tns, @gruppo_sind
    )
  `)

  const updateDipendente = db.prepare(`
    UPDATE dipendenti SET
      codice_nel_file = @codice_nel_file,
      unita_organizzativa = @unita_organizzativa,
      cdc_costo = @cdc_costo,
      cdc_costo_is_numeric = @cdc_costo_is_numeric,
      titolare = @titolare,
      codice_struttura = @codice_struttura,
      livello = @livello,
      ruoli_oltre_v = @ruoli_oltre_v,
      ruoli = @ruoli,
      viaggiatore = @viaggiatore,
      segr_redaz = @segr_redaz,
      approvatore = @approvatore,
      cassiere = @cassiere,
      visualizzatori = @visualizzatori,
      segretario = @segretario,
      controllore = @controllore,
      amministrazione = @amministrazione,
      segr_red_assistita = @segr_red_assistita,
      segretario_assistito = @segretario_assistito,
      controllore_assistito = @controllore_assistito,
      ruoli_afc = @ruoli_afc,
      ruoli_hr = @ruoli_hr,
      altri_ruoli = @altri_ruoli,
      sede_tns = @sede_tns,
      gruppo_sind = @gruppo_sind,
      updated_at = CURRENT_TIMESTAMP,
      deleted_at = NULL
    WHERE codice_fiscale = @codice_fiscale
  `)

  const existsStruttura = db.prepare('SELECT codice FROM strutture WHERE codice = ?')
  const existsDipendente = db.prepare('SELECT codice_fiscale FROM dipendenti WHERE codice_fiscale = ?')

  const runImport = db.transaction(() => {
    let struttureSeen = 0
    let dipendentiSeen = 0

    for (const row of rows) {
      if (isDipendente(row)) {
        dipendentiSeen++
        const cf = String(row['TxCodFiscale']).trim()
        const codiceNelFile = toStr(row['Codice'])
        const codicePadre = toStr(row["UNITA' OPERATIVA PADRE "])
        const { value: cdcVal, isNumeric } = normalizeCdc(row['CDCCOSTO'])

        const data = {
          codice_fiscale: cf,
          codice_nel_file: codiceNelFile,
          unita_organizzativa: toStr(row['Unità Organizzativa']),
          cdc_costo: cdcVal || null,
          cdc_costo_is_numeric: isNumeric ? 1 : 0,
          titolare: toStr(row['Titolare']),
          codice_struttura: codicePadre ?? '',
          livello: toStr(row['LIVELLO']),
          ruoli_oltre_v: toStr(row['RUOLI OltreV']),
          ruoli: toStr(row['RUOLI']),
          viaggiatore: toStr(row['Viaggiatore']),
          segr_redaz: toStr(row['Segr_Redaz']),
          approvatore: toStr(row['Approvatore']),
          cassiere: toStr(row['Cassiere']),
          visualizzatori: toStr(row['Visualizzatori']),
          segretario: toStr(row['Segretario']),
          controllore: toStr(row['Controllore']),
          amministrazione: toStr(row['Amministrazione']),
          segr_red_assistita: toStr(row['SegreteriA Red. Ass.ta']),
          segretario_assistito: toStr(row['SegretariO Ass.to']),
          controllore_assistito: toStr(row['Controllore Ass.to']),
          ruoli_afc: toStr(row['RuoliAFC']),
          ruoli_hr: toStr(row['RuoliHR']),
          altri_ruoli: toStr(row['AltriRuoli']),
          sede_tns: toStr(row['Sede_TNS']),
          gruppo_sind: toStr(row['GruppoSind'])
        }

        const existing = existsDipendente.get(cf)
        if (existing) {
          updateDipendente.run(data)
          report.updated++
        } else {
          insertDipendente.run(data)
          report.inserted++
        }
      } else {
        struttureSeen++
        const codice = toStr(row['Codice'])
        if (!codice) {
          report.errors.push(`Struttura senza codice alla riga ${struttureSeen + dipendentiSeen}`)
          continue
        }

        const data = {
          codice,
          codice_padre: toStr(row["UNITA' OPERATIVA PADRE "]),
          descrizione: toStr(row['DESCRIZIONE']) ?? '',
          cdc_costo: toStr(row['CDCCOSTO']),
          titolare: toStr(row['Titolare']),
          livello: toStr(row['LIVELLO']),
          unita_organizzativa: toStr(row['Unità Organizzativa']),
          ruoli_oltre_v: toStr(row['RUOLI OltreV']),
          ruoli: toStr(row['RUOLI']),
          viaggiatore: toStr(row['Viaggiatore']),
          segr_redaz: toStr(row['Segr_Redaz']),
          approvatore: toStr(row['Approvatore']),
          cassiere: toStr(row['Cassiere']),
          visualizzatori: toStr(row['Visualizzatori']),
          segretario: toStr(row['Segretario']),
          controllore: toStr(row['Controllore']),
          amministrazione: toStr(row['Amministrazione']),
          segr_red_assistita: toStr(row['SegreteriA Red. Ass.ta']),
          segretario_assistito: toStr(row['SegretariO Ass.to']),
          controllore_assistito: toStr(row['Controllore Ass.to']),
          ruoli_afc: toStr(row['RuoliAFC']),
          ruoli_hr: toStr(row['RuoliHR']),
          altri_ruoli: toStr(row['AltriRuoli']),
          sede_tns: toStr(row['Sede_TNS']),
          gruppo_sind: toStr(row['GruppoSind'])
        }

        const existing = existsStruttura.get(codice)
        if (existing) {
          updateStruttura.run(data)
          report.updated++
        } else {
          insertStruttura.run(data)
          report.inserted++
        }
      }
    }
  })

  try {
    runImport()
  } catch (e) {
    report.errors.push(`Errore durante import: ${e}`)
    return report
  }

  // Write import log
  const total = report.inserted + report.updated
  writeChangeLog(
    db,
    'system',
    'import',
    null,
    'IMPORT',
    null,
    null,
    `${report.inserted} inseriti, ${report.updated} aggiornati, ${report.unchanged} invariati`
  )

  return report
}
