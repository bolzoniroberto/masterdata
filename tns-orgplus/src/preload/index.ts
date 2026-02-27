import { contextBridge, ipcRenderer } from 'electron'

// Expose typed API to renderer
contextBridge.exposeInMainWorld('api', {
  strutture: {
    list: (showDeleted?: boolean) => ipcRenderer.invoke('strutture:list', showDeleted),
    get: (codice: string) => ipcRenderer.invoke('strutture:get', codice),
    getDipendenti: (codice: string) => ipcRenderer.invoke('strutture:getDipendenti', codice),
    create: (data: Record<string, unknown>) => ipcRenderer.invoke('strutture:create', data),
    update: (codice: string, data: Record<string, unknown>) => ipcRenderer.invoke('strutture:update', codice, data),
    delete: (codice: string) => ipcRenderer.invoke('strutture:delete', codice),
    restore: (codice: string) => ipcRenderer.invoke('strutture:restore', codice),
    suggestCodice: (codicePadre: string) => ipcRenderer.invoke('strutture:suggestCodice', codicePadre),
    checkCodice: (codice: string) => ipcRenderer.invoke('strutture:checkCodice', codice),
    updateParent: (codice: string, newCodiceParent: string | null) =>
      ipcRenderer.invoke('strutture:updateParent', codice, newCodiceParent)
  },

  dipendenti: {
    list: (showDeleted?: boolean) => ipcRenderer.invoke('dipendenti:list', showDeleted),
    get: (cf: string) => ipcRenderer.invoke('dipendenti:get', cf),
    create: (data: Record<string, unknown>) => ipcRenderer.invoke('dipendenti:create', data),
    update: (cf: string, data: Record<string, unknown>) => ipcRenderer.invoke('dipendenti:update', cf, data),
    delete: (cf: string) => ipcRenderer.invoke('dipendenti:delete', cf),
    restore: (cf: string) => ipcRenderer.invoke('dipendenti:restore', cf)
  },

  xls: {
    openFileDialog: () => ipcRenderer.invoke('xls:openFileDialog'),
    saveFileDialog: () => ipcRenderer.invoke('xls:saveFileDialog'),
    import: (filePath: string) => ipcRenderer.invoke('xls:import', filePath),
    importDev: () => ipcRenderer.invoke('xls:importDev'),
    export: (filePath: string) => ipcRenderer.invoke('xls:export', filePath)
  },

  changelog: {
    list: (filters?: Record<string, unknown>) => ipcRenderer.invoke('changelog:list', filters),
    exportCsv: (filePath: string) => ipcRenderer.invoke('changelog:exportCsv', filePath)
  },

  stats: {
    counts: () => ipcRenderer.invoke('stats:counts'),
    sedi: () => ipcRenderer.invoke('stats:sedi')
  }
})
