import React, { useState, useMemo } from 'react'
import { Search, ChevronDown, Plus, Trash2, Edit2 } from 'lucide-react'
import {
  DndContext,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
} from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import * as Accordion from '@radix-ui/react-accordion'
import { useOrgStore } from '../store/useOrgStore'
import type { Struttura, Dipendente } from '../types'
import ConfirmDialog from '../components/shared/ConfirmDialog'
import RecordDrawer from '../components/shared/RecordDrawer'

interface TreeStructura {
  struttura: Struttura & { dipendenti_count: number }
  children: TreeStructura[]
  dipendenti: Dipendente[]
}

// Build hierarchical tree
function buildTree(
  strutture: (Struttura & { dipendenti_count: number })[],
  dipendenti: Dipendente[],
  filteredCodici?: Set<string>
): TreeStructura[] {
  const byParent = new Map<string | null, (Struttura & { dipendenti_count: number })[]>()
  const dipendentesByStruttura = new Map<string, Dipendente[]>()

  strutture.forEach((s) => {
    if (filteredCodici && !filteredCodici.has(s.codice)) return
    const p = s.codice_padre ?? null
    if (!byParent.has(p)) byParent.set(p, [])
    byParent.get(p)!.push(s)
  })

  dipendenti.forEach((d) => {
    if (!dipendentesByStruttura.has(d.codice_struttura)) {
      dipendentesByStruttura.set(d.codice_struttura, [])
    }
    dipendentesByStruttura.get(d.codice_struttura)!.push(d)
  })

  function build(parentCodice: string | null): TreeStructura[] {
    const children = byParent.get(parentCodice) ?? []
    return children
      .sort((a, b) => (a.codice ?? '').localeCompare(b.codice ?? ''))
      .map((s) => ({
        struttura: s,
        children: build(s.codice),
        dipendenti: dipendentesByStruttura.get(s.codice) ?? [],
      }))
  }

  return build(null)
}

// Draggable struttura item
interface SortableStruturaItemProps {
  treeNode: TreeStructura
  onEdit: (s: Struttura & { dipendenti_count: number }) => void
  onDelete: (s: Struttura & { dipendenti_count: number }) => void
  compact: boolean
}

function SortableStruturaItem({
  treeNode,
  onEdit,
  onDelete,
  compact,
}: SortableStruturaItemProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useSortable({
    id: treeNode.struttura.codice,
  })

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`py-2 px-3 bg-white border border-gray-200 rounded-md cursor-move hover:bg-gray-50 transition-colors ${
        isDragging ? 'shadow-lg' : 'shadow-sm'
      }`}
      {...attributes}
      {...listeners}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900">{treeNode.struttura.codice}</div>
          {!compact && (
            <>
              <div className="text-sm text-gray-600 truncate">{treeNode.struttura.descrizione}</div>
              {treeNode.struttura.titolare && (
                <div className="text-xs text-gray-500">Titolare: {treeNode.struttura.titolare}</div>
              )}
              {treeNode.struttura.cdc_costo && (
                <div className="text-xs text-gray-500">CdC: {treeNode.struttura.cdc_costo}</div>
              )}
            </>
          )}
        </div>
        <div className="flex items-center gap-2 ml-2 flex-shrink-0">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEdit(treeNode.struttura)
            }}
            className="text-xs p-1.5 text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
            title="Modifica"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete(treeNode.struttura)
            }}
            className="text-xs p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
            title="Elimina"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

// Draggable dipendente item
interface SortableDipendenteItemProps {
  dipendente: Dipendente
  onEdit: (d: Dipendente) => void
  onDelete: (d: Dipendente) => void
  compact: boolean
}

function SortableDipendenteItem({
  dipendente,
  onEdit,
  onDelete,
  compact,
}: SortableDipendenteItemProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useSortable({
    id: `dip-${dipendente.codice_fiscale}`,
  })

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`py-2 px-3 bg-blue-50 border border-blue-200 rounded-md cursor-move hover:bg-blue-100 transition-colors ml-4 ${
        isDragging ? 'shadow-lg' : 'shadow-sm'
      }`}
      {...attributes}
      {...listeners}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900">{dipendente.codice_fiscale}</div>
          {!compact && dipendente.titolare && (
            <div className="text-sm text-gray-600">{dipendente.titolare}</div>
          )}
        </div>
        <div className="flex items-center gap-2 ml-2 flex-shrink-0">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEdit(dipendente)
            }}
            className="text-xs p-1.5 text-blue-600 hover:bg-blue-200 rounded transition-colors"
            title="Modifica"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete(dipendente)
            }}
            className="text-xs p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
            title="Elimina"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

// Recursive accordion item for struttura with children
interface AccordionStruturaItemProps {
  treeNode: TreeStructura
  onEditStruttura: (s: Struttura & { dipendenti_count: number }) => void
  onDeleteStruttura: (s: Struttura & { dipendenti_count: number }) => void
  onCreateDipendente: (strutturaCodice: string) => void
  onEditDipendente: (d: Dipendente) => void
  onDeleteDipendente: (d: Dipendente) => void
  compact: boolean
}

function AccordionStruturaItem({
  treeNode,
  onEditStruttura,
  onDeleteStruttura,
  onCreateDipendente,
  onEditDipendente,
  onDeleteDipendente,
  compact,
}: AccordionStruturaItemProps) {
  const allIds = useMemo(() => {
    const ids = [treeNode.struttura.codice]
    treeNode.dipendenti.forEach((d) => ids.push(`dip-${d.codice_fiscale}`))
    if (treeNode.children.length > 0) {
      // Add child structure IDs
      const collectIds = (node: TreeStructura) => {
        ids.push(node.struttura.codice)
        node.children.forEach(collectIds)
      }
      treeNode.children.forEach(collectIds)
    }
    return ids
  }, [treeNode])

  return (
    <Accordion.Item value={treeNode.struttura.codice} className="border-b border-gray-200">
      <Accordion.Trigger className="w-full p-3 hover:bg-gray-50 transition-colors flex items-center justify-between data-[state=open]:bg-gray-50">
        <div className="flex items-center flex-1 min-w-0 text-left">
          <ChevronDown className="w-4 h-4 mr-2 flex-shrink-0 transition-transform group-data-[state=open]:-rotate-180" />
          <div className="flex-1 min-w-0">
            <div className="font-medium text-gray-900">{treeNode.struttura.codice}</div>
            {!compact && (
              <div className="text-sm text-gray-600 truncate">{treeNode.struttura.descrizione}</div>
            )}
          </div>
          {(treeNode.dipendenti.length > 0 || treeNode.children.length > 0) && (
            <span className="ml-2 text-xs text-gray-500 flex-shrink-0">
              {treeNode.dipendenti.length > 0 && `${treeNode.dipendenti.length} dip.`}
              {treeNode.children.length > 0 && ` ${treeNode.children.length} sub.`}
            </span>
          )}
        </div>
      </Accordion.Trigger>
      <Accordion.Content className="p-3 bg-gray-50">
        <SortableContext items={allIds} strategy={verticalListSortingStrategy}>
          <div className="space-y-3">
            {/* Struttura item */}
            <div>
              <div className="text-xs font-semibold text-gray-700 px-3 mb-2">Struttura</div>
              <SortableStruturaItem
                treeNode={treeNode}
                onEdit={onEditStruttura}
                onDelete={onDeleteStruttura}
                compact={compact}
              />
            </div>

            {/* Dipendenti */}
            {treeNode.dipendenti.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-gray-700 px-3 mb-2">Dipendenti ({treeNode.dipendenti.length})</div>
                <div className="space-y-2">
                  {treeNode.dipendenti.map((d) => (
                    <SortableDipendenteItem
                      key={d.codice_fiscale}
                      dipendente={d}
                      onEdit={onEditDipendente}
                      onDelete={onDeleteDipendente}
                      compact={compact}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Add dipendente button */}
            <button
              onClick={() => onCreateDipendente(treeNode.struttura.codice)}
              className="w-full py-2 px-3 text-sm text-blue-600 hover:bg-blue-50 rounded-md border border-dashed border-blue-300 transition-colors flex items-center justify-center gap-1"
            >
              <Plus className="w-4 h-4" />
              Nuovo Dipendente
            </button>

            {/* Child structures */}
            {treeNode.children.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-gray-700 px-3 mb-2">Sottostrutture ({treeNode.children.length})</div>
                <Accordion type="single" collapsible className="border border-gray-200 rounded-md">
                  {treeNode.children.map((child) => (
                    <AccordionStruturaItem
                      key={child.struttura.codice}
                      treeNode={child}
                      onEditStruttura={onEditStruttura}
                      onDeleteStruttura={onDeleteStruttura}
                      onCreateDipendente={onCreateDipendente}
                      onEditDipendente={onEditDipendente}
                      onDeleteDipendente={onDeleteDipendente}
                      compact={compact}
                    />
                  ))}
                </Accordion>
              </div>
            )}
          </div>
        </SortableContext>
      </Accordion.Content>
    </Accordion.Item>
  )
}

export default function AccordionView() {
  const { strutture, dipendenti, refreshAll, addToast } = useOrgStore()
  const [search, setSearch] = useState('')
  const [sedeFiltro, setSedeFiltro] = useState<string>('all')
  const [compact, setCompact] = useState(false)
  const [confirmDialog, setConfirmDialog] = useState<{
    title: string
    message: string
    onConfirm: () => Promise<void>
  } | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerRecord, setDrawerRecord] = useState<(Struttura & { dipendenti_count: number }) | Dipendente | null>(null)
  const [drawerType, setDrawerType] = useState<'struttura' | 'dipendente'>('struttura')

  const sensors = useSensors(useSensor(PointerSensor, { distance: 8 }))

  const sediList = useMemo(() => {
    const all = new Set<string>()
    strutture.forEach((s) => s.sede_tns && all.add(s.sede_tns))
    dipendenti.forEach((d) => d.sede_tns && all.add(d.sede_tns))
    return Array.from(all).sort()
  }, [strutture, dipendenti])

  const filteredStrutture = useMemo(() => {
    let result = strutture
    if (sedeFiltro !== 'all') {
      result = result.filter((s) => (s.sede_tns?.toLowerCase() ?? '') === sedeFiltro.toLowerCase())
    }
    return result
  }, [strutture, sedeFiltro])

  const filteredDipendenti = useMemo(() => {
    let result = dipendenti
    if (sedeFiltro !== 'all') {
      result = result.filter((d) => (d.sede_tns?.toLowerCase() ?? '') === sedeFiltro.toLowerCase())
    }
    return result
  }, [dipendenti, sedeFiltro])

  const searchResults = useMemo(() => {
    if (!search) return new Set<string>()
    const lower = search.toLowerCase()
    const matching = new Set<string>()
    filteredStrutture.forEach((s) => {
      if (
        s.descrizione?.toLowerCase().includes(lower) ||
        s.codice?.toLowerCase().includes(lower) ||
        s.titolare?.toLowerCase().includes(lower)
      ) {
        matching.add(s.codice)
      }
    })
    return matching
  }, [search, filteredStrutture])

  const treeData = useMemo(
    () => buildTree(filteredStrutture, filteredDipendenti, search ? searchResults : undefined),
    [filteredStrutture, filteredDipendenti, search, searchResults]
  )

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    // Guard: ensure window.api is available
    if (!window.api?.strutture?.updateParent) {
      addToast('Applicazione non completamente inizializzata', 'error')
      return
    }

    const activeId = String(active.id)
    const overId = String(over.id)

    try {
      if (!activeId.startsWith('dip-') && !overId.startsWith('dip-')) {
        // Moving structure - update parent
        const newParent = overId
        const result = await window.api.strutture.updateParent(activeId, newParent === 'root' ? null : newParent)
        if (result.success) {
          await refreshAll()
          addToast('Struttura spostata con successo', 'success')
        } else {
          addToast(result.message || 'Errore nello spostamento', 'error')
        }
      }
    } catch (err) {
      addToast('Errore: ' + String(err), 'error')
    }
  }

  const handleDeleteStruttura = (s: Struttura & { dipendenti_count: number }) => {
    if ((s.dipendenti_count || 0) > 0) {
      addToast(`La struttura "${s.codice}" ha ${s.dipendenti_count} dipendente(i). Trasferiscili prima.`, 'error')
      return
    }

    setConfirmDialog({
      title: 'Elimina struttura',
      message: `Sei sicuro di voler eliminare "${s.codice}"?`,
      onConfirm: async () => {
        try {
          if (!window.api?.strutture?.delete) {
            addToast('Applicazione non completamente inizializzata', 'error')
            return
          }
          const result = await window.api.strutture.delete(s.codice)
          if (result.success) {
            await refreshAll()
            addToast('Struttura eliminata', 'success')
          } else {
            addToast(result.message || 'Errore', 'error')
          }
        } catch (err) {
          addToast('Errore: ' + String(err), 'error')
        }
      },
    })
  }

  const handleDeleteDipendente = (d: Dipendente) => {
    setConfirmDialog({
      title: 'Elimina dipendente',
      message: `Sei sicuro di voler eliminare "${d.codice_fiscale}"?`,
      onConfirm: async () => {
        try {
          if (!window.api?.dipendenti?.delete) {
            addToast('Applicazione non completamente inizializzata', 'error')
            return
          }
          const result = await window.api.dipendenti.delete(d.codice_fiscale)
          if (result.success) {
            await refreshAll()
            addToast('Dipendente eliminato', 'success')
          } else {
            addToast('Errore', 'error')
          }
        } catch (err) {
          addToast('Errore: ' + String(err), 'error')
        }
      },
    })
  }

  return (
    <div className="flex flex-col h-full gap-4 p-4 bg-white">
      {/* Toolbar */}
      <div className="flex items-center gap-3 pb-3 border-b border-gray-200">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Cerca struttura..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-400"
          />
        </div>

        <select
          value={sedeFiltro}
          onChange={(e) => setSedeFiltro(e.target.value)}
          className="text-sm border border-gray-200 rounded-md px-2 py-2 focus:outline-none focus:ring-1 focus:ring-indigo-400 bg-white"
        >
          <option value="all">Tutte le sedi</option>
          {sediList.map((s) => (
            <option key={s} value={s.toLowerCase()}>
              {s}
            </option>
          ))}
        </select>

        <button
          onClick={() => setCompact(!compact)}
          className={`text-sm px-3 py-2 rounded-md transition-colors ${
            compact ? 'bg-indigo-100 text-indigo-700' : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          {compact ? 'Compatto' : 'Esteso'}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {treeData.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-400">Nessuna struttura trovata</p>
          </div>
        ) : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <Accordion.Root type="single" collapsible className="space-y-2">
              {treeData.map((rootNode) => (
                <AccordionStruturaItem
                  key={rootNode.struttura.codice}
                  treeNode={rootNode}
                  onEditStruttura={(s) => {
                    setDrawerType('struttura')
                    setDrawerRecord(s)
                    setDrawerOpen(true)
                  }}
                  onDeleteStruttura={handleDeleteStruttura}
                  onCreateDipendente={() => addToast('Crea dipendente non ancora implementato', 'info')}
                  onEditDipendente={(d) => {
                    setDrawerType('dipendente')
                    setDrawerRecord(d)
                    setDrawerOpen(true)
                  }}
                  onDeleteDipendente={handleDeleteDipendente}
                  compact={compact}
                />
              ))}
            </Accordion.Root>
          </DndContext>
        )}
      </div>

      {/* Confirm Dialog */}
      {confirmDialog && (
        <ConfirmDialog
          title={confirmDialog.title}
          message={confirmDialog.message}
          onConfirm={async () => {
            await confirmDialog.onConfirm()
            setConfirmDialog(null)
          }}
          onCancel={() => setConfirmDialog(null)}
        />
      )}

      {/* Record Drawer */}
      {drawerOpen && drawerRecord && drawerType === 'struttura' && (
        <RecordDrawer
          open={drawerOpen}
          type="struttura"
          record={drawerRecord as Struttura & { dipendenti_count: number }}
          initialMode="view"
          onClose={() => setDrawerOpen(false)}
          onSaved={refreshAll}
        />
      )}
      {drawerOpen && drawerRecord && drawerType === 'dipendente' && (
        <RecordDrawer
          open={drawerOpen}
          type="dipendente"
          record={drawerRecord as Dipendente}
          initialMode="view"
          onClose={() => setDrawerOpen(false)}
          onSaved={refreshAll}
        />
      )}
    </div>
  )
}
