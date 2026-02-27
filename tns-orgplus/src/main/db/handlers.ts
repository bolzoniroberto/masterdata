import { ipcMain, dialog, app } from 'electron'
import path from 'path'
import { getDb } from './init'
import { importXls } from '../xls/import'
import { exportXls } from '../xls/export'

// Development path for XLS file
const DEV_XLS_PATH =
  '/Users/robertobolzoni/Downloads/TNS24 Gruppo Il Sole 24 ORE ORG PLUS 25 11 06 (3).xls'

function writeChangeLog(
  entityType: string,
  entityId: string,
  entityLabel: string | null,
  action: string,
  fieldName: string | null,
  oldValue: string | null,
  newValue: string | null
): void {
  const db = getDb()
  db.prepare(`
    INSERT INTO change_log (entity_type, entity_id, entity_label, action, field_name, old_value, new_value)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(entityType, entityId, entityLabel, action, fieldName, oldValue, newValue)
}

export function registerHandlers(): void {
  // ──────────────────────────────────────────────────────────────
  // STRUTTURE
  // ──────────────────────────────────────────────────────────────

  ipcMain.handle('strutture:list', (_event, showDeleted = false) => {
    const db = getDb()
    const where = showDeleted ? '' : 'WHERE deleted_at IS NULL'
    const strutture = db
      .prepare(`
        SELECT s.*,
          (SELECT COUNT(*) FROM dipendenti d WHERE d.codice_struttura = s.codice AND d.deleted_at IS NULL) as dipendenti_count
        FROM strutture s
        ${where}
        ORDER BY s.codice ASC
      `)
      .all()
    return strutture
  })

  ipcMain.handle('strutture:get', (_event, codice: string) => {
    const db = getDb()
    return db
      .prepare(`
        SELECT s.*,
          (SELECT COUNT(*) FROM dipendenti d WHERE d.codice_struttura = s.codice AND d.deleted_at IS NULL) as dipendenti_count
        FROM strutture s
        WHERE s.codice = ?
      `)
      .get(codice)
  })

  ipcMain.handle('strutture:getDipendenti', (_event, codice: string) => {
    const db = getDb()
    return db
      .prepare('SELECT * FROM dipendenti WHERE codice_struttura = ? AND deleted_at IS NULL ORDER BY titolare ASC')
      .all(codice)
  })

  ipcMain.handle('strutture:create', (_event, data: Record<string, unknown>) => {
    const db = getDb()
    // Check codice uniqueness
    const existing = db.prepare('SELECT codice FROM strutture WHERE codice = ?').get(data.codice)
    if (existing) {
      return { success: false, error: 'DUPLICATE_CODICE', message: `Il codice "${data.codice}" è già in uso` }
    }

    db.prepare(`
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
    `).run(data)

    writeChangeLog('struttura', String(data.codice), data.descrizione as string, 'CREATE', null, null, null)
    return { success: true }
  })

  ipcMain.handle('strutture:update', (_event, codice: string, data: Record<string, unknown>) => {
    const db = getDb()

    // Get current values for change log
    const current = db.prepare('SELECT * FROM strutture WHERE codice = ?').get(codice) as Record<string, unknown>
    if (!current) {
      return { success: false, error: 'NOT_FOUND' }
    }

    const updateFields = [
      'codice_padre', 'descrizione', 'cdc_costo', 'titolare', 'livello',
      'unita_organizzativa', 'ruoli_oltre_v', 'ruoli', 'viaggiatore', 'segr_redaz',
      'approvatore', 'cassiere', 'visualizzatori', 'segretario', 'controllore',
      'amministrazione', 'segr_red_assistita', 'segretario_assistito',
      'controllore_assistito', 'ruoli_afc', 'ruoli_hr', 'altri_ruoli', 'sede_tns', 'gruppo_sind'
    ]

    // Merge current values with incoming data so missing fields don't cause
    // "Missing named parameter" errors in better-sqlite3
    const merged: Record<string, unknown> = { codice }
    for (const field of updateFields) {
      merged[field] = field in data ? (data[field] ?? null) : (current[field] ?? null)
    }

    db.prepare(`
      UPDATE strutture SET
        ${updateFields.map((f) => `${f} = @${f}`).join(',\n        ')},
        updated_at = CURRENT_TIMESTAMP
      WHERE codice = @codice
    `).run(merged)

    // Log changed fields
    for (const field of updateFields) {
      const oldVal = current[field] !== undefined ? String(current[field]) : null
      const newVal = data[field] !== undefined && data[field] !== null ? String(data[field]) : null
      if (oldVal !== newVal) {
        writeChangeLog(
          'struttura',
          codice,
          (current.descrizione as string) ?? codice,
          'UPDATE',
          field,
          oldVal,
          newVal
        )
      }
    }

    return { success: true }
  })

  ipcMain.handle('strutture:delete', (_event, codice: string) => {
    const db = getDb()

    // Block if active children exist
    const figli = (
      db.prepare('SELECT COUNT(*) as n FROM strutture WHERE codice_padre = ? AND deleted_at IS NULL').get(codice) as { n: number }
    ).n

    if (figli > 0) {
      return {
        success: false,
        error: 'STRUTTURA_HAS_CHILDREN',
        message: `Impossibile eliminare: ${figli} struttur${figli === 1 ? 'a figlia attiva' : 'e figlie attive'}. Spostale prima.`
      }
    }

    // Block if active employees exist
    const dipendenti = (
      db.prepare('SELECT COUNT(*) as n FROM dipendenti WHERE codice_struttura = ? AND deleted_at IS NULL').get(codice) as { n: number }
    ).n

    if (dipendenti > 0) {
      return {
        success: false,
        error: 'STRUTTURA_HAS_EMPLOYEES',
        message: `Impossibile eliminare: ${dipendenti} dipendent${dipendenti === 1 ? 'e assegnato' : 'i assegnati'}. Spostali prima.`
      }
    }

    const struttura = db.prepare('SELECT descrizione FROM strutture WHERE codice = ?').get(codice) as { descrizione: string }
    db.prepare('UPDATE strutture SET deleted_at = CURRENT_TIMESTAMP WHERE codice = ?').run(codice)
    writeChangeLog('struttura', codice, struttura?.descrizione ?? codice, 'DELETE', null, null, null)

    return { success: true }
  })

  ipcMain.handle('strutture:restore', (_event, codice: string) => {
    const db = getDb()
    db.prepare('UPDATE strutture SET deleted_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE codice = ?').run(codice)
    const struttura = db.prepare('SELECT descrizione FROM strutture WHERE codice = ?').get(codice) as { descrizione: string }
    writeChangeLog('struttura', codice, struttura?.descrizione ?? codice, 'RESTORE', null, null, null)
    return { success: true }
  })

  ipcMain.handle('strutture:suggestCodice', (_event, codicePadre: string) => {
    const db = getDb()
    const fratelli = (
      db
        .prepare('SELECT codice FROM strutture WHERE codice_padre = ? AND deleted_at IS NULL')
        .all(codicePadre) as { codice: string }[]
    ).map((r) => r.codice)

    return suggestCodice(codicePadre, fratelli)
  })

  ipcMain.handle('strutture:checkCodice', (_event, codice: string) => {
    const db = getDb()
    const existing = db.prepare('SELECT codice FROM strutture WHERE codice = ?').get(codice)
    return { available: !existing }
  })

  // ──────────────────────────────────────────────────────────────
  // DIPENDENTI
  // ──────────────────────────────────────────────────────────────

  ipcMain.handle('dipendenti:list', (_event, showDeleted = false) => {
    const db = getDb()
    const where = showDeleted ? '' : 'WHERE deleted_at IS NULL'
    return db.prepare(`SELECT * FROM dipendenti ${where} ORDER BY titolare ASC`).all()
  })

  ipcMain.handle('dipendenti:get', (_event, cf: string) => {
    const db = getDb()
    return db.prepare('SELECT * FROM dipendenti WHERE codice_fiscale = ?').get(cf)
  })

  ipcMain.handle('dipendenti:create', (_event, data: Record<string, unknown>) => {
    const db = getDb()
    const existing = db.prepare('SELECT codice_fiscale FROM dipendenti WHERE codice_fiscale = ?').get(data.codice_fiscale)
    if (existing) {
      return { success: false, error: 'DUPLICATE_CF', message: `Il codice fiscale "${data.codice_fiscale}" è già in uso` }
    }

    db.prepare(`
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
    `).run(data)

    writeChangeLog('dipendente', String(data.codice_fiscale), data.titolare as string, 'CREATE', null, null, null)
    return { success: true }
  })

  ipcMain.handle('dipendenti:update', (_event, cf: string, data: Record<string, unknown>) => {
    const db = getDb()
    const current = db.prepare('SELECT * FROM dipendenti WHERE codice_fiscale = ?').get(cf) as Record<string, unknown>
    if (!current) {
      return { success: false, error: 'NOT_FOUND' }
    }

    const updateFields = [
      'codice_nel_file', 'unita_organizzativa', 'cdc_costo', 'cdc_costo_is_numeric',
      'titolare', 'codice_struttura', 'livello', 'ruoli_oltre_v', 'ruoli', 'viaggiatore',
      'segr_redaz', 'approvatore', 'cassiere', 'visualizzatori', 'segretario', 'controllore',
      'amministrazione', 'segr_red_assistita', 'segretario_assistito', 'controllore_assistito',
      'ruoli_afc', 'ruoli_hr', 'altri_ruoli', 'sede_tns', 'gruppo_sind'
    ]

    // Merge current values with incoming data so missing fields don't cause
    // "Missing named parameter" errors in better-sqlite3
    const merged: Record<string, unknown> = { codice_fiscale: cf }
    for (const field of updateFields) {
      merged[field] = field in data ? (data[field] ?? null) : (current[field] ?? null)
    }

    db.prepare(`
      UPDATE dipendenti SET
        ${updateFields.map((f) => `${f} = @${f}`).join(',\n        ')},
        updated_at = CURRENT_TIMESTAMP
      WHERE codice_fiscale = @codice_fiscale
    `).run(merged)

    for (const field of updateFields) {
      const oldVal = current[field] !== undefined && current[field] !== null ? String(current[field]) : null
      const newVal = data[field] !== undefined && data[field] !== null ? String(data[field]) : null
      if (oldVal !== newVal) {
        writeChangeLog(
          'dipendente',
          cf,
          (current.titolare as string) ?? cf,
          'UPDATE',
          field,
          oldVal,
          newVal
        )
      }
    }

    return { success: true }
  })

  ipcMain.handle('dipendenti:delete', (_event, cf: string) => {
    const db = getDb()
    const dip = db.prepare('SELECT titolare FROM dipendenti WHERE codice_fiscale = ?').get(cf) as { titolare: string }
    db.prepare('UPDATE dipendenti SET deleted_at = CURRENT_TIMESTAMP WHERE codice_fiscale = ?').run(cf)
    writeChangeLog('dipendente', cf, dip?.titolare ?? cf, 'DELETE', null, null, null)
    return { success: true }
  })

  ipcMain.handle('dipendenti:restore', (_event, cf: string) => {
    const db = getDb()
    db.prepare('UPDATE dipendenti SET deleted_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE codice_fiscale = ?').run(cf)
    const dip = db.prepare('SELECT titolare FROM dipendenti WHERE codice_fiscale = ?').get(cf) as { titolare: string }
    writeChangeLog('dipendente', cf, dip?.titolare ?? cf, 'RESTORE', null, null, null)
    return { success: true }
  })

  // ──────────────────────────────────────────────────────────────
  // XLS IMPORT / EXPORT
  // ──────────────────────────────────────────────────────────────

  ipcMain.handle('xls:openFileDialog', async () => {
    const { filePaths, canceled } = await dialog.showOpenDialog({
      title: 'Seleziona file XLS',
      filters: [
        { name: 'Excel Files', extensions: ['xls', 'xlsx'] },
        { name: 'All Files', extensions: ['*'] }
      ],
      properties: ['openFile']
    })
    return canceled ? null : filePaths[0]
  })

  ipcMain.handle('xls:saveFileDialog', async () => {
    const now = new Date()
    const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
    const { filePath, canceled } = await dialog.showSaveDialog({
      title: 'Esporta file XLS',
      defaultPath: `TNS_ORG_${dateStr}.xls`,
      filters: [
        { name: 'Excel 97-2003', extensions: ['xls'] }
      ]
    })
    return canceled ? null : filePath
  })

  ipcMain.handle('xls:import', (_event, filePath: string) => {
    return importXls(filePath)
  })

  ipcMain.handle('xls:importDev', () => {
    return importXls(DEV_XLS_PATH)
  })

  ipcMain.handle('xls:export', (_event, filePath: string) => {
    exportXls(filePath)
    return { success: true }
  })

  // ──────────────────────────────────────────────────────────────
  // CHANGE LOG
  // ──────────────────────────────────────────────────────────────

  ipcMain.handle('changelog:list', (_event, filters: {
    search?: string
    entityType?: string
    action?: string
    dateFrom?: string
    dateTo?: string
    limit?: number
    offset?: number
  } = {}) => {
    const db = getDb()
    const conditions: string[] = []
    const params: unknown[] = []

    if (filters.search) {
      conditions.push('(entity_label LIKE ? OR entity_id LIKE ? OR new_value LIKE ?)')
      const s = `%${filters.search}%`
      params.push(s, s, s)
    }
    if (filters.entityType && filters.entityType !== 'all') {
      conditions.push('entity_type = ?')
      params.push(filters.entityType)
    }
    if (filters.action && filters.action !== 'all') {
      conditions.push('action = ?')
      params.push(filters.action)
    }
    if (filters.dateFrom) {
      conditions.push('timestamp >= ?')
      params.push(filters.dateFrom)
    }
    if (filters.dateTo) {
      conditions.push('timestamp <= ?')
      params.push(filters.dateTo)
    }

    const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : ''
    const limit = filters.limit ?? 200
    const offset = filters.offset ?? 0

    return db
      .prepare(`SELECT * FROM change_log ${where} ORDER BY timestamp DESC LIMIT ? OFFSET ?`)
      .all([...params, limit, offset])
  })

  ipcMain.handle('changelog:exportCsv', async (_event, filePath: string) => {
    const db = getDb()
    const rows = db.prepare('SELECT * FROM change_log ORDER BY timestamp DESC').all() as Record<string, unknown>[]

    const header = 'id,timestamp,entity_type,entity_id,entity_label,action,field_name,old_value,new_value\n'
    const csvRows = rows.map((r) => {
      const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
      return [r.id, r.timestamp, r.entity_type, r.entity_id, r.entity_label, r.action, r.field_name, r.old_value, r.new_value]
        .map(esc)
        .join(',')
    })

    const { writeFileSync } = await import('fs')
    writeFileSync(filePath, header + csvRows.join('\n'), 'utf-8')
    return { success: true }
  })

  // ──────────────────────────────────────────────────────────────
  // STATS
  // ──────────────────────────────────────────────────────────────

  ipcMain.handle('stats:counts', () => {
    const db = getDb()
    const strutture = (db.prepare('SELECT COUNT(*) as n FROM strutture WHERE deleted_at IS NULL').get() as { n: number }).n
    const dipendenti = (db.prepare('SELECT COUNT(*) as n FROM dipendenti WHERE deleted_at IS NULL').get() as { n: number }).n
    return {
      strutture,
      dipendenti,
      db_tns: strutture + dipendenti
    }
  })

  ipcMain.handle('stats:sedi', () => {
    const db = getDb()
    const sedi = new Set<string>()
    ;(db.prepare('SELECT DISTINCT sede_tns FROM strutture WHERE deleted_at IS NULL AND sede_tns IS NOT NULL').all() as { sede_tns: string }[])
      .forEach((r) => sedi.add(r.sede_tns.toLowerCase()))
    ;(db.prepare('SELECT DISTINCT sede_tns FROM dipendenti WHERE deleted_at IS NULL AND sede_tns IS NOT NULL').all() as { sede_tns: string }[])
      .forEach((r) => sedi.add(r.sede_tns.toLowerCase()))
    return Array.from(sedi).sort()
  })

  // ──────────────────────────────────────────────────────────────
  // STRUTTURE - PARENT UPDATE (with cycle detection)
  // ──────────────────────────────────────────────────────────────

  ipcMain.handle('strutture:updateParent', (_event, codice: string, newCodiceParent: string | null) => {
    const db = getDb()

    // Get current structure
    const current = db.prepare('SELECT * FROM strutture WHERE codice = ?').get(codice) as Record<string, unknown>
    if (!current) {
      return { success: false, error: 'NOT_FOUND', message: 'Struttura non trovata' }
    }

    // Same parent - no-op
    if (current.codice_padre === newCodiceParent) {
      return { success: true }
    }

    // Cycle detection: check if newCodiceParent is a descendant of codice
    if (newCodiceParent) {
      const checkCycle = db.prepare(`
        WITH RECURSIVE descendants(c) AS (
          SELECT ?1
          UNION ALL
          SELECT s.codice FROM strutture s
          INNER JOIN descendants d ON s.codice_padre = d.c
          WHERE s.deleted_at IS NULL
        )
        SELECT COUNT(*) as n FROM descendants WHERE c = ?2
      `)
      const cycleCheck = checkCycle.get(codice, newCodiceParent) as { n: number }
      if (cycleCheck.n > 0) {
        return { success: false, error: 'CYCLE_DETECTED', message: 'Non puoi impostare un figlio come padre' }
      }

      // Verify newCodiceParent exists and is not deleted
      const parentExists = db.prepare('SELECT codice FROM strutture WHERE codice = ? AND deleted_at IS NULL').get(newCodiceParent)
      if (!parentExists) {
        return { success: false, error: 'PARENT_NOT_FOUND', message: 'Struttura padre non trovata o eliminata' }
      }
    }

    // Update parent
    const oldParent = current.codice_padre as string | null
    db.prepare('UPDATE strutture SET codice_padre = ?, updated_at = CURRENT_TIMESTAMP WHERE codice = ?').run(newCodiceParent, codice)

    // Write change log
    writeChangeLog(
      'struttura',
      codice,
      current.descrizione as string,
      'UPDATE',
      'codice_padre',
      oldParent ?? null,
      newCodiceParent ?? null
    )

    return { success: true }
  })
}

// Code suggestion helper
function suggestCodice(codicePadre: string, fratelli: string[]): string {
  if (fratelli.length === 0) {
    return codicePadre + '01'
  }

  // Pattern: single letters (A, B, C)
  if (fratelli.every((c) => /^[A-Z]$/.test(c))) {
    for (let i = 65; i <= 90; i++) {
      const letter = String.fromCharCode(i)
      if (!fratelli.includes(letter)) return letter
    }
    return codicePadre + '_' + (fratelli.length + 1)
  }

  // Pattern: letter + number (O01, O08)
  const letterNum = /^([A-Z]+)(\d+)$/
  const matches = fratelli.filter((c) => letterNum.test(c))
  if (matches.length > 0) {
    const lastMatch = matches[matches.length - 1].match(letterNum)!
    const prefix = lastMatch[1]
    const maxNum = Math.max(...matches.map((c) => parseInt(c.match(letterNum)![2])))
    const nextNum = String(maxNum + 1).padStart(lastMatch[2].length, '0')
    return prefix + nextNum
  }

  // Fallback
  return codicePadre + '_' + (fratelli.length + 1)
}
