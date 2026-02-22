# 🧪 Guida Testing Wizard Merge/Arricchimento

## 📋 Prerequisiti

1. **Avvia l'applicazione**:
   ```bash
   cd /Users/robertobolzoni/hr-management-platform
   streamlit run app.py
   ```

2. **Verifica che il database abbia dati iniziali** (almeno 10-20 dipendenti)
   - Se vuoto, esegui prima un import DB_ORG completo

3. **File di test disponibili** in `/tests/merge_test_files/`:
   - ✅ `test_salary_review.xlsx` (5 dipendenti)
   - ✅ `test_tns_reorg.xlsx` (3 strutture)
   - ✅ `test_banding.xlsx` (4 dipendenti)
   - ✅ `test_cessati_assunti.xlsx` (5 dipendenti, include 2 nuovi)

---

## 🧪 Test 1: Salary Review

**Obiettivo**: Aggiornare RAL solo per subset dipendenti (post salary review)

### Step-by-Step

1. **Apri wizard**:
   - Click ribbon **"Gestione Dati"**
   - Expander **"📥 Import/Export"**
   - Click **"🔄 Merge/Arricchimento"**

2. **Step 1: Upload File**:
   - Carica: `/tests/merge_test_files/test_salary_review.xlsx`
   - Verifica: **5 righe** caricate
   - Auto-detection dovrebbe rilevare: **salary_review**
   - Click **"➡️ Avanti"**

3. **Step 2: Tipo & Chiave**:
   - Verifica tipo: **salary_review**
   - Chiave matching: **tx_cod_fiscale**
   - Leggi info: "Strategia OVERWRITE su RAL, KEEP_TARGET su resto"
   - Click **"➡️ Avanti"**

4. **Step 3: Column Mapping**:
   - Verifica mapping automatico:
     - `tx_cod_fiscale` → `tx_cod_fiscale` ✓
     - `ral` → `ral` ✓
     - `monthly_gross` → `monthly_gross` ✓
   - Click **"➡️ Avanti"**

5. **Step 4: Gap Analysis**:
   - **Matched**: 5 (i 5 dipendenti nel file che esistono anche in DB)
   - **New**: 0 (nessun nuovo dipendente)
   - **Gap**: N (dipendenti in DB non nel file = senza variazione RAL)
   - Verifica tab **"Matched"**: mostra i 5 dipendenti
   - Verifica tab **"Gap"**: mostra dipendenti NON aggiornati (normale per salary review)
   - Click **"➡️ Avanti"**

6. **Step 5: Merge Preview**:
   - Verifica **"Record con modifiche"**: 5
   - Verifica preview: mostra before/after RAL
   - **Conflitti**: 0 (OVERWRITE non genera conflitti)
   - Click **"➡️ Avanti"**

7. **Step 6: Conferma**:
   - Verifica riepilogo:
     - Record da aggiornare: **5**
     - Gap: **N** (dipendenti senza variazione)
   - Seleziona **"📸 Crea snapshot"**: ✓
   - Seleziona **"✅ Valida dati"**: ✓
   - Click **"✅ APPLICA MERGE"**

8. **Verifica Risultato**:
   - ✅ Merge completato: **5 record aggiornati**
   - ✅ Snapshot creato
   - ✅ Audit log registrato

### Validazione Post-Merge

```bash
# Verifica che RAL siano state aggiornate
python3 << 'EOF'
from services.database import DatabaseHandler
import pandas as pd

db = DatabaseHandler()
df = pd.read_sql_query("SELECT tx_cod_fiscale, ral FROM employees WHERE tx_cod_fiscale IN ('RSSMRA80A01H501U', 'BNCGPP75B02F205W')", db.get_connection())
print(df)
# Dovrebbe mostrare RAL aggiornate (52000, 48000)
EOF
```

---

## 🧪 Test 2: TNS Reorganization

**Obiettivo**: Modificare padre_tns solo per strutture coinvolte in riorganizzazione

### Step-by-Step

1. **Apri wizard** (come Test 1)

2. **Step 1: Upload**:
   - Carica: `test_tns_reorg.xlsx`
   - Verifica: **3 righe**
   - Auto-detection: **tns_reorg**

3. **Step 2: Tipo & Chiave**:
   - Tipo: **tns_reorg**
   - Chiave: **cod_tns**
   - Info: "OVERWRITE su padre_tns, responsabile_tns"

4. **Step 3-6**: Segui stesso flusso Test 1

### Verifica Attesa

- **Matched**: 3 (le 3 strutture TNS nel file)
- **Gap**: N (strutture TNS non toccate dalla reorg)
- **Merge**: Solo padre_tns e responsabile_tns aggiornati

---

## 🧪 Test 3: Banding Enrichment

**Obiettivo**: Arricchire dipendenti con nuove colonne (job_family, band, grade)

### Step-by-Step

1. **Apri wizard**

2. **Step 1: Upload**:
   - Carica: `test_banding.xlsx`
   - Verifica: **4 righe**
   - Auto-detection: **banding**

3. **Step 2: Tipo & Chiave**:
   - Tipo: **banding**
   - Chiave: **tx_cod_fiscale**
   - Info: "Strategia FILL_EMPTY (non sovrascrive esistenti)"

4. **Step 5: Merge Preview**:
   - Verifica strategia: **FILL_EMPTY**
   - Se campi già popolati → NON sovrascritti
   - Se campi vuoti → popolati

### Verifica Attesa

- **Matched**: 4
- **Merge**: Solo campi vuoti popolati
- Campi già esistenti NON modificati

---

## 🧪 Test 4: Cessati/Assunti Detection

**Obiettivo**: Rilevare potenziali cessati (gap) e assunti (new)

### Step-by-Step

1. **Apri wizard**

2. **Step 1: Upload**:
   - Carica: `test_cessati_assunti.xlsx`
   - Verifica: **5 righe** (include 2 nuovi CF: NEWCF1X, NEWCF2Y)
   - Auto-detection: **cessati_assunti**

3. **Step 4: Gap Analysis** ⚠️ **CRITICO**:
   - **Matched**: 3 (dipendenti esistenti che sono anche nel file)
   - **New**: 2 (NEWCF1X, NEWCF2Y = **potenziali assunti**)
   - **Gap**: N (dipendenti in DB NON nel file = **potenziali cessati**)

   - ⚠️ **Alert Critical Gaps**:
     - Se tra i gap ci sono manager → Alert rosso
     - Messaggio: "X gap critici rilevati!"
     - Expander mostra dettagli manager gap

4. **Tab "Gap"**:
   - Warning: "⚠️ Questi record potrebbero essere **cessati**"
   - Export CSV disponibile

5. **Tab "New"**:
   - Info: "🆕 Questi record potrebbero essere **assunti**"
   - Mostra NEWCF1X, NEWCF2Y

### Verifica Attesa

- Alert automatico se gap include manager
- Gap chiaramente marcati come potenziali cessati
- New chiaramente marcati come potenziali assunti

---

## 🔍 Checklist Completa Testing

### Funzionalità Generali
- [ ] Wizard si apre da ribbon "Gestione Dati" → "Import/Export"
- [ ] Progress indicator mostra step corrente
- [ ] Bottone "⬅️ Indietro" funziona in tutti gli step
- [ ] Dialog modale "large" width

### Step 1: Upload
- [ ] Upload file Excel funziona
- [ ] Auto-detection tipo import corretta per tutti i 4 file
- [ ] Preview dati mostra prime 10 righe
- [ ] Metrics (righe, colonne) corrette

### Step 2: Tipo & Chiave
- [ ] Select tipo import funziona
- [ ] Select chiave matching funziona
- [ ] Info descrittiva per ogni tipo mostrata
- [ ] Validation duplicati chiave funziona (se applicabile)

### Step 3: Column Mapping
- [ ] Fuzzy matching automatico funziona
- [ ] Mapping table mostra file → DB
- [ ] Override manuale funziona
- [ ] Unmapped columns warning mostrato

### Step 4: Gap Analysis
- [ ] Matching eseguito correttamente
- [ ] Metrics (matched/new/gap) corrette
- [ ] Alert critical gaps appare se necessario
- [ ] Tabs Matched/Gap/New funzionano
- [ ] Export CSV gap funziona
- [ ] Recommendations mostrate

### Step 5: Merge Preview
- [ ] Preview before/after corretta
- [ ] Conflict detection funziona
- [ ] Conflict resolution UI funziona
- [ ] Strategie per campo visualizzate

### Step 6: Confirmation
- [ ] Riepilogo accurato
- [ ] Checkbox snapshot/validation funzionano
- [ ] Apply merge esegue correttamente
- [ ] Success message con dettagli
- [ ] Snapshot creato se selezionato
- [ ] Audit log registrato

### Post-Merge
- [ ] Dati effettivamente aggiornati in DB
- [ ] Solo campi previsti modificati
- [ ] Gap records NON modificati
- [ ] Snapshot ripristinabile
- [ ] Audit log consultabile

---

## 🐛 Bug da Segnalare

Se durante il testing trovi problemi, annota:

1. **Step dove si verifica**
2. **Tipo import testato**
3. **Messaggio errore** (se presente)
4. **Comportamento atteso vs reale**
5. **Screenshot** (se UI issue)

---

## ✅ Success Criteria

**Test considerato PASSED se**:
- ✅ Tutti e 4 use cases completano senza errori
- ✅ Merge aggiorna solo record matched
- ✅ Gap records rimangono invariati
- ✅ Strategie merge rispettate (OVERWRITE, FILL_EMPTY, etc.)
- ✅ Snapshot creato e ripristinabile
- ✅ Audit log completo e accurato
- ✅ Critical gaps alert funziona (Test 4)
- ✅ UI responsiva e intuitiva

---

**Data test**: _______________
**Tester**: _______________
**Risultato**: ⬜ PASSED  ⬜ FAILED (specificare issue)
