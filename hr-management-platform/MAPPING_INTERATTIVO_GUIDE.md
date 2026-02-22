# Guida Mapping Interattivo Colonne - Import Wizard

## ✅ Implementato!

Il wizard di import ora include un **mapping interattivo** delle colonne che ti permette di:
- ✅ Vedere quali colonne servono per i 3 organigrammi
- ✅ Associare manualmente le colonne Excel anche se i nomi non corrispondono
- ✅ Ricevere suggerimenti automatici basati su nome e posizione
- ✅ Salvare il mapping per riutilizzarlo

---

## 🎯 Come Funziona

### Step 1: Carica File Excel
1. Vai al tab **"Gestione Dati"** → **"Nuovo Import"**
2. Carica il file Excel DB_ORG
3. Il wizard rileva automaticamente le colonne

### Step 2: Mappatura Colonne

Il wizard mostra 3 sezioni:

#### 🔴 Colonne Obbligatorie
Queste DEVONO essere mappate per procedere:
- **ID** - Identificativo univoco posizione
- **TxCodFiscale** - Codice Fiscale dipendente
- **Titolare** - Nome dipendente
- **Unità Organizzativa** - Unità organizzativa livello 1

#### ⚪ Colonne Opzionali
Utili ma non obbligatorie:
- **Unità Organizzativa 2** - Livello 2 gerarchia
- **ReportsTo** - Parent posizione ORG (colonna AC)
- **Matricola** - Matricola dipendente
- **Email** - Email aziendale

#### 🌳 Colonne Gerarchie Organigrammi (Opzionali)
**NUOVE!** Per costruire i 3 organigrammi:

| Campo Sistema | Descrizione | Colonna Suggerita |
|---------------|-------------|-------------------|
| **CF Responsabile Diretto** | 👤 CF del responsabile diretto | **CZ** (colonna 104) |
| **Codice TNS** | 🔢 Codice TNS dipendente | **CB** (colonna 80) |
| **Padre TNS** | 👆 Codice TNS del parent | **CC** (colonna 81) |

---

## 🔍 Auto-detect Intelligente

Il wizard prova automaticamente a rilevare le colonne in base a:

### 1. Nome Esatto (case-insensitive)
Se la colonna Excel si chiama **esattamente** come il campo sistema (es: "TxCodFiscale"), viene mappata automaticamente.

### 2. Fuzzy Matching su Alias
Se non trova match esatto, cerca tra gli alias:
- **CF Responsabile Diretto**: cerca "cf responsabile", "responsabile diretto", "cf superiore", "resp diretto"
- **Codice TNS**: cerca "codice tns", "cod tns", "tns code", "cod_tns"
- **Padre TNS**: cerca "padre tns", "parent tns", "tns parent"

### 3. Mappatura Manuale
Se l'auto-detect non funziona, puoi selezionare manualmente dal dropdown:
- Mostra TUTTE le colonne del file Excel
- Puoi lasciare vuoto se non hai quel dato
- Suggerimento sulla posizione colonna (CZ, CB, CC)

---

## 📋 Esempio Pratico

### Scenario: File Excel con nomi diversi

Il tuo file ha:
- Colonna CZ: "CF_Responsabile" (invece di "CF Responsabile Diretto")
- Colonna CB: "TNS_Code" (invece di "Codice TNS")
- Colonna CC: "TNS_Parent" (invece di "Padre TNS")

**Cosa fa il wizard:**

1. **Auto-detect prova:**
   - "CF_Responsabile" → cerca "cf responsabile" → ✅ MATCH!
   - "TNS_Code" → cerca "tns code" → ✅ MATCH!
   - "TNS_Parent" → cerca "tns parent" → ✅ MATCH!

2. **Se fallisce:**
   - Ti mostra dropdown con TUTTE le colonne
   - Tu selezioni manualmente "CF_Responsabile" per "CF Responsabile Diretto"
   - Tu selezioni manualmente "TNS_Code" per "Codice TNS"
   - Tu selezioni manualmente "TNS_Parent" per "Padre TNS"

3. **Salvi il mapping:**
   - Click su "💾 Salva Mappatura"
   - La prossima volta il wizard userà questa mappatura salvata!

---

## 🚀 Test del Nuovo Sistema

### 1. Cancella Database (opzionale)
Per fare un test pulito:
```bash
rm data/db/app.db
```

### 2. Riavvia App
```bash
streamlit run app.py
```

### 3. Import con Mapping Interattivo

1. **Carica file Excel**
   - Tab "Gestione Dati" → "Nuovo Import"
   - Seleziona file DB_ORG

2. **Verifica Auto-detect**
   - Il wizard mostra % di colonne rilevate
   - Se 100% → Skip automatico Step 2
   - Se < 100% → Vai a Step 2 per mappare manualmente

3. **Step 2: Mapping Manuale (se necessario)**
   - Verifica le colonne rilevate
   - Correggi quelle sbagliate usando i dropdown
   - **IMPORTANTE**: Mappa le 3 colonne gerarchie:
     - CF Responsabile Diretto (CZ)
     - Codice TNS (CB)
     - Padre TNS (CC)

4. **Completa Import**
   - Click "Avanti →"
   - Conferma import
   - Il wizard esegue import REALE (non più simulato!)

### 4. Verifica Dati Importati

```bash
python3 -c "
import sqlite3
from pathlib import Path

conn = sqlite3.connect('data/db/app.db')
cursor = conn.cursor()

# Check hierarchy data populated
cursor.execute('SELECT COUNT(*) FROM employees WHERE reports_to_cf IS NOT NULL')
hr_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM employees WHERE cod_tns IS NOT NULL')
tns_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM org_units WHERE parent_org_unit_id IS NOT NULL')
org_count = cursor.fetchone()[0]

print('✅ Dati Gerarchie Popolati:')
print(f'  HR (reports_to_cf): {hr_count} dipendenti')
print(f'  TNS (cod_tns): {tns_count} dipendenti')
print(f'  ORG (parent_org_unit_id): {org_count} posizioni')

conn.close()
"
```

### 5. Test Organigrammi

1. Tab **"Organigrammi"** nella ribbon
2. Testa i 3 organigrammi:
   - **HR Hierarchy** - Deve mostrare albero persone
   - **ORG Hierarchy** - Deve mostrare albero posizioni
   - **TNS Structures** - Deve mostrare albero TNS

---

## ⚙️ Configurazione Avanzata

### Salvare Mapping Personalizzato

Il mapping viene salvato in:
```
config/column_mapping.json
```

Puoi editarlo manualmente se necessario:
```json
{
  "ID": "Codice_Posizione",
  "TxCodFiscale": "CF",
  "Titolare": "Nome_Completo",
  "CF Responsabile Diretto": "CF_Resp",
  "Codice TNS": "TNS_Code",
  "Padre TNS": "TNS_Parent"
}
```

### Riutilizzo Automatico

Il wizard riutilizza automaticamente il mapping salvato per:
- ✅ Import successivi con stesso formato
- ✅ Auto-compilare i dropdown
- ✅ Velocizzare il processo

---

## 🎉 Vantaggi

### Prima (Mapping Hardcoded):
❌ Nomi colonne DEVONO essere esatti
❌ Se cambiano, import fallisce
❌ Nessuna flessibilità

### Adesso (Mapping Interattivo):
✅ Rileva automaticamente variazioni nomi
✅ Dropdown manuale se serve
✅ Suggerimenti su posizione colonne
✅ Salva per riutilizzo
✅ Funziona con QUALSIASI formato Excel!

---

## 📝 Note Importanti

### Colonne Gerarchie Opzionali

Le 3 colonne gerarchie (CZ, CB, CC) sono **OPZIONALI**:
- Se non le mappi → Import funziona comunque
- Ma → Organigrammi non vengono generati (dati mancanti)

### ReportsTo (AC) è Diverso

- **ReportsTo (AC)** → Per gerarchia POSIZIONI (org_units)
- **CF Responsabile Diretto (CZ)** → Per gerarchia PERSONE (employees)

Sono DUE campi diversi per DUE organigrammi diversi!

---

## 🆘 Troubleshooting

### "Colonna non rilevata"
**Soluzione**: Usa il dropdown manuale per selezionarla

### "Import completato ma organigrammi vuoti"
**Causa**: Colonne CZ/CB/CC non mappate
**Soluzione**: Rifai import e mappa le colonne gerarchie

### "Dropdown non mostra la mia colonna"
**Causa**: La colonna non esiste nel file
**Soluzione**: Verifica che il file Excel abbia effettivamente quella colonna

---

## ✅ Checklist Test

- [ ] Riavvia app
- [ ] Cancella database vecchio
- [ ] Carica file Excel
- [ ] Verifica auto-detect funziona
- [ ] Mappa manualmente colonne CZ, CB, CC (se non auto-rilevate)
- [ ] Salva mapping
- [ ] Completa import
- [ ] Verifica dati popolati (script Python)
- [ ] Test organigrammi HR, ORG, TNS
- [ ] Conferma alberi vengono visualizzati

---

**Pronto per testare!** 🚀
