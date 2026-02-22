# Organigrammi Enhancements - 2026-02-22

## Summary

Aggiunte funzionalità avanzate agli organigrammi HR per migliorare usabilità e capacità di analisi:

1. ✅ **Rilevamento e visualizzazione orfani** - Identifica nodi senza responsabile
2. ✅ **Tooltip dettagliati** - Informazioni complete al mouse over
3. ✅ **Filtri avanzati** - Panel con criteri multipli di filtraggio

---

## 1. Rilevamento Orfani

### Cos'è un nodo orfano?
Un **nodo orfano** è un dipendente che:
- Ha `reports_to_cf` vuoto o NULL
- Riporta direttamente alla ROOT virtuale
- Non ha un responsabile assegnato nella gerarchia

### Funzionalità Orfani

#### A) Checkbox "Solo Orfani"
```python
# Posizione: Toolbar principale, colonna 4
show_orphans_only = st.checkbox(
    "👤 Solo Orfani",
    value=False,
    key="org_hr_orphans",
    help="Mostra solo nodi senza responsabile (orfani)"
)
```

**Comportamento**:
- ✅ Filtra la vista per mostrare SOLO nodi orfani
- ✅ Nasconde tutti gli altri nodi della gerarchia
- ✅ Utile per identificare rapidamente problemi di assegnazione

#### B) Alert Orfani
Se vengono rilevati orfani, mostra automaticamente:

```
⚠️ **7 nodi orfani** rilevati (senza responsabile diretto)
```

#### C) Lista Dettagliata Orfani
Expander cliccabile con tabella dettagli:

| Nome | CF | Area | Sede | Dipendenti |
|------|-------|------|------|------------|
| Rossi Mario | RSSMRA80... | IT | Milano | 5 |
| Bianchi Giuseppe | BNCGPP75... | HR | Roma | 0 |

**Limiti**: Mostra primi 20 orfani per performance

---

## 2. Tooltip Dettagliati

### Prima (tooltip basico)
```
Nome Struttura
123 dipendenti
```

### Dopo (tooltip avanzato)
```
┌───────────────────────────────┐
│ Rossi Mario                   │
├───────────────────────────────┤
│ CF: RSSMRA80A01H501U          │
│ Qualifica: Senior Manager     │
│ Area: Information Technology  │
│ Sede: Milano                  │
│ Società: Il Sole 24 ORE       │
│ Dipendenti: 12                │
│ Email: m.rossi@ilsole24ore.com│
│ Contratto: Indeterminato      │
└───────────────────────────────┘
```

### Implementazione

#### Arricchimento Dati Nodi
```python
# Per ogni nodo, query dettagli completi dipendente
emp_details = orgchart_service._query("""
    SELECT
        titolare, tx_cod_fiscale, area, sede, qualifica,
        societa, email, data_assunzione, contratto
    FROM employees
    WHERE tx_cod_fiscale = ?
""", (node['id'],))

# Aggiungi ai dati nodo
node['full_name'] = emp['titolare']
node['cf'] = emp['tx_cod_fiscale']
node['area'] = emp['area'] or 'N/D'
node['sede'] = emp['sede'] or 'N/D'
# ... etc
```

#### Funzione JavaScript Tooltip
```javascript
function showEnhancedTooltip(event, d) {
  const node = d.data;
  const tooltip = document.getElementById('tooltip');

  // Build detailed tooltip content
  let tooltipHTML = `
    <div style="padding:4px">
      <div style="font-weight:700;margin-bottom:6px">
        ${node.full_name || node.name}
      </div>
      <div style="font-size:9px;color:#94a3b8;line-height:1.5">
        ${node.cf ? '<div><b>CF:</b> ' + node.cf + '</div>' : ''}
        ${node.qualifica !== 'N/D' ? '<div><b>Qualifica:</b> ' + node.qualifica + '</div>' : ''}
        ${node.area !== 'N/D' ? '<div><b>Area:</b> ' + node.area + '</div>' : ''}
        // ... più campi
      </div>
    </div>
  `;

  tooltip.innerHTML = tooltipHTML;
  tooltip.style.display = 'block';
}
```

#### Event Handlers Nodi
```javascript
// Albero Orizzontale
const ne = nd.enter().append('g').attr('class','node-g')
  .on('click', (ev,d)=>{ev.stopPropagation();toggle(d);})
  .on('dblclick',(ev,d)=>{ev.stopPropagation();openModal(d);})
  .on('mouseover', (ev,d)=>showEnhancedTooltip(ev,d))  // ← NUOVO
  .on('mouseout', hideTooltip);                        // ← NUOVO

// Stesso per Albero Verticale
```

### Campi Visualizzati nel Tooltip
1. **Nome completo** (titolare)
2. **Codice Fiscale**
3. **Qualifica** (ruolo aziendale)
4. **Area** (es. IT, HR, Finance)
5. **Sede** (città)
6. **Società** (gruppo multi-società)
7. **Numero dipendenti** (riporti)
8. **Email** aziendale
9. **Tipo contratto** (indeterminato, determinato, etc.)

**Nota**: Campi con valore 'N/D' vengono nascosti automaticamente

---

## 3. Filtri Avanzati

### Panel Filtri (Expander)

```python
with st.expander("🔧 Filtri Avanzati", expanded=False):
    fcol1, fcol2, fcol3 = st.columns(3)

    with fcol1:
        min_employees = st.number_input("Min. dipendenti", ...)

    with fcol2:
        has_responsible_filter = st.selectbox(
            "Ha responsabile",
            options=["Tutti", "Sì", "No"]
        )

    with fcol3:
        node_depth_filter = st.selectbox(
            "Livello gerarchico",
            options=["Tutti"] + [f"Livello {i}" for i in range(1, 6)]
        )
```

### Filtri Disponibili

#### A) Min. Dipendenti
**Tipo**: Number Input
**Range**: 0+
**Comportamento**:
- Mostra solo nodi con almeno N dipendenti
- Utile per identificare manager e team leader
- Nasconde individual contributor (IC)

**Esempio**: `min_employees = 5` → mostra solo manager con 5+ riporti

#### B) Ha Responsabile
**Tipo**: Select Box
**Opzioni**:
- `Tutti` - Mostra tutti i nodi
- `Sì` - Solo nodi con responsabile assegnato
- `No` - Solo orfani (equivalente checkbox "Solo Orfani")

**Implementazione**:
```python
if has_responsible_filter == "Sì":
    filtered_nodes = [n for n in nodes if n.get('has_responsible')]
elif has_responsible_filter == "No":
    filtered_nodes = [n for n in nodes if not n.get('has_responsible')]
```

#### C) Livello Gerarchico
**Tipo**: Select Box
**Opzioni**:
- `Tutti` - Mostra tutti i livelli
- `Livello 1` - Solo top management (diretti della ROOT)
- `Livello 2` - Secondo livello
- ... fino a `Livello 5`

**Comportamento**:
- Filtra per profondità (depth) nella gerarchia
- ROOT = profondità 0
- Livello 1 = profondità 1 (es. CEO, direttori generali)
- Livello 2 = profondità 2 (es. responsabili dipartimento)

**Use Case**: Visualizzare solo management di alto livello

### Logica Filtri Combinati

I filtri si **combinano** con operatore AND:

```python
filtered_nodes = nodes

# Filtro 1: Solo orfani?
if show_orphans_only:
    filtered_nodes = orphans

# Filtro 2: Ha responsabile?
if has_responsible_filter != "Tutti":
    if has_responsible_filter == "Sì":
        filtered_nodes = [n for n in filtered_nodes if n.get('has_responsible')]
    else:
        filtered_nodes = [n for n in filtered_nodes if not n.get('has_responsible')]

# Filtro 3: Min dipendenti?
if min_employees > 0:
    filtered_nodes = [n for n in filtered_nodes if n.get('employee_count', 0) >= min_employees]

# Filtro 4: Livello gerarchico?
# (passato a JavaScript via filters_config)
```

**Esempio Combinazione**:
- `min_employees = 3` AND `has_responsible = "Sì"` AND `livello = 2`
- Risultato: Solo manager di 2° livello con 3+ dipendenti che hanno un responsabile

---

## File Modificati

### `/ui/orgchart_hr_view.py`

**Modifiche Python (Streamlit)**:
- Linee 28-64: Aggiunto filtri avanzati (5 colonne + expander)
- Linee 104-136: Arricchimento nodi con dati completi dipendente
- Linee 137-155: Logica filtri e conteggio orfani
- Linee 167-187: Alert e lista orfani

**Modifiche JavaScript (D3.js)**:
- Linee 410-438: Funzione `showEnhancedTooltip()` e `hideTooltip()`
- Linee 674-677: Event handlers tooltip albero orizzontale
- Linee 766-769: Event handlers tooltip albero verticale
- Linea 421: Aggiunto `const FILTERS = {filters_json};`

**Totale modifiche**: ~120 righe aggiunte

---

## Uso delle Nuove Funzionalità

### Scenario 1: Identificare Orfani

1. **Apri organigramma HR**
2. **Guarda alert** in cima se ci sono orfani
3. **Click expander "Dettagli Orfani"** per vedere lista
4. **Oppure check "Solo Orfani"** per visualizzare solo loro nell'organigramma

### Scenario 2: Analizzare Manager

1. **Apri "Filtri Avanzati"**
2. **Imposta "Min. dipendenti" = 3**
3. **Seleziona "Livello gerarchico" = Livello 2**
4. Visualizza solo manager di secondo livello con 3+ riporti

### Scenario 3: Ispezionare Dettagli Dipendente

1. **Passa mouse** sopra un nodo nell'organigramma
2. **Leggi tooltip** con dati completi
3. **Identifica area, sede, qualifica** senza aprire scheda separata

---

## Benefits

### UX Improvements
✅ **Identificazione rapida problemi**: Orfani evidenziati immediatamente
✅ **Informazioni contestuali**: Tooltip ricchi senza click aggiuntivi
✅ **Analisi flessibile**: Filtri multipli combinabili
✅ **Drill-down guidato**: Filtri aiutano a focalizzare l'attenzione

### Business Value
✅ **Quality assurance**: Rileva dati gerarchici mancanti
✅ **Org analysis**: Identifica pattern organizzativi (manager con troppi/pochi riporti)
✅ **Data cleanup**: Lista orfani guida correzione dati

---

## Prossimi Passi

### Estensione ad Altri Organigrammi

Le stesse funzionalità dovrebbero essere replicate in:
- [ ] `/ui/orgchart_org_view.py` - Organigramma ORG
- [ ] `/ui/orgchart_tns_structures_view.py` - Organigramma TNS

### Funzionalità Future

**Export orfani**:
- Bottone "Esporta Orfani Excel"
- Genera file con lista completa per correzione

**Filtri aggiuntivi**:
- Filtra per società (multi-tenancy)
- Filtra per tipo contratto
- Filtra per sede

**Tooltip configurabili**:
- Utente sceglie quali campi visualizzare
- Salva preferenze in session state

**Orphans auto-fix**:
- Suggerimenti automatici per assegnare responsabili
- Basati su area/sede/qualifica similarità

---

## Testing Checklist

- [x] Checkbox "Solo Orfani" filtra correttamente
- [x] Alert orfani appare quando presenti
- [x] Lista orfani mostra dati corretti
- [x] Tooltip appare al mouse over
- [x] Tooltip contiene tutti i campi previsti
- [x] Tooltip nasconde campi N/D
- [x] Filtro "Min dipendenti" funziona
- [x] Filtro "Ha responsabile" funziona
- [x] Filtri si combinano correttamente (AND logic)
- [x] Performance OK con 1000+ nodi

---

**Implementato**: 2026-02-22
**File modificati**: 1 (`orgchart_hr_view.py`)
**Righe aggiunte**: ~120
**Funzionalità**: 3 (Orfani, Tooltip, Filtri)
