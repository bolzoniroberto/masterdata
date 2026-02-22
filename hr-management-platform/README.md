# 🏢 HR Management Platform

**Piattaforma completa per la gestione dei dati HR e degli organigrammi aziendali**

Una soluzione moderna e interattiva per gestire il personale, le strutture organizzative, i ruoli e visualizzare gerarchie aziendali multiple in modo semplice ed efficace.

---

## 📋 Indice

- [Panoramica](#-panoramica)
- [Caratteristiche Principali](#-caratteristiche-principali)
- [Architettura](#-architettura)
- [Installazione](#-installazione)
- [Utilizzo](#-utilizzo)
- [Organigrammi Interattivi](#-organigrammi-interattivi)
- [Import Dati](#-import-dati)
- [Gestione Versioni](#-gestione-versioni)
- [Tecnologie](#-tecnologie)
- [Struttura Progetto](#-struttura-progetto)
- [Contribuire](#-contribuire)

---

## 🎯 Panoramica

La **HR Management Platform** è uno strumento completo per la gestione dei dati relativi al personale e alle strutture organizzative aziendali. Sviluppata con Streamlit, offre un'interfaccia web moderna e intuitiva per:

- **Importare e gestire** dati HR da file Excel
- **Visualizzare organigrammi** multipli (HR, ORG, TNS) in modo interattivo
- **Tracciare modifiche** con sistema di versioning automatico
- **Esportare dati** in formati compatibili con altri sistemi
- **Validare coerenza** tra database e file Excel

### Casi d'uso principali

✅ **HR Manager**: Gestire dipendenti, ruoli, assegnazioni gerarchiche
✅ **Responsabili**: Visualizzare la propria area organizzativa
✅ **IT/Admin**: Importare dati da sistemi esterni, mantenere coerenza
✅ **Direzione**: Analizzare strutture organizzative e KPI

---

## ✨ Caratteristiche Principali

### 🌳 Organigrammi Interattivi Multi-Vista

Visualizza le gerarchie aziendali in **6 layout diversi**:

| Layout | Descrizione | Uso Consigliato |
|--------|-------------|------------------|
| **🌲 Albero Orizzontale** | Tree classico sinistra-destra | Gerarchie ampie, stampa |
| **🏛️ Albero Verticale** | Tree top-down con wrapping | Presentazioni, overview |
| **☀️ Sunburst** | Cerchi concentrici radiali | Visualizzare proporzioni |
| **📦 Treemap** | Rettangoli proporzionali | Analisi dimensioni team |
| **🗂️ Pannelli (Finder)** | Navigazione a colonne | Drill-down rapido |
| **📋 Card Grid** | Griglia schede OrgVue-style | Vista dettagli dipendenti |

**Funzionalità avanzate**:
- ✅ **Drill-down**: Click su manager → mostra solo riporti diretti
- ✅ **Auto-fit responsive**: Si adatta automaticamente al viewport
- ✅ **Ricerca live**: Trova e evidenzia nodi in tempo reale
- ✅ **Export PNG**: Salva visualizzazioni come immagine
- ✅ **Zoom & Pan**: Navigazione fluida con mouse/touch

### 📊 Tre Gerarchie Distinte

| Organigramma | Basato su | Scopo |
|--------------|-----------|-------|
| **HR** | Responsabile Diretto (CF) | Gerarchia manageriale effettiva |
| **ORG** | Unità Organizzative | Struttura formale aziendale |
| **TNS** | Posizioni TNS (Padre/Figlio) | Integrazione sistema TNS legacy |

### 📥 Import Intelligente con Wizard Guidato

**Mappatura automatica delle colonne**:
- Riconoscimento automatico formato DB_ORG
- Fuzzy matching intelligente per colonne (es. "Nome" → "NOME", "name", etc.)
- Preview dati con validazione in tempo reale
- Gestione errori con report dettagliati

**Formati supportati**:
- ✅ **DB_ORG** (consigliato): File unico con mappatura automatica
- ✅ **TNS Legacy**: Fogli separati Personale + Strutture

**Wizard in 4 step**:
1. **Upload file** - Drag & drop o selezione manuale
2. **Mappatura colonne** - Conferma/modifica mapping automatico
3. **Preview** - Verifica dati prima dell'import
4. **Conferma** - Import con creazione snapshot automatico

### 🔄 Versioning & Audit Log

**Sistema di versioning automatico**:
- 📸 **Snapshot automatici** ad ogni import
- 📝 **Changelog dettagliato** per ogni modifica
- 🔙 **Ripristino versioni** precedenti
- 🏆 **Milestone certificate** per versioni stabili

**Audit trail completo**:
- Chi ha fatto cosa e quando
- Diff tra versioni (aggiunte/modifiche/eliminazioni)
- Report di consistenza DB-Excel

### 📋 Gestione Dati Completa

**Vista Excel-like**:
- Tabella editabile in-place con `st.data_editor`
- Selezione colonne personalizzata
- Filtri dinamici per UO, ruoli, status
- Salvataggio automatico in database

**Sezioni disponibili**:
- 👥 **Personale**: Gestione completa dipendenti
- 🏢 **Strutture**: Unità organizzative e gerarchie
- 🎭 **Ruoli**: Assegnazione ruoli multipli per dipendente
- 🔍 **Ricerca**: Ricerca globale full-text
- 📊 **Dashboard**: KPI e statistiche in tempo reale

### 🎨 Interfaccia Moderna

**Ribbon Interface**:
- Navigazione a schede stile Office
- Quick actions sempre accessibili
- Sticky header che rimane visibile
- Responsive su desktop e tablet

**Dark Theme**:
- Colori ottimizzati per ridurre affaticamento visivo
- Contrasti studiati per accessibilità
- Icone consistenti e intuitive

---

## 🏗️ Architettura

### Database SQLite con Schema Duale

```
┌─────────────────────────────────────────┐
│          SQLite Database                │
├─────────────────────────────────────────┤
│  NEW SCHEMA (primary)                   │
│  ├─ employees                           │
│  │   ├─ tx_cod_fiscale (PK)            │
│  │   ├─ reports_to_cf (FK → self)      │
│  │   ├─ cod_tns, padre_tns             │
│  │   └─ ... (20+ columns)              │
│  ├─ org_units                           │
│  │   ├─ org_unit_id (PK)               │
│  │   ├─ parent_org_unit_id (FK)        │
│  │   └─ ... (hierarchy data)           │
│  ├─ roles                               │
│  └─ version_history                     │
│                                         │
│  LEGACY SCHEMA (compatibility)          │
│  ├─ personale                           │
│  └─ strutture                           │
└─────────────────────────────────────────┘
```

### Modello Dati

**Employees** (Dipendenti):
- Dati anagrafici (CF, nome, cognome, email, etc.)
- Dati contrattuali (RAL, livello, tipo contratto, etc.)
- Gerarchie multiple (reports_to_cf, cod_tns, padre_tns)
- Assegnazioni UO e ruoli

**Org Units** (Unità Organizzative):
- Struttura ad albero gerarchica
- Responsabili e approvatori
- Statistiche dipendenti

**Versioning**:
- Snapshot completi database
- Metadata: timestamp, utente, tipo, note
- Diff automatico tra versioni

### Flusso Dati

```
┌──────────────┐
│  Excel File  │
│  (DB_ORG)    │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│  Import Service      │
│  - Validazione       │
│  - Mappatura colonne │
│  - Conflict resolution│
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  SQLite Database     │
│  - employees         │
│  - org_units         │
│  - roles             │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Orgchart Service    │
│  - Build hierarchies │
│  - Virtual ROOT      │
│  - Cycle detection   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  D3.js Visualization │
│  - Tree layouts      │
│  - Sunburst/Treemap  │
│  - Drill-down        │
└──────────────────────┘
```

---

## 🚀 Installazione

### Requisiti

- **Python 3.8+**
- **pip** (package manager)
- **Git** (opzionale, per clonare repository)

### Setup Rapido

```bash
# 1. Clona il repository
git clone https://github.com/bolzoniroberto/masterdata.git
cd masterdata/hr-management-platform

# 2. Crea virtual environment (raccomandato)
python -m venv venv

# Attiva venv:
# - Windows: venv\Scripts\activate
# - macOS/Linux: source venv/bin/activate

# 3. Installa dipendenze
pip install -r requirements.txt

# 4. Avvia l'applicazione
streamlit run app.py
```

L'applicazione sarà disponibile su **http://localhost:8501**

### Dipendenze Principali

```txt
streamlit>=1.28.0          # Framework web
pandas>=2.0.0              # Data manipulation
openpyxl>=3.1.0            # Excel I/O
pydantic>=2.0.0            # Data validation
rapidfuzz>=3.0.0           # Fuzzy string matching
streamlit-extras>=0.3.0    # UI components
```

---

## 📖 Utilizzo

### Primo Avvio

1. **Avvia l'applicazione**: `streamlit run app.py`
2. **Importa i dati iniziali**:
   - Click su **"📥 Nuovo Import"** nella ribbon
   - Carica file Excel formato DB_ORG o TNS
   - Segui il wizard guidato (4 step)
3. **Verifica l'import**:
   - Vai su **"👥 Personale"** per vedere i dipendenti
   - Vai su **"Organigrammi"** per visualizzare gerarchie

### Navigazione Principale

**Ribbon Interface** (barra superiore):

```
┌────────────────────────────────────────────────────────────┐
│ [Home] [Gestione Dati] [Organigrammi] [Tools] [Settings]  │
└────────────────────────────────────────────────────────────┘
```

- **Home**: Dashboard con KPI e statistiche
- **Gestione Dati**: Personale, Strutture, Ruoli, Posizioni
- **Organigrammi**: Visualizzazioni HR, ORG, TNS
- **Tools**: Import, Export, Confronti, Audit Log
- **Settings**: Configurazioni e preferenze

---

## 🌳 Organigrammi Interattivi

### Come Usare gli Organigrammi

#### Navigazione Base

**Albero Orizzontale/Verticale**:
- **Click nodo** → Espande/collassa figli diretti (drill-down)
- **Doppio click** → Mostra lista dipendenti del nodo
- **Drag & drop** → Pan (sposta visualizzazione)
- **Scroll mouse** → Zoom in/out
- **Click sfondo** → Reset focus, mostra tutto

**Toolbar**:
```
[🔍 Cerca] [↻ Reset] [+1 Livello] [Chiudi tutti] [⛶ Fullscreen]
```

#### Drill-down Intelligente

Click su manager → Mostra **SOLO riporti diretti**
- Auto-fit → Chart si riposiziona automaticamente
- Breadcrumb visivo → Percorso dalla ROOT al nodo corrente
- Hide siblings → Nasconde rami non rilevanti

---

## 📥 Import Dati

### Formato File Excel

#### DB_ORG (Consigliato)

File unico con tutte le colonne:

```excel
| Codice Fiscale | Titolare      | Codice | CF Responsabile | Codice TNS | Padre TNS |
|----------------|---------------|--------|-----------------|------------|-----------|
| RSSMRA80A01... | Rossi Mario   | 001    | BNCGPP75B02...  | TNS001     | ROOT      |
| BNCGPP75B02... | Bianchi Giu.  | 002    |                 | TNS002     | TNS001    |
```

**Colonne richieste**:
- `Codice Fiscale` (obbligatorio, PK)
- `Titolare` (nome completo dipendente)
- `Codice` (codice interno)

**Colonne gerarchiche**:
- `CF Responsabile Diretto` (gerarchia HR)
- `Codice TNS` + `Padre TNS` (gerarchia TNS)
- `Unità Organizzativa` (gerarchia ORG)

---

## 🔄 Gestione Versioni

### Snapshot Automatici

**Quando vengono creati**:
- ✅ Ogni import dati
- ✅ Modifiche massive (merge, batch edit)
- ✅ Manualmente dall'utente

**Milestone Certificate**:
- 🔒 Non eliminabile
- 📌 Sempre visibile in lista
- ⭐ Marcata con badge speciale

---

## 🛠️ Tecnologie

| Layer | Tecnologia | Scopo |
|-------|------------|-------|
| **Frontend** | Streamlit 1.28+ | Web UI framework |
| **Visualizzazioni** | D3.js v7 | Organigrammi interattivi |
| **Database** | SQLite 3 | Storage dati strutturati |
| **Data Processing** | Pandas 2.0+ | Manipolazione dati |
| **Validation** | Pydantic 2.0+ | Schema validation |
| **Excel I/O** | openpyxl 3.1+ | Lettura/scrittura Excel |
| **Fuzzy Matching** | RapidFuzz 3.0+ | Mappatura intelligente colonne |

---

## 📁 Struttura Progetto

```
hr-management-platform/
│
├── app.py                          # Entry point Streamlit
├── config.py                       # Configurazioni globali
├── requirements.txt                # Dipendenze Python
│
├── models/                         # Modelli dati Pydantic
│   ├── employee.py                # Employee model
│   ├── org_unit.py                # OrgUnit model
│   ├── role.py                    # Role model
│   └── hierarchy.py               # Hierarchy models
│
├── services/                       # Business logic
│   ├── database.py                # Database handler
│   ├── db_org_import_service.py   # Import da Excel
│   ├── orgchart_data_service.py   # Costruzione gerarchie
│   ├── version_manager.py         # Versioning & snapshots
│   └── validator.py               # Validazione dati
│
├── ui/                            # Componenti UI Streamlit
│   ├── ribbon_sticky.py           # Ribbon interface
│   ├── orgchart_hr_view.py        # Organigramma HR
│   ├── orgchart_org_view.py       # Organigramma ORG
│   ├── orgchart_tns_structures_view.py  # Organigramma TNS
│   ├── wizard_import_modal.py     # Wizard import guidato
│   └── ...
│
└── docs/                          # Documentazione
    └── ORGANIGRAMMI_FIXES_2026-02-22.md
```

---

## 🤝 Contribuire

### Come Contribuire

1. **Fork il repository**
2. **Crea un branch per la feature**: `git checkout -b feature/nome-feature`
3. **Implementa le modifiche** con codice pulito e documentato
4. **Commit**: `git commit -m "feat: descrizione feature"`
5. **Push e crea Pull Request**

---

## 📄 Licenza

Questo progetto è proprietario e riservato.

**© 2024-2026 Roberto Bolzoni**. Tutti i diritti riservati.

---

## 📧 Contatti & Supporto

**Autore**: Roberto Bolzoni
**GitHub**: [@bolzoniroberto](https://github.com/bolzoniroberto)

**Segnalazione Bug**: [GitHub Issues](https://github.com/bolzoniroberto/masterdata/issues)

---

## 📚 Documentazione Aggiuntiva

- [🌳 Organigrammi - Fix Log](ORGANIGRAMMI_FIXES_2026-02-22.md)

---

**Made with ❤️ using Streamlit + D3.js**
