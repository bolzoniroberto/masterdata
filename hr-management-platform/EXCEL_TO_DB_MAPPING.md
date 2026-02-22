# Mapping Excel DB_ORG → Database Tables

## 📋 Processo di Import in 5 Step

```
Step 1: Import COMPANIES (dalla colonna "Società")
Step 2: Import ORG_UNITS (posizioni organizzative)
Step 3: Import EMPLOYEES (dipendenti)
Step 4: Assign HIERARCHIES (gerarchie multiple)
Step 5: Assign ROLES (ruoli TNS/SGSL/GDPR)
```

---

## 1️⃣ COMPANIES Table

### Mapping
| Colonna Excel | Lettera | → | Campo Database | Tipo |
|--------------|---------|---|----------------|------|
| **Società** | ? | → | `company_name` | TEXT |
| (auto-generated) | | → | `company_code` | TEXT (uppercase) |
| (default) | | → | `company_id` | INTEGER PK |

### Logica
- Estrae valori unici dalla colonna **Società**
- Crea un record per ogni società se non esiste
- `company_code` = nome società in uppercase con underscore

### Esempio Dati Importati
```
company_id: 1
company_code: "COLLABORATORI_IL_SOLE_24_ORE_S.P.A."
company_name: "Collaboratori Il Sole 24 Ore S.p.A."
```

---

## 2️⃣ ORG_UNITS Table (Posizioni Organizzative)

### Mapping Completo
| Colonna Excel | Lettera | → | Campo Database | Tipo | Note |
|--------------|---------|---|----------------|------|------|
| **ID** | **AB** | → | `codice` | TEXT UNIQUE | ⭐ Chiave logica posizione |
| **Unità Organizzativa** | ? | → | `descrizione` | TEXT | Nome posizione |
| **Unità Organizzativa** | ? | → | `unita_org_livello1` | TEXT | Livello 1 gerarchia |
| **Unità Organizzativa 2** | ? | → | `unita_org_livello2` | TEXT | Livello 2 gerarchia |
| **CdC** | ? | → | `cdccosto` | TEXT | Centro di costo |
| **Società** | ? | → | `company_id` | INTEGER FK | FK to companies |
| (auto-calculated) | | → | `livello` | INTEGER | 1 o 2 in base a livello2 |
| (auto-generated) | | → | `org_unit_id` | INTEGER PK | ID numerico |
| (null per ora) | | → | `parent_org_unit_id` | INTEGER FK | Parent gerarchico |

### Logica
- Estrae righe uniche per combinazione di (ID, Unità Organizzativa, Unità Organizzativa 2, CdC, Società)
- Ogni **ID** univoco crea una posizione organizzativa
- `livello` = 2 se c'è "Unità Organizzativa 2", altrimenti 1
- `parent_org_unit_id` viene popolato DOPO nello Step 4

### Esempio Dati Importati
```
org_unit_id: 1
codice: "Calabi C.Amministratore DelegatoCLBCLD48D20L219M"
descrizione: "Corporate"
company_id: 1
parent_org_unit_id: NULL
cdccosto: NULL
livello: 2
unita_org_livello1: "Corporate"
unita_org_livello2: "Chief Executive Officer"
```

---

## 3️⃣ EMPLOYEES Table (Dipendenti)

### Mapping Completo
| Colonna Excel | Lettera | → | Campo Database | Tipo | Note |
|--------------|---------|---|----------------|------|------|
| **TxCodFiscale** | **AF** | → | `tx_cod_fiscale` | TEXT UNIQUE | ⭐ Chiave logica dipendente |
| **ID** | **AB** | → | `codice` | TEXT UNIQUE | Identificativo posizione |
| **Titolare** | ? | → | `titolare` | TEXT | Nome completo |
| **ReportsTo** | **AC** | → | `reports_to_codice` | TEXT | ⭐ GERARCHIA HR - Parent |
| **Società** | ? | → | `company_id` | INTEGER FK | FK to companies |
| **Cognome** | ? | → | `cognome` | TEXT | |
| **Nome** | ? | → | `nome` | TEXT | |
| **Area** | ? | → | `area` | TEXT | |
| **SottoArea** | ? | → | `sottoarea` | TEXT | |
| **Sede** | ? | → | `sede` | TEXT | |
| **Contratto** | ? | → | `contratto` | TEXT | |
| **Qualifica** | ? | → | `qualifica` | TEXT | |
| **Livello** | ? | → | `livello` | TEXT | |
| **RAL** | ? | → | `ral` | REAL | Retribuzione annua |
| **Data Assunzione** | ? | → | `data_assunzione` | DATE | |
| **Data Cessazione** | ? | → | `data_cessazione` | DATE | |
| **Data Nascita** | ? | → | `data_nascita` | DATE | |
| **Sesso** | ? | → | `sesso` | TEXT | |
| **Email** | ? | → | `email` | TEXT | |
| **Matricola** | ? | → | `matricola` | TEXT | |
| **FTE** | ? | → | `fte` | REAL | Default 1.0 |
| (auto-generated) | | → | `employee_id` | INTEGER PK | |
| (default True) | | → | `active` | BOOLEAN | |

### Logica
- Per ogni riga Excel con TxCodFiscale, ID e Titolare compilati → crea un dipendente
- Salta righe senza questi 3 campi obbligatori
- **reports_to_codice** contiene il valore della colonna **ReportsTo** (AC)

### Esempio Dati Importati
```
employee_id: 1
tx_cod_fiscale: "SLVFRC71A14F205W"
codice: "Calabi C.Amministratore DelegatoCLBCLD48D20L219M"
titolare: "Silvestri F."
company_id: 1
reports_to_codice: "CDA_ID"  ← COLONNA AC "ReportsTo"
cognome: NULL
nome: NULL
sede: "Milano"
qualifica: "Dirigente"
...
```

---

## 4️⃣ HIERARCHY_ASSIGNMENTS Table

Questo step **NON è ancora implementato** nel codice attuale.

### Mapping Previsto (da implementare)
| Colonna Excel | → | Campo Database | Note |
|--------------|---|----------------|------|
| TxCodFiscale | → | `employee_id` | FK |
| (da determinare) | → | `org_unit_id` | FK |
| (hardcoded) | → | `hierarchy_type_id` | FK (HR=1, TNS=2, etc.) |

---

## 5️⃣ ROLE_ASSIGNMENTS Table

Questo step **NON è ancora implementato** nel codice attuale.

### Mapping Previsto (da implementare)
Dalle colonne TNS (BS-CV):
- Viaggiatore
- Approvatore
- Controllore
- Cassiere
- Segretario
- etc.

---

## 🔍 COLONNE CHIAVE PER ORGANIGRAMMI

### ⭐ MAPPATURA CORRETTA GERARCHIE ⭐

| Organigramma | ID Nodo (Excel) | Parent (Excel) | ID Nodo (DB) | Parent (DB) |
|--------------|----------------|----------------|--------------|-------------|
| **ORG (Posizioni)** | AB (ID) | **AC (ReportsTo)** | `org_units.codice` | `org_units.parent_org_unit_id` |
| **HR (Persone)** | AF (TxCodFiscale) | **CZ (CF Responsabile)** | `employees.tx_cod_fiscale` | `employees.reports_to_cf` |
| **TNS (Persone)** | CB (Cod_TNS) | **CC (Padre TNS)** | `employees.cod_tns` | `employees.padre_tns` |

### Organigramma ORG (Posizioni Organizzative)
```
Excel:
  AB (ID) = Codice posizione
  AC (ReportsTo) = Codice parent posizione ⭐

Database:
  org_units.codice (da colonna AB)
  org_units.parent_org_unit_id ← risolve AC tramite lookup codice→org_unit_id
```

**Esempio costruzione albero (con JOIN):**
```sql
SELECT
    o.codice AS id,                -- Nodo corrente
    o.descrizione AS name,          -- Display nome
    parent.codice AS parentId       -- Parent codice (via JOIN)
FROM org_units o
LEFT JOIN org_units parent
    ON o.parent_org_unit_id = parent.org_unit_id
WHERE o.codice IS NOT NULL
```

**Logica import:**
```python
# Durante import, per ogni org_unit:
parent_codice = row['AC (ReportsTo)']  # Codice del parent
# Lookup parent_org_unit_id dal codice
parent_id = org_units_map.get(parent_codice)  # Mappa codice → org_unit_id
# Inserisci con parent_org_unit_id risolto
```

### Organigramma HR (Persone → Responsabile Diretto)
```
Excel:
  AF (TxCodFiscale) = Codice fiscale dipendente
  CZ (CF Responsabile Diretto) = Codice fiscale del responsabile ⭐

Database:
  employees.tx_cod_fiscale (da colonna AF)
  employees.reports_to_cf (da colonna CZ) ← NUOVO CAMPO
```

**Esempio costruzione albero:**
```sql
SELECT
    tx_cod_fiscale AS id,      -- Nodo corrente
    titolare AS name,           -- Display nome
    reports_to_cf AS parentId   -- Parent nella gerarchia (CF responsabile)
FROM employees
WHERE tx_cod_fiscale IS NOT NULL
```

⚠️ **ATTENZIONE**: Attualmente il codice import usa **AC (ReportsTo)** per `reports_to_codice`.
Questo è **SBAGLIATO** per l'organigramma HR! Deve usare **CZ**.

### Organigramma TNS (Persone con gerarchia TNS)
```
Excel:
  CB (Codice TNS) = Codice TNS del dipendente
  CC (Padre TNS) = Codice TNS del parent ⭐

Database:
  employees.cod_tns (da colonna CB) ← NUOVO CAMPO
  employees.padre_tns (da colonna CC) ← NUOVO CAMPO
```

**Esempio costruzione albero:**
```sql
SELECT
    cod_tns AS id,              -- Nodo corrente (codice TNS)
    titolare AS name,           -- Display nome
    padre_tns AS parentId       -- Parent TNS
FROM employees
WHERE cod_tns IS NOT NULL
```

---

## ✅ INFORMAZIONI CONFERMATE

### Colonne Gerarchie Excel → Database

| Organigramma | Colonna ID | Colonna Parent | Campo DB ID | Campo DB Parent |
|--------------|-----------|----------------|-------------|-----------------|
| **ORG** | AB (ID) | **AC (ReportsTo)** | `org_units.codice` | `org_units.parent_org_unit_id` |
| **HR** | AF (TxCodFiscale) | **CZ (CF Responsabile)** | `employees.tx_cod_fiscale` | `employees.reports_to_cf` |
| **TNS** | CB (Cod_TNS) | **CC (Padre TNS)** | `employees.cod_tns` | `employees.padre_tns` |

### Lettere Excel → Numero Colonna
- **AB** = colonna 28 (ID)
- **AC** = colonna 29 (ReportsTo)
- **AF** = colonna 32 (TxCodFiscale)
- **CB** = colonna 80 (Codice TNS)
- **CC** = colonna 81 (Padre TNS)
- **CZ** = colonna 104 (CF Responsabile Diretto)

---

## 🔧 MODIFICHE NECESSARIE AL CODICE IMPORT

### 1. Aggiungere nuove colonne al mapping
```python
# In db_org_import_service.py → _init_column_mappings()
'CF Responsabile Diretto': 'reports_to_cf',     # Colonna CZ
'Codice TNS': 'cod_tns',                        # Colonna CB
'Padre TNS': 'padre_tns',                       # Colonna CC
```

### 2. Aggiungere campi alla tabella employees
```sql
ALTER TABLE employees ADD COLUMN reports_to_cf TEXT;
ALTER TABLE employees ADD COLUMN cod_tns TEXT;
ALTER TABLE employees ADD COLUMN padre_tns TEXT;
```

### 3. Modificare _import_employees()
```python
# SBAGLIATO (attuale):
reports_to = str(row.get('ReportsTo', '')).strip()  # Colonna AC

# CORRETTO (nuovo):
reports_to_cf = str(row.get('CF Responsabile Diretto', '')).strip()  # Colonna CZ
cod_tns = str(row.get('Codice TNS', '')).strip()  # Colonna CB
padre_tns = str(row.get('Padre TNS', '')).strip()  # Colonna CC

# Inserimento:
INSERT INTO employees (..., reports_to_cf, cod_tns, padre_tns, ...)
VALUES (..., ?, ?, ?, ...)
```

### 4. Modificare _import_org_units() per popolare parent
```python
# Durante l'import delle org_units:
for _, row in unique_units.iterrows():
    codice = row.get('ID')  # Colonna AB
    parent_codice = row.get('ReportsTo')  # Colonna AC

    # Lookup parent_org_unit_id dal codice parent
    if parent_codice and parent_codice in org_units_map:
        parent_id = org_units_map[parent_codice]
    else:
        parent_id = None

    # Insert con parent_id risolto
    INSERT INTO org_units (..., parent_org_unit_id, ...)
    VALUES (..., ?, ...)
```

### 5. Rimuovere campo obsoleto
```python
# reports_to_codice NON serve più, è stato rimpiazzato da:
# - reports_to_cf (per HR)
# - cod_tns/padre_tns (per TNS)
# - parent_org_unit_id (per ORG - già esiste)
```

---

## 📊 RIEPILOGO TABELLE POPOLATE

Dopo import di un file DB_ORG:

✅ **companies** (12 record) - Società uniche dal file
✅ **org_units** (901 record) - Una per ogni ID univoco
✅ **employees** (772 record) - Una per ogni TxCodFiscale+Titolare
✅ **import_versions** (1 record) - Tracciamento import
❌ **personale** (0 record) - Vecchio schema, non usato
❌ **strutture** (0 record) - Vecchio schema, non usato
❌ **hierarchy_assignments** (0 record) - Step 4 non implementato
❌ **role_assignments** (0 record) - Step 5 non implementato
