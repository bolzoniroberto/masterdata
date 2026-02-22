# Database Schema Reference - HR Management Platform

## Tabelle Principali con Dati

### 📊 EMPLOYEES (772 record)
**Dipendenti - Gerarchia HR**

Colonne chiave:
- `employee_id` - ID numerico (PK autoincrement)
- `tx_cod_fiscale` - Codice fiscale (UNIQUE)
- `codice` - Identificativo univoco persona/posizione
- `titolare` - Nome completo dipendente
- `reports_to_codice` - **A chi riporta** (gerarchia HR) ⭐
- `company_id` - FK to companies
- `cognome`, `nome` - Anagrafica
- `area`, `sottoarea` - Organizzazione
- `sede`, `qualifica`, `livello` - Dettagli lavoro
- `ral`, `data_assunzione`, `data_cessazione` - Contratto

**Esempio gerarchia HR:**
```
Employee: "Silvestri F." (codice: Calabi C.Amministratore DelegatoCLBCLD48D20L219M)
  reports_to_codice: "CDA_ID"

Employee: "Monteverdi S." (codice: Brullo M.Internal AuditingBRLMSM70S24F205Q)
  reports_to_codice: "Calabi C.Amministratore DelegatoCLBCLD48D20L219M"
```

### 🏢 ORG_UNITS (901 record)
**Unità Organizzative - Gerarchia Posizioni**

Colonne chiave:
- `org_unit_id` - ID numerico (PK autoincrement)
- `codice` - Codice posizione organizzativa (UNIQUE)
- `descrizione` - Nome della posizione
- `company_id` - FK to companies
- `parent_org_unit_id` - **Parent posizione** (INTEGER FK) ⭐
- `responsible_employee_id` - Responsabile della posizione (FK to employees)
- `cdccosto`, `cdc_amm` - Centro di costo
- `livello` - Livello gerarchico (1, 2, 3...)
- `unita_org_livello1`, `unita_org_livello2` - Nomi gerarchici

**Esempio gerarchia ORG:**
```
Org Unit: "Corporate" (codice: Calabi C.Amministratore DelegatoCLBCLD48D20L219M)
  org_unit_id: 1
  parent_org_unit_id: NULL (è root)
  livello: 2

Org Unit: "Marketing" (codice: FRRNDR65L28D969P_ID)
  org_unit_id: 2
  parent_org_unit_id: NULL (è root)
  livello: 1
```

### 🏢 COMPANIES (12 record)
Società/Aziende

- `company_id` - PK
- `company_code` - Codice società
- `company_name` - Nome società

---

## Tabelle Vuote (Nuovo Schema)

### ⚠️ PERSONALE (0 record)
**Vecchio schema TNS - VUOTO**

### ⚠️ STRUTTURE (0 record)
**Vecchio schema TNS - VUOTO**

### HIERARCHY_ASSIGNMENTS (0 record)
Assegnazioni gerarchie multiple (HR, TNS, SGSL, GDPR, IT)

### ROLE_ASSIGNMENTS (0 record)
Assegnazione ruoli ai dipendenti

### ROLE_DEFINITIONS (0 record)
Definizione ruoli (Approvatore, Viaggiatore, etc.)

### SALARY_RECORDS (0 record)
Record retribuzioni mensili

---

## Mappatura Colonne DB_ORG → Database

### Colonne Gerarchie Organigrammi

| Colonna Excel DB_ORG | Lettera | Campo Database | Tabella | Note |
|----------------------|---------|----------------|---------|------|
| **ID** | AB | `codice` | employees/org_units | Identificativo univoco |
| **ReportsTo** | AC | `reports_to_codice` | employees | Parent HR (persone) |
| **ReportsTo** | AC | `parent_org_unit_id` | org_units | Parent ORG (posizioni) |
| **TxCodFiscale** | AF | `tx_cod_fiscale` | employees | Codice fiscale |
| **Responsabile Diretto** | BF? | `reports_to_codice` | employees | A chi riporta |

---

## Come Costruire gli Organigrammi

### 1️⃣ ORGANIGRAMMA HR (Persone → Responsabile Diretto)

**Query base:**
```sql
SELECT
    codice AS id,
    tx_cod_fiscale,
    titolare AS name,
    reports_to_codice AS parentId
FROM employees
WHERE tx_cod_fiscale IS NOT NULL
ORDER BY titolare
```

**Gerarchia:** `employees.codice` → `employees.reports_to_codice`

### 2️⃣ ORGANIGRAMMA ORG (Posizioni Organizzative)

**Query base (con JOIN per risolvere parent):**
```sql
SELECT
    o.codice AS id,
    o.descrizione AS name,
    o.livello,
    parent.codice AS parentId
FROM org_units o
LEFT JOIN org_units parent ON o.parent_org_unit_id = parent.org_unit_id
WHERE o.codice IS NOT NULL
ORDER BY o.descrizione
```

**Gerarchia:** `org_units.codice` → parent via `parent_org_unit_id` (JOIN)

### 3️⃣ ORGANIGRAMMA TNS (Persone con ruoli TNS)

Stesso di Organigramma HR ma filtrato per ruoli TNS (da definire quali campi usare per il filtro)

---

## Note Importanti

⚠️ **Schema Duale:**
- **Vecchio schema** (personale/strutture) = VUOTO (0 record)
- **Nuovo schema** (employees/org_units) = POPOLATO (772+901 record)

⚠️ **Parent in org_units:**
- `parent_org_unit_id` è INTEGER (FK a org_unit_id)
- Serve JOIN per ottenere il `codice` del parent
- Non è direttamente un campo testuale come in employees

⚠️ **Campi `codice`:**
- In `employees`: valori strani tipo "Calabi C.Amministratore DelegatoCLBCLD48D20L219M"
- In `org_units`: stessi valori strani
- Sembra che sia un mix di info (nome + ruolo + CF)

---

## Prossimi Step per Organigrammi

1. ✅ Decidere quali campi usare come ID nei nodi (codice? tx_cod_fiscale?)
2. ✅ Confermare che BF = reports_to_codice (colonna AC)
3. ✅ Implementare query con JOIN per org_units parent
4. ✅ Definire filtri per organigramma TNS (quali ruoli?)
