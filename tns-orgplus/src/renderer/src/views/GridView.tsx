import React, { useState, useMemo, useCallback } from 'react'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef, ICellRendererParams } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'
import { ChevronRight, Plus, Search, Eye, EyeOff } from 'lucide-react'
import { useOrgStore } from '../store/useOrgStore'
import type { Struttura, Dipendente } from '../types'
import RecordDrawer from '../components/shared/RecordDrawer'

type SubTab = 'strutture' | 'dipendenti'

export default function GridView() {
  const { strutture, dipendenti, refreshAll } = useOrgStore()
  const [subTab, setSubTab] = useState<SubTab>('strutture')
  const [search, setSearch] = useState('')
  const [sedeFiltro, setSedeFiltro] = useState<string>('all')
  const [showDeleted, setShowDeleted] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerType, setDrawerType] = useState<'struttura' | 'dipendente'>('struttura')
  const [drawerRecord, setDrawerRecord] = useState<(Struttura & { dipendenti_count?: number }) | Dipendente | null>(null)
  const [drawerMode, setDrawerMode] = useState<'view' | 'edit' | 'create'>('view')

  const sediList = useMemo(() => {
    const all = new Set<string>()
    strutture.forEach((s) => s.sede_tns && all.add(s.sede_tns))
    dipendenti.forEach((d) => d.sede_tns && all.add(d.sede_tns))
    return Array.from(all).sort()
  }, [strutture, dipendenti])

  const openDrawer = useCallback(
    (type: 'struttura' | 'dipendente', record: (Struttura & { dipendenti_count?: number }) | Dipendente | null, mode: 'view' | 'edit' | 'create') => {
      setDrawerType(type)
      setDrawerRecord(record)
      setDrawerMode(mode)
      setDrawerOpen(true)
    },
    []
  )

  // Column definitions for Strutture
  const struttureCols: ColDef[] = useMemo(
    () => [
      {
        field: 'codice',
        headerName: 'Codice',
        width: 110,
        sortable: true,
        cellClass: 'font-mono text-xs text-gray-600'
      },
      {
        field: 'descrizione',
        headerName: 'Descrizione',
        flex: 2,
        sortable: true,
        cellClass: 'text-sm font-medium text-gray-900'
      },
      {
        field: 'cdc_costo',
        headerName: 'CdC',
        width: 110,
        sortable: true,
        cellClass: 'text-xs text-gray-500'
      },
      {
        field: 'codice_padre',
        headerName: 'Padre',
        width: 100,
        sortable: true,
        cellClass: 'font-mono text-xs text-gray-500'
      },
      {
        field: 'titolare',
        headerName: 'Titolare',
        flex: 1.5,
        sortable: true,
        cellClass: 'text-sm text-gray-600'
      },
      {
        field: 'approvatore',
        headerName: 'Approvatore',
        width: 130,
        sortable: true,
        cellClass: 'text-xs text-gray-600'
      },
      {
        field: 'sede_tns',
        headerName: 'Sede',
        width: 120,
        sortable: true,
        cellClass: 'text-xs text-gray-500'
      },
      {
        field: 'dipendenti_count',
        headerName: '# Dip.',
        width: 80,
        sortable: true,
        cellClass: 'text-xs text-gray-500 text-center',
        type: 'numericColumn'
      },
      {
        headerName: '',
        width: 46,
        pinned: 'right',
        sortable: false,
        cellRenderer: (params: ICellRendererParams) => (
          <button
            onClick={() => openDrawer('struttura', params.data, 'view')}
            className="flex items-center justify-center w-full h-full text-gray-300 hover:text-gray-600"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )
      }
    ],
    [openDrawer]
  )

  // Column definitions for Dipendenti
  const dipendentiCols: ColDef[] = useMemo(
    () => [
      {
        field: 'codice_fiscale',
        headerName: 'CF',
        width: 160,
        sortable: true,
        cellClass: 'font-mono text-xs text-gray-500'
      },
      {
        field: 'titolare',
        headerName: 'Titolare',
        flex: 2,
        sortable: true,
        cellClass: 'text-sm font-medium text-gray-900'
      },
      {
        field: 'codice_struttura',
        headerName: 'Struttura',
        width: 120,
        sortable: true,
        cellClass: 'font-mono text-xs text-gray-600'
      },
      {
        field: 'viaggiatore',
        headerName: 'Viaggiatore',
        width: 120,
        sortable: true,
        cellClass: 'text-xs text-gray-600'
      },
      {
        field: 'approvatore',
        headerName: 'Approvatore',
        width: 130,
        sortable: true,
        cellClass: 'text-xs text-gray-600'
      },
      {
        field: 'cassiere',
        headerName: 'Cassiere',
        width: 100,
        sortable: true,
        cellClass: 'text-xs text-gray-600'
      },
      {
        field: 'sede_tns',
        headerName: 'Sede',
        width: 120,
        sortable: true,
        cellClass: 'text-xs text-gray-500'
      },
      {
        headerName: '',
        width: 46,
        pinned: 'right',
        sortable: false,
        cellRenderer: (params: ICellRendererParams) => (
          <button
            onClick={() => openDrawer('dipendente', params.data, 'view')}
            className="flex items-center justify-center w-full h-full text-gray-300 hover:text-gray-600"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )
      }
    ],
    [openDrawer]
  )

  // Filtered data
  const filteredData = useMemo(() => {
    const searchLower = search.toLowerCase()
    if (subTab === 'strutture') {
      return strutture.filter((s) => {
        const matchDeleted = showDeleted ? true : !s.deleted_at
        const matchSearch =
          !search ||
          (s.codice?.toLowerCase().includes(searchLower) ?? false) ||
          (s.descrizione?.toLowerCase().includes(searchLower) ?? false) ||
          (s.titolare?.toLowerCase().includes(searchLower) ?? false)
        const matchSede =
          sedeFiltro === 'all' || (s.sede_tns?.toLowerCase() === sedeFiltro.toLowerCase())
        return matchDeleted && matchSearch && matchSede
      })
    } else {
      return dipendenti.filter((d) => {
        const matchDeleted = showDeleted ? true : !d.deleted_at
        const matchSearch =
          !search ||
          (d.codice_fiscale?.toLowerCase().includes(searchLower) ?? false) ||
          (d.titolare?.toLowerCase().includes(searchLower) ?? false) ||
          (d.codice_struttura?.toLowerCase().includes(searchLower) ?? false)
        const matchSede =
          sedeFiltro === 'all' || (d.sede_tns?.toLowerCase() === sedeFiltro.toLowerCase())
        return matchDeleted && matchSearch && matchSede
      })
    }
  }, [strutture, dipendenti, subTab, search, sedeFiltro, showDeleted])

  const getRowClass = (params: { data?: (Struttura | Dipendente) & { deleted_at?: string | null } }) => {
    if (params.data?.deleted_at) return 'bg-red-50 line-through text-gray-400'
    return ''
  }

  return (
    <div className="flex flex-col h-full">
      {/* Sub-tab + toolbar */}
      <div className="flex items-center gap-3 px-4 py-2.5 bg-white border-b border-gray-200">
        {/* Sub-tabs */}
        <div className="flex gap-1">
          {(['strutture', 'dipendenti'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setSubTab(tab)}
              className={[
                'px-3 py-1.5 text-sm rounded-md transition-colors capitalize',
                subTab === tab
                  ? 'bg-indigo-50 text-indigo-700 font-medium'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              ].join(' ')}
            >
              {tab === 'strutture' ? `Strutture (${strutture.filter((s) => !s.deleted_at).length})` : `Dipendenti (${dipendenti.filter((d) => !d.deleted_at).length})`}
            </button>
          ))}
        </div>

        <div className="flex-1" />

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            placeholder="Cerca..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-md w-52 focus:outline-none focus:ring-1 focus:ring-indigo-400"
          />
        </div>

        {/* Sede filter */}
        <select
          value={sedeFiltro}
          onChange={(e) => setSedeFiltro(e.target.value)}
          className="text-sm border border-gray-200 rounded-md px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-400 bg-white text-gray-700"
        >
          <option value="all">Tutte le sedi</option>
          {sediList.map((s) => (
            <option key={s} value={s.toLowerCase()}>
              {s}
            </option>
          ))}
        </select>

        {/* Show deleted toggle */}
        <button
          onClick={() => setShowDeleted((v) => !v)}
          className={[
            'flex items-center gap-1.5 text-sm px-2.5 py-1.5 rounded-md border transition-colors',
            showDeleted
              ? 'bg-red-50 border-red-200 text-red-700'
              : 'border-gray-200 text-gray-500 hover:text-gray-700'
          ].join(' ')}
          title={showDeleted ? 'Nascondi eliminati' : 'Mostra eliminati'}
        >
          {showDeleted ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
          <span className="hidden sm:inline">Eliminati</span>
        </button>

        {/* Add button */}
        <button
          onClick={() => openDrawer(subTab === 'strutture' ? 'struttura' : 'dipendente', null, 'create')}
          className="flex items-center gap-1.5 text-sm bg-indigo-600 text-white px-3 py-1.5 rounded-md hover:bg-indigo-700 transition-colors font-medium"
        >
          <Plus className="w-3.5 h-3.5" />
          Aggiungi
        </button>
      </div>

      {/* Grid */}
      <div className="flex-1 ag-theme-alpine">
        <AgGridReact
          rowData={filteredData}
          columnDefs={subTab === 'strutture' ? struttureCols : dipendentiCols}
          defaultColDef={{
            resizable: true,
            suppressMovable: false,
            sortable: true
          }}
          getRowClass={getRowClass}
          onRowDoubleClicked={(e) => {
            openDrawer(
              subTab === 'strutture' ? 'struttura' : 'dipendente',
              e.data,
              'edit'
            )
          }}
          animateRows={true}
          suppressCellFocus={false}
          rowHeight={36}
          headerHeight={36}
        />
      </div>

      {/* Drawer */}
      <RecordDrawer
        open={drawerOpen}
        type={drawerType}
        record={drawerRecord}
        initialMode={drawerMode}
        onClose={() => setDrawerOpen(false)}
        onSaved={() => refreshAll()}
      />
    </div>
  )
}
