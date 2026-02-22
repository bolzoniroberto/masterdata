# Changelog - 2026-02-03

## 🎯 Modifiche Principali

### 1. Chiarimento Scopo Progetto

**Da**: Generico "HR Management Platform"
**A**: "Travel & Expense Approval Management" - Focus su gestione approvazioni trasferte/note spese

**File modificati**:
- `CLAUDE.md` - Documentazione allineata allo scopo reale
- `config.py` - Titolo e icona aggiornati (✈️)
- `app.py` - UI e messaggi benvenuto focalizzati su ruoli approvazione

### 2. Fix Validazione CF Duplicati

**Problema**: Codici fiscali duplicati erano trattati come errori bloccanti
**Soluzione**: Convertiti in WARNING (non bloccanti) - possono essere legittimi in alcuni casi

**File modificati**:
- `ui/dashboard.py` - Cambio da `'tipo': 'error'` a `'tipo': 'warning'`
- `CLAUDE.md` - Documentata la nuova policy

**Comportamento**:
- ✅ I CF duplicati vengono ancora **segnalati** nella dashboard
- ✅ Ma **NON bloccano** salvataggio, export o merge DB_TNS
- ✅ L'utente può decidere se sono legittimi o errori

### 3. Aggiornamento Streamlit

**Problema**: `TypeError: dataframe() got an unexpected keyword argument 'on_select'`
**Causa**: Streamlit 1.31.0 non supporta selezione interattiva tabelle
**Soluzione**: Aggiornamento a Streamlit 1.50.0

**File modificati**:
- `requirements.txt` - `streamlit==1.31.0` → `streamlit>=1.35.0`

**Funzionalità abilitate**:
- ✅ Pattern Master-Detail interattivo in Gestione Strutture
- ✅ Pattern Master-Detail interattivo in Gestione Personale
- ✅ Click diretto su riga per vedere dettagli (invece di selectbox)

## 📋 Campi Ruoli Approvazione Evidenziati

I seguenti campi sono ora evidenziati nella documentazione come chiave per il workflow trasferte:

**Ruoli Primari**:
- `Viaggiatore` - Può inserire richieste
- `Approvatore` - Approva richieste
- `Controllore` - Controlla/audita spese
- `Cassiere` - Gestisce pagamenti
- `Segretario` - Supporto amministrativo
- `Visualizzatori` - Accesso read-only
- `Amministrazione` - Ruolo amministrativo

**Ruoli Assistenti** (deleghe):
- `SegreteriA Red. Ass.ta`
- `SegretariO Ass.to`
- `Controllore Ass.to`

**Altri**:
- `RuoliAFC`, `RuoliHR`, `AltriRuoli`
- `Sede_TNS`, `GruppoSind`

## 🚀 Come Procedere

1. **Riavvia Streamlit**:
   ```bash
   streamlit run app.py
   ```

2. **Verifica funzionalità**:
   - Carica un file Excel TNS
   - Vai in "🏗️ Gestione Strutture"
   - Clicca su una riga nella tabella di sinistra
   - I dettagli dovrebbero apparire a destra

3. **Testa CF duplicati**:
   - Se presenti, dovrebbero apparire come ⚠️ WARNING (arancione)
   - Non come 🔴 ERROR (rosso)
   - Puoi salvare/esportare anche con CF duplicati presenti

## ✅ Checklist Testing

- [ ] App si avvia senza errori
- [ ] Click su riga struttura mostra dettagli
- [ ] Click su riga personale mostra dettagli
- [ ] CF duplicati mostrati come WARNING
- [ ] Salvataggio funziona con CF duplicati presenti
- [ ] Export DB_TNS funziona correttamente
- [ ] Backup automatici vengono creati

## 📝 Note

- Streamlit 1.50.0 è molto più recente del minimo richiesto (1.35.0)
- Questo garantisce compatibilità futura con nuove feature
- Se emergono problemi di compatibilità, possiamo fare downgrade a 1.35.0

## 🔧 Emergency Fix - 2026-02-03 Pomeriggio

**Problema**: `models/personale.py` era stato convertito a SQLModel (con `sqlmodel` import non disponibile)
**Causa**: Tentativo di aggiungere database SQLite interrotto
**Soluzione**: Ripristinato file originale con Pydantic

**Importante**:
- Il progetto usa **Pydantic per validazione Excel**, non database
- SQLModel non è una dipendenza (`requirements.txt`)
- Sempre usare: `from pydantic import BaseModel, Field, field_validator`
- NEVER usare: `from sqlmodel import ...`

---

**Data**: 2026-02-03
**Versione Streamlit**: 1.31.0 → 1.50.0
**Status**: ✅ App funzionante, pronto per feature "Gestione Ruoli"
