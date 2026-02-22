# Piano Implementazione Organigrammi - CHIARO E DEFINITIVO

## 🎯 I TRE ORGANIGRAMMI

### 1️⃣ ORGANIGRAMMA ORG (Posizioni Organizzative)
**Cosa mostra:** Gerarchia delle posizioni/unità organizzative

**Excel → Database:**
- **Nodo ID**: Colonna **AB (ID)** → `org_units.codice`
- **Parent**: Colonna **AC (ReportsTo)** → `org_units.parent_org_unit_id`
- **Display**: Colonna "Unità Organizzativa" → `org_units.descrizione`

**Query costruzione albero:**
```sql
SELECT
    o.codice AS id,
    o.descrizione AS name,
    parent.codice AS parentId
FROM org_units o
LEFT JOIN org_units parent ON o.parent_org_unit_id = parent.org_unit_id
```

---

### 2️⃣ ORGANIGRAMMA HR (Persone → Responsabile Diretto)
**Cosa mostra:** Gerarchia persone basata su chi riporta a chi

**Excel → Database:**
- **Nodo ID**: Colonna **AF (TxCodFiscale)** → `employees.tx_cod_fiscale`
- **Parent**: Colonna **CZ (CF Responsabile Diretto)** → `employees.reports_to_cf` ⚠️ NUOVO CAMPO
- **Display**: Colonna "Titolare" → `employees.titolare`

**Query costruzione albero:**
```sql
SELECT
    tx_cod_fiscale AS id,
    titolare AS name,
    reports_to_cf AS parentId
FROM employees
WHERE tx_cod_fiscale IS NOT NULL
```

---

### 3️⃣ ORGANIGRAMMA TNS (Gerarchia TNS)
**Cosa mostra:** Gerarchia basata su codici TNS

**Excel → Database:**
- **Nodo ID**: Colonna **CB (Codice TNS)** → `employees.cod_tns` ⚠️ NUOVO CAMPO
- **Parent**: Colonna **CC (Padre TNS)** → `employees.padre_tns` ⚠️ NUOVO CAMPO
- **Display**: Colonna "Titolare" → `employees.titolare`

**Query costruzione albero:**
```sql
SELECT
    cod_tns AS id,
    titolare AS name,
    padre_tns AS parentId
FROM employees
WHERE cod_tns IS NOT NULL
```

---

## 🔧 MODIFICHE NECESSARIE

### STEP 1: Aggiungere colonne alla tabella employees

```sql
-- Migration da creare
ALTER TABLE employees ADD COLUMN reports_to_cf TEXT;
ALTER TABLE employees ADD COLUMN cod_tns TEXT;
ALTER TABLE employees ADD COLUMN padre_tns TEXT;
```

### STEP 2: Aggiornare mapping colonne (db_org_import_service.py)

```python
def _init_column_mappings(self):
    return {
        # ... colonne esistenti ...

        # NUOVE COLONNE PER GERARCHIE
        'CF Responsabile Diretto': 'reports_to_cf',  # CZ - per organigramma HR
        'Codice TNS': 'cod_tns',                      # CB - per organigramma TNS
        'Padre TNS': 'padre_tns',                     # CC - per organigramma TNS
    }
```

### STEP 3: Modificare _import_employees()

```python
# Estrarre nuovi campi
reports_to_cf = str(row.get('CF Responsabile Diretto', '')).strip() if pd.notna(row.get('CF Responsabile Diretto')) else None
cod_tns = str(row.get('Codice TNS', '')).strip() if pd.notna(row.get('Codice TNS')) else None
padre_tns = str(row.get('Padre TNS', '')).strip() if pd.notna(row.get('Padre TNS')) else None

# Aggiungere all'INSERT
cursor.execute("""
    INSERT INTO employees (
        ..., reports_to_cf, cod_tns, padre_tns, ...
    ) VALUES (
        ..., ?, ?, ?, ...
    )
""", (..., reports_to_cf, cod_tns, padre_tns, ...))
```

### STEP 4: Modificare _import_org_units() per popolare parent

```python
def _import_org_units(self, cursor, df, companies_map):
    org_units_map = {}

    # FIRST PASS: Inserisci tutte le org_units senza parent
    for _, row in unique_units.iterrows():
        codice = str(row.get('ID')).strip()
        # ... altri campi ...

        cursor.execute("""
            INSERT INTO org_units (codice, descrizione, company_id, ...)
            VALUES (?, ?, ?, ...)
        """, (codice, descrizione, company_id, ...))

        org_units_map[codice] = cursor.lastrowid

    # SECOND PASS: Aggiorna i parent usando ReportsTo (AC)
    for _, row in unique_units.iterrows():
        codice = str(row.get('ID')).strip()
        parent_codice = str(row.get('ReportsTo', '')).strip() if pd.notna(row.get('ReportsTo')) else None

        if parent_codice and parent_codice in org_units_map:
            parent_id = org_units_map[parent_codice]

            cursor.execute("""
                UPDATE org_units
                SET parent_org_unit_id = ?
                WHERE codice = ?
            """, (parent_id, codice))
```

### STEP 5: Aggiornare orgchart_data_service.py

Modificare i metodi per usare i nuovi campi:

```python
# get_hr_hierarchy_tree() - Organigramma HR
def get_hr_hierarchy_tree(self):
    employees = self._query("""
        SELECT
            tx_cod_fiscale AS id,
            titolare AS name,
            reports_to_cf AS parentId,
            cognome, nome, qualifica, area
        FROM employees
        WHERE tx_cod_fiscale IS NOT NULL
        ORDER BY titolare
    """)

    # Costruisci nodi...

# get_tns_hierarchy_tree() - Organigramma TNS
def get_tns_hierarchy_tree(self):
    employees = self._query("""
        SELECT
            cod_tns AS id,
            titolare AS name,
            padre_tns AS parentId,
            tx_cod_fiscale, cognome, nome
        FROM employees
        WHERE cod_tns IS NOT NULL
        ORDER BY titolare
    """)

    # Costruisci nodi...

# get_org_hierarchy_tree() - Organigramma ORG (già corretto)
# Usa già org_units con parent_org_unit_id
```

---

## 📋 CHECKLIST IMPLEMENTAZIONE

### Database:
- [ ] Creare migration per aggiungere colonne: `reports_to_cf`, `cod_tns`, `padre_tns`
- [ ] Eseguire migration su database esistente

### Import Service:
- [ ] Aggiornare `_init_column_mappings()` con nuove colonne CZ, CB, CC
- [ ] Modificare `_import_employees()` per estrarre e salvare nuovi campi
- [ ] Modificare `_import_org_units()` con SECOND PASS per popolare parent_org_unit_id

### OrgChart Service:
- [ ] Aggiornare `get_hr_hierarchy_tree()` per usare `reports_to_cf`
- [ ] Aggiornare `get_tns_hierarchy_tree()` per usare `cod_tns` e `padre_tns`
- [ ] Verificare `get_org_hierarchy_tree()` usa correttamente `parent_org_unit_id`

### UI Views:
- [ ] Testare `orgchart_hr_view.py` con nuova gerarchia
- [ ] Testare `orgchart_tns_structures_view.py` con nuova gerarchia TNS
- [ ] Testare `orgchart_org_view.py` con parent popolato

### Testing:
- [ ] Re-importare file Excel con nuove colonne
- [ ] Verificare dati popolati correttamente
- [ ] Testare rendering dei 3 organigrammi
- [ ] Verificare nodi parent collegati correttamente

---

## 🚨 CAMPO OBSOLETO DA RIMUOVERE

**`employees.reports_to_codice`** - Attualmente popolato con colonna AC (ReportsTo)

Questo campo è SBAGLIATO perché:
- AC (ReportsTo) è per le POSIZIONI (org_units), non per le PERSONE
- Per le persone serve CZ (CF Responsabile Diretto)

**Azione:** Può essere rimosso o lasciato vuoto (deprecato)

---

## ✅ RISULTATO FINALE

Dopo l'implementazione, avrai:

1. **Organigramma ORG** funzionante con gerarchia posizioni (AB → AC)
2. **Organigramma HR** funzionante con gerarchia persone (AF → CZ)
3. **Organigramma TNS** funzionante con gerarchia TNS (CB → CC)

Tutti e 3 gli organigrammi saranno costruiti correttamente dai dati importati dall'Excel DB_ORG!
