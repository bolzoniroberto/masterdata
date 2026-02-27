import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement)

// window.api is only available inside Electron (injected by preload script).
// If opened in a regular browser, show a clear error instead of crashing.
if (!(window as any).api) {
  root.render(
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', height: '100vh', fontFamily: 'system-ui',
      background: '#fafafa', color: '#333'
    }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
      <h1 style={{ margin: 0, fontSize: 22, fontWeight: 600 }}>App non disponibile nel browser</h1>
      <p style={{ marginTop: 12, color: '#666', textAlign: 'center', maxWidth: 400 }}>
        TNS OrgPlus è un'app desktop Electron.<br />
        Aprila con <code style={{ background: '#eee', padding: '2px 6px', borderRadius: 4 }}>npm run dev</code> dalla cartella <code style={{ background: '#eee', padding: '2px 6px', borderRadius: 4 }}>tns-orgplus/</code>.
      </p>
    </div>
  )
} else {
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
}
