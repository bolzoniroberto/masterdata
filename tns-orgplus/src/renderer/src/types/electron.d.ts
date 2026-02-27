import type { Struttura, Dipendente, ChangeLogEntry, ImportReport, DeleteResult, StrutturaCounts } from './index'

interface ElectronAPI {
  strutture: {
    list: (showDeleted?: boolean) => Promise<(Struttura & { dipendenti_count: number })[]>
    get: (codice: string) => Promise<(Struttura & { dipendenti_count: number }) | null>
    getDipendenti: (codice: string) => Promise<Dipendente[]>
    create: (data: Partial<Struttura>) => Promise<{ success: boolean; error?: string; message?: string }>
    update: (codice: string, data: Partial<Struttura>) => Promise<{ success: boolean; error?: string }>
    delete: (codice: string) => Promise<DeleteResult>
    restore: (codice: string) => Promise<{ success: boolean }>
    suggestCodice: (codicePadre: string) => Promise<string>
    checkCodice: (codice: string) => Promise<{ available: boolean }>
  }
  dipendenti: {
    list: (showDeleted?: boolean) => Promise<Dipendente[]>
    get: (cf: string) => Promise<Dipendente | null>
    create: (data: Partial<Dipendente>) => Promise<{ success: boolean; error?: string; message?: string }>
    update: (cf: string, data: Partial<Dipendente>) => Promise<{ success: boolean; error?: string }>
    delete: (cf: string) => Promise<{ success: boolean }>
    restore: (cf: string) => Promise<{ success: boolean }>
  }
  xls: {
    openFileDialog: () => Promise<string | null>
    saveFileDialog: () => Promise<string | null>
    import: (filePath: string) => Promise<ImportReport>
    importDev: () => Promise<ImportReport>
    export: (filePath: string) => Promise<{ success: boolean }>
  }
  changelog: {
    list: (filters?: {
      search?: string
      entityType?: string
      action?: string
      dateFrom?: string
      dateTo?: string
      limit?: number
      offset?: number
    }) => Promise<ChangeLogEntry[]>
    exportCsv: (filePath: string) => Promise<{ success: boolean }>
  }
  stats: {
    counts: () => Promise<StrutturaCounts>
    sedi: () => Promise<string[]>
  }
}

declare global {
  interface Window {
    api: ElectronAPI
  }
}
