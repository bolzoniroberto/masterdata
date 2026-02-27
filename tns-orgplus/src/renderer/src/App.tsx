import React, { useEffect } from 'react'
import AppShell from './components/layout/AppShell'
import OrgChartView from './views/OrgChartView'
import GridView from './views/GridView'
import AccordionView from './views/AccordionView'
import ImportExportView from './views/ImportExportView'
import StoricoView from './views/StoricoView'
import { useOrgStore } from './store/useOrgStore'

export default function App() {
  const { activeTab, refreshAll } = useOrgStore()

  useEffect(() => {
    refreshAll()
  }, [])

  return (
    <AppShell>
      {/* Tutti i tab restano montati: si usa hidden per preservare lo stato locale (accordion aperto, posizione scroll, ecc.) */}
      <div className={`h-full ${activeTab === 'orgchart' ? '' : 'hidden'}`}><OrgChartView /></div>
      <div className={`h-full ${activeTab === 'grid' ? '' : 'hidden'}`}><GridView /></div>
      <div className={`h-full ${activeTab === 'accordion' ? '' : 'hidden'}`}><AccordionView /></div>
      <div className={`h-full ${activeTab === 'importexport' ? '' : 'hidden'}`}><ImportExportView /></div>
      <div className={`h-full ${activeTab === 'storico' ? '' : 'hidden'}`}><StoricoView /></div>
    </AppShell>
  )
}
