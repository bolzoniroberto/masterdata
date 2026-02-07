# 📦 Guida Sistema Versioning e Recovery

## Panoramica

Il sistema HR Management Platform ora include un **sistema completo di versioning con snapshot recuperabili**. Ogni volta che importi un file Excel, viene creato automaticamente uno snapshot che può essere ripristinato in qualsiasi momento.

## 🎯 Problema Risolto

**Prima:**
- Import Excel sovrascriveva sempre i dati
- Nessun modo di tornare indietro dopo un import errato
- Audit log veniva cancellato ad ogni import
- Difficile tracciare le modifiche nel tempo

**Ora:**
- ✅ Ogni import crea uno snapshot recuperabile
- ✅ Snapshot manuali quando vuoi (non solo durante import)
- ✅ Puoi ripristinare qualsiasi versione precedente
- ✅ Audit log persistente mai cancellato
- ✅ Preview semplice del contenuto file prima di confermare
- ✅ Tracciabilità completa di tutte le operazioni

---

## 🚀 Funzionalità Principali

### 1. Snapshot Automatici

**Quando vengono creati:**
- Ad ogni import Excel (con o senza preview)
- Automaticamente, senza intervento manuale
- Prima di ogni operazione di restore (backup automatico)

**Cosa contiene uno snapshot:**
```json
{
  "metadata": {
    "import_version_id": 5,
    "timestamp": "2026-02-07T10:30:15",
    "source_filename": "TNS_HR_Data.xls",
    "user_note": "Aggiornamento organigramma Q1",
    "personale_count": 245,
    "strutture_count": 48
  },
  "personale": [...],  // Tutti i record dipendenti
  "strutture": [...]   // Tutti i record strutture
}
```

**Dove vengono salvati:**
- Directory: `data/snapshots/`
- Formato: `snapshot_{version_id}_{timestamp}.json`
- Esempio: `snapshot_5_20260207_103015.json`

### 2. Snapshot Manuali

**📸 Crea snapshot quando vuoi, non solo durante import!**

Gli snapshot manuali ti permettono di salvare lo stato attuale del database in qualsiasi momento, mentre stai lavorando con i dati. Sono perfetti per creare punti di ripristino prima di operazioni rischiose.

**Quando usarli:**
- Stai per fare modifiche importanti e vuoi poter tornare indietro
- Hai completato un gruppo di modifiche coerenti
- Prima di operazioni rischiose (bulk delete, merge, ecc.)
- Alla fine della giornata lavorativa
- Prima di test o sperimentazioni

**Come crearli:**
1. **In qualsiasi momento**, mentre lavori con i dati:
2. Sidebar → Clicca "📸 Crea Snapshot Manuale"
3. Aggiungi nota descrittiva (obbligatoria)
4. Conferma → Snapshot salvato

**Differenza con Snapshot Import:**

| Tipo | Quando | Identificazione | File Origine |
|------|--------|-----------------|--------------|
| 📦 Import | Automatico ad ogni caricamento Excel | Icona 📦 | Nome file Excel caricato |
| 📸 Manuale | Su richiesta utente durante lavoro | Icona 📸 | MANUAL_SNAPSHOT |

**Esempio uso:**
```
Situazione: Stai per riorganizzare 50 dipendenti tra reparti

1. Prima di iniziare: Crea snapshot manuale
   Nota: "Prima di riorganizzazione Q1 - stato iniziale"

2. Fai le modifiche (modifica 50 record)

3. Dopo aver finito: Crea altro snapshot manuale
   Nota: "Dopo riorganizzazione Q1 - completata"

4. Se qualcosa non va: Ripristina snapshot "Prima di..."
```

**Vantaggi:**
- ✅ Protezione contro errori mentre lavori
- ✅ Punti di ripristino personalizzati
- ✅ Non legati a import Excel
- ✅ Stessa funzionalità di restore degli snapshot import
- ✅ Visibili nella lista con icona 📸 distintiva

### 3. Preview Pre-Import (Semplificata)

**Prima di ogni import puoi vedere:**
1. **Conteggi immediati**:
   - 👥 Dipendenti (Personale)
   - 🏗️ Strutture Organizzative
   - 📊 Record Totali
2. **Anteprima dati**: Prime 5 righe di ogni tipo
3. **Info file**: Nome e dimensione
4. **Nota descrittiva** personalizzabile
5. **Conferma o annulla** l'operazione

**Vantaggi nuova preview:**
- ✅ Più chiara e intuitiva
- ✅ Nessuna confusione con severity/modifiche
- ✅ Vedi esattamente cosa c'è nel file
- ✅ Verifica veloce dei dati

### 4. Vista "📦 Gestione Versioni"

**Accessibile dal menu principale, offre:**

#### Visualizzazione Snapshot
- Lista completa di tutti gli snapshot
- Dettagli: ID, data/ora, file origine, nota, record counts
- Dimensione in MB di ogni snapshot
- Spazio totale utilizzato

#### Ripristino Versioni
1. Seleziona versione da ripristinare
2. Visualizza dettagli snapshot
3. Opzione: crea backup automatico (consigliato ✅)
4. Conferma sovrascrittura con checkbox
5. Ripristina → database torna a quella versione
6. Tutti i dati in session state vengono ricaricati

#### Gestione Spazio
- Pulizia automatica: mantieni ultimi N snapshot
- Eliminazione manuale di snapshot specifici
- Monitoraggio spazio utilizzato

---

## 📖 Tutorial Passo-Passo

### Scenario 1: Primo Import con Versioning

```
1. Apri http://localhost:8501
2. Nella sidebar, attiva "🔍 Mostra anteprima file"
3. Carica file Excel
4. Nella preview vedi:
   - 👥 Dipendenti: 245
   - 🏗️ Strutture: 48
   - 📊 Record Totali: 293
   - Prime 5 righe di anteprima
5. Aggiungi nota: "Versione iniziale database"
6. Clicca "✅ Carica nel Database"
7. Messaggio di conferma:
   ✅ Dati caricati con successo nel database!
   📦 Snapshot creato automaticamente per recovery
   🎉 Puoi ora lavorare con i dati
```

### Scenario 2: Snapshot Manuale Durante Lavoro

```
Situazione: Hai appena finito di modificare 15 dipendenti e vuoi salvare lo stato

1. Sidebar → Clicca "📸 Crea Snapshot Manuale"
2. Dialog si apre mostrando:
   - 👥 Personale: 245
   - 🏗️ Strutture: 48
3. Aggiungi nota: "Dopo modifica ruoli reparto IT - 15 dipendenti aggiornati"
4. Clicca "✅ Crea Snapshot"
5. Messaggio: ✅ Snapshot creato con successo! 📦 snapshot_5_20260207_143022.json
6. Vai a "📦 Gestione Versioni" → Vedi snapshot con icona 📸 e tipo "Manuale"
```

### Scenario 3: Secondo Import con Nuovo File

```
1. Modifica il file Excel e salva
2. Sidebar → Carica nuovo file
3. Preview mostra:
   - 👥 Dipendenti: 250 (+5 rispetto a prima)
   - 🏗️ Strutture: 50 (+2 rispetto a prima)
   - Anteprima prime 5 righe
4. Aggiungi nota: "Aggiornamento Q1 - nuovi assunti e strutture"
5. Conferma import
6. Ora hai 3 snapshot: #1 (import iniziale), #2 (snapshot manuale), #3 (nuovo import)
```

### Scenario 4: Errore - Ripristino Versione Precedente

```
Situazione: Hai importato file sbagliato per errore!

1. Vai a "📦 Gestione Versioni"
2. Vedi la lista:
   - Version #3: oggi 11:45 (ERRATO!)
   - Version #2: oggi 10:30 (OK)
   - Version #1: ieri 15:20 (OK)

3. Sezione "🔄 Ripristina Versione"
4. Seleziona: "#2: 07/02/2026 10:30 - TNS_HR_Data.xls"
5. Verifica dettagli snapshot
6. ✅ Attiva "Crea backup automatico" (importante!)
7. ⚠️ Attiva "Confermo di voler sovrascrivere"
8. Clicca "🔄 Ripristina Questa Versione"
9. Attendere...
10. Successo! Database ripristinato a version #2
11. Un backup automatico della version #3 è stato salvato (version #-1)
```

### Scenario 5: Gestione Spazio Snapshot

```
Situazione: Hai 100 snapshot e vuoi liberare spazio

1. Vai a "📦 Gestione Versioni"
2. Vedi:
   - Snapshot Disponibili: 100
   - Spazio Utilizzato: 523.8 MB

3. Sezione "🗑️ Gestione Spazio"
4. Imposta: "Mantieni ultimi 30 snapshot"
5. Messaggio: "⚠️ Hai 70 snapshot che verranno eliminati"
6. Clicca "🗑️ Pulisci Snapshot Vecchi"
7. Risultato:
   ✅ Eliminati 70 snapshot vecchi
   - Snapshot rimasti: 30
   - Spazio utilizzato: 157.1 MB
```

---

## 🔒 Sicurezza e Best Practices

### Sicurezza

✅ **Backup Automatico Prima del Restore**
- Sempre consigliato
- Crea snapshot di sicurezza (ID: -1)
- Filename: "AUTO_BACKUP"
- Recuperabile in caso di errori

✅ **Conferma Esplicita**
- Richiesta prima di ogni sovrascrittura
- Checkbox: "Confermo di voler sovrascrivere i dati attuali"
- Previene operazioni accidentali

✅ **Audit Log Completo**
- Tutte le operazioni tracciate
- Include RESTORE operations
- Mai cancellato automaticamente
- Tracciabilità completa

✅ **Snapshot Immutabili**
- File JSON creati in sola lettura
- Non modificabili dopo creazione
- Solo eliminazione manuale possibile

### Best Practices

📝 **Note Descrittive**
```
✅ BUONO: "Riorganizzazione Q1 - cambio responsabili IT e HR"
✅ BUONO: "Correzione codici fiscali errati reparto amministrazione"
✅ BUONO: "Aggiornamento gerarchie dopo fusione reparti"

❌ CATTIVO: "Import"
❌ CATTIVO: "Modifica"
❌ CATTIVO: ""  (vuoto)
```

🕐 **Frequenza Snapshot**
- Non c'è limite al numero di snapshot
- Crea snapshot ad ogni import significativo
- **Usa snapshot manuali** prima di operazioni rischiose:
  - Prima di bulk edit/delete
  - Alla fine della giornata lavorativa
  - Prima di test o sperimentazioni
  - Dopo completamento gruppo modifiche coerenti
- Mantieni almeno 30-50 snapshot recenti
- Usa cleanup per gestire spazio

📸 **Quando Usare Snapshot Manuali**
```
✅ BUONI MOMENTI:
- Prima di riorganizzare 50+ dipendenti tra reparti
- Prima di eliminare strutture organizzative
- Prima di modifiche massive ai ruoli di approvazione
- Alla fine del giorno dopo lavoro importante
- Prima di test/validazioni su dati reali

❌ NON NECESSARI:
- Dopo ogni singola modifica minore
- Già fatto import Excel (che crea snapshot automatico)
- Prima di operazioni facilmente reversibili
```

💾 **Gestione Spazio**
- Snapshot tipico: 2-5 MB
- 50 snapshot ≈ 100-250 MB
- Cleanup consigliato ogni 2-3 mesi
- Mantieni sempre almeno 10-20 snapshot

🔄 **Restore Strategy**
```
Prima di restore importante:
1. Verifica dettagli snapshot (data, record counts)
2. Attiva SEMPRE backup automatico ✅
3. Aggiungi nota al restore (es: "Rollback import errato")
4. Verifica dati dopo restore
5. Se qualcosa non va, ripristina il backup automatico
```

---

## 📊 Monitoraggio e Manutenzione

### Dashboard - Modifiche Recenti

Nella vista **📊 Dashboard** trovi il widget:

```
🕐 Modifiche Recenti (Ultime 24h)
┌──────────┬──────┬──────┬──────┐
│🔴 CRITICAL│🟠 HIGH│🟡 MEDIUM│⚪ LOW│
│     3    │  12  │   45   │  89 │
└──────────┴──────┴──────┴──────┘
         [📖 Vedi Dettagli Storico]
```

### Storico Modifiche

Vista **🔍 Confronto & Storico** → Tab **📖 Storico Modifiche**:

**Filtri disponibili:**
- 📦 Versione Import (dropdown)
- ⚠️ Gravità (CRITICAL/HIGH/MEDIUM/LOW)
- 📋 Tabella (personale/strutture)

**Visualizzazione:**
- Tabella con descrizioni italiane
- Esempio: "Dipendente ROSSI MARIO ha cambiato approvatore da BIANCHI a VERDI"
- Export report Excel

### Metriche Versioning

In **📦 Gestione Versioni**:
```
┌─────────────────────┬──────────────────┬─────────────────┐
│📦 Snapshot Disponibili│💾 Spazio Totale │🔢 Versione Corrente│
│         42         │    215.3 MB    │      #45       │
└─────────────────────┴──────────────────┴─────────────────┘
```

---

## 🔧 Troubleshooting

### Problema: Snapshot non viene creato

**Sintomo:** Import completato ma nessun snapshot nella lista

**Soluzione:**
1. Verifica che `data/snapshots/` esista
2. Controlla permessi scrittura directory
3. Verifica log server per errori
4. Riavvia server Streamlit

### Problema: Restore fallisce

**Sintomo:** Errore durante ripristino versione

**Soluzione:**
1. Verifica che il file snapshot esista
2. Controlla che non sia corrotto (apri JSON in editor)
3. Verifica permessi lettura file
4. Prova con backup automatico disattivato
5. Controlla audit log per dettagli errore

### Problema: Spazio insufficiente

**Sintomo:** Disco pieno, troppi snapshot

**Soluzione:**
1. Vai a "Gestione Versioni"
2. Gestione Spazio → "Pulisci Snapshot Vecchi"
3. Mantieni solo 20-30 snapshot
4. Considera backup esterni per snapshot critici
5. Archivia snapshot vecchi su storage esterno

### Problema: Performance lenta con molti snapshot

**Sintomo:** Lista snapshot impiega tempo a caricare

**Soluzione:**
1. Riduci numero snapshot (< 100)
2. Usa cleanup automatico regolarmente
3. Considera database più performante per grandi quantità
4. Verifica che JSON non siano corrotti

---

## 📚 Riferimenti Tecnici

### File e Directory

```
hr-management-platform/
├── data/
│   ├── snapshots/          ← Snapshot JSON
│   │   ├── snapshot_1_*.json
│   │   ├── snapshot_2_*.json
│   │   └── ...
│   └── db/
│       └── app.db          ← Database SQLite (import_versions, audit_log)
├── services/
│   ├── version_manager.py  ← Logica snapshot/restore
│   ├── database.py         ← DB + audit + versioning
│   └── ...
└── ui/
    ├── version_management_view.py  ← Vista gestione versioni
    └── ...
```

### Database Schema

**Tabella `import_versions`:**
```sql
CREATE TABLE import_versions (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP,
    source_filename TEXT,
    user_note TEXT,
    personale_count INTEGER,
    strutture_count INTEGER,
    changes_summary TEXT,
    completed BOOLEAN,
    completed_at TIMESTAMP
)
```

**Tabella `audit_log`:**
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP,
    table_name TEXT,
    operation TEXT,
    record_key TEXT,
    before_values TEXT,      -- JSON
    after_values TEXT,       -- JSON
    import_version_id INTEGER,  -- Link a version
    change_severity TEXT,       -- CRITICAL/HIGH/MEDIUM/LOW
    field_name TEXT
)
```

### API VersionManager

```python
from services.version_manager import VersionManager

vm = VersionManager(db_handler, snapshots_dir)

# Crea snapshot
snapshot_path = vm.create_snapshot(
    import_version_id=5,
    source_filename="data.xls",
    user_note="Update Q1"
)

# Lista snapshot
snapshots = vm.list_snapshots()

# Ripristina
success, msg = vm.restore_snapshot(
    snapshot_file_path="/path/to/snapshot.json",
    create_backup=True
)

# Cleanup
deleted = vm.cleanup_old_snapshots(keep_last_n=30)
```

---

## 🆘 Supporto

**Domande frequenti:**

**Q: Posso ripristinare un snapshot eliminato?**
A: No, l'eliminazione è permanente. Fai backup esterni degli snapshot critici.

**Q: Gli snapshot includono l'audit log?**
A: No, solo i dati (personale + strutture). L'audit log rimane nel database SQLite.

**Q: Posso esportare snapshot in Excel?**
A: Sì, nella vista gestione versioni c'è funzione export (in sviluppo).

**Q: Quanto spazio occupa tipicamente?**
A: 2-5 MB per snapshot, dipende dal numero di record.

**Q: Posso fare rollback di un rollback?**
A: Sì! Ogni restore crea un nuovo snapshot, quindi puoi sempre tornare indietro.

---

## ✅ Checklist Operativa

### Import Quotidiano
- [ ] Carica file Excel con preview attiva
- [ ] Verifica modifiche CRITICAL/HIGH
- [ ] Aggiungi nota descrittiva
- [ ] Conferma import
- [ ] Verifica "Snapshot creato" nel messaggio

### Manutenzione Settimanale
- [ ] Controlla "Gestione Versioni"
- [ ] Verifica numero snapshot disponibili
- [ ] Controlla spazio utilizzato
- [ ] Se > 100 snapshot, esegui cleanup (mantieni 50)

### Manutenzione Mensile
- [ ] Review audit log in "Storico Modifiche"
- [ ] Verifica anomalie nel dashboard
- [ ] Backup snapshot critici su storage esterno
- [ ] Cleanup aggressivo se necessario (mantieni 30)

### In Caso di Emergenza
- [ ] Vai immediatamente a "Gestione Versioni"
- [ ] Identifica ultima versione corretta
- [ ] Attiva "Crea backup automatico"
- [ ] Ripristina versione corretta
- [ ] Verifica dati ripristinati
- [ ] Documenta incidente in nota

---

**Ultima revisione:** 2026-02-07
**Versione documento:** 1.0
**Sistema versioning:** Operativo ✅
