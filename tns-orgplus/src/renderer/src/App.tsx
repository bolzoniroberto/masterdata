import React, { useEffect } from 'react'
import AppShell from './components/layout/AppShell'
import OrgChartView from './views/OrgChartView'
import GridView from './views/GridView'
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
      <div className="h-full">
        {activeTab === 'orgchart' && <OrgChartView />}
        {activeTab === 'grid' && <GridView />}
        {activeTab === 'importexport' && <ImportExportView />}
        {activeTab === 'storico' && <StoricoView />}
      </div>
    </AppShell>
  )
}
