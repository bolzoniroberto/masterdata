# 🚀 Guida Rapida - HR Management Platform

## ⚡ Installazione Rapida

### 1. Estrai l'archivio
```bash
tar -xzf hr-management-platform.tar.gz
cd hr-management-platform
```

### 2. Installa dipendenze
```bash
pip install -r requirements.txt
```

### 3. Verifica installazione
```bash
python test_platform.py
```

Se vedi "✅ TUTTI I TEST COMPLETATI CON SUCCESSO!" sei pronto!

### 4. Avvia l'applicazione
```bash
streamlit run app.py
```

L'applicazione si aprirà automaticamente nel browser su `http://localhost:8501`

## 📝 Primo Utilizzo

### Scenario 1: File già presente in `data/input/`
Il file di esempio `TNS_HR_Data.xls` è già incluso. Basta avviare l'app!

### Scenario 2: Caricare il tuo file
1. Avvia l'applicazione
2. Dalla sidebar, clicca "Carica file TNS"
3. Seleziona il tuo file Excel (.xls o .xlsx)
4. Il file deve contenere i fogli:
   - **TNS Personale** (dipendenti con CF)
   - **TNS Strutture** (organigramma senza CF)

## 🎯 Workflow Tipico

### 1️⃣ Carica dati
- Usa upload sidebar o posiziona file in `data/input/TNS_HR_Data.xls`

### 2️⃣ Controlla Dashboard
- Verifica statistiche
- Leggi alert anomalie (se presenti)
- Identifica record incompleti o duplicati

### 3️⃣ Modifica dati
**Gestione Strutture:**
- Modifica descrizioni e codici
- Aggiungi nuove unità organizzative
- Elimina strutture non referenziate
- Visualizza gerarchia

**Gestione Personale:**
- Modifica dati dipendenti
- Aggiungi nuovi dipendenti
- Filtra per sede/unità
- Cerca per nome/CF

### 4️⃣ Genera DB_TNS
- Vai in "Genera DB_TNS"
- Clicca "🚀 Genera DB_TNS"
- Controlla statistiche merge
- Verifica anteprima

### 5️⃣ Salva modifiche
**Opzione A - Sovrascrivi originale:**
- Vai in "Salvataggio & Export"
- Tab "Salva modifiche"
- Clicca "💾 Salva modifiche"
- Backup automatico creato

**Opzione B - Esporta nuovo file:**
- Tab "Esporta"
- Scegli prefisso nome
- Clicca "📤 Esporta"
- Scarica file generato

## 🔧 Risoluzione Problemi Comuni

### Errore "File non trovato"
**Soluzione:**
```bash
# Posiziona il file qui:
cp tuo_file.xls data/input/TNS_HR_Data.xls
```

### Errore "Fogli mancanti"
**Causa:** File Excel non contiene i fogli richiesti

**Soluzione:** Verifica che il file contenga esattamente:
- Foglio "TNS Personale"
- Foglio "TNS Strutture"

### Errori validazione Pydantic
**Causa:** Campi obbligatori vuoti o CF malformato

**Soluzione:**
1. Vai in Dashboard
2. Espandi alert anomalie
3. Correggi i record segnalati
4. Rigenera DB_TNS

### "DB_TNS non aggiornato"
**Causa:** Modifiche a Personale/Strutture non ancora propagate

**Soluzione:**
1. Vai in "Genera DB_TNS"
2. Clicca "🚀 Genera DB_TNS"
3. Il merge verrà ricalcolato

## 📊 Cosa Controlla la Piattaforma

### ✅ Validazioni Automatiche

**Personale:**
- CF 16 caratteri alfanumerici
- Titolare, Codice, UO obbligatori
- CF univoci
- Padri esistenti

**Strutture:**
- Codice e DESCRIZIONE obbligatori
- CF sempre vuoto
- Codici univoci
- Nessun ciclo gerarchico
- Padri esistenti

**DB_TNS:**
- Conteggio corretto (Strutture + Personale)
- Integrità referenziale
- Separazione corretta

### 🚨 Alert Dashboard

1. **Record incompleti**: Campi obbligatori mancanti
2. **Codici duplicati**: CF o Codici non univoci
3. **Strutture orfane**: Unità senza dipendenti assegnati
4. **Riferimenti invalidi**: Padri inesistenti

## 📁 Dove Sono i File?

```
hr-management-platform/
├── data/
│   ├── input/          ← File Excel sorgente
│   ├── output/         ← Export con timestamp
│   └── backups/        ← Backup automatici (max 50)
```

## 💡 Tips & Best Practices

1. **Controlla sempre Dashboard prima di modificare**
   - Identifica anomalie esistenti
   - Pianifica correzioni

2. **Usa filtri per modifiche massive**
   - Filtra per sede/UO
   - Modifica gruppi omogenei

3. **Rigenera DB_TNS dopo ogni modifica**
   - Necessario per avere merge aggiornato
   - Validazione automatica inclusa

4. **Backup automatico protegge da errori**
   - Ogni salvataggio crea backup
   - Ripristino rapido da Tab "Backup"

5. **Export per condivisione**
   - Non modifica originale
   - File timestampato univoco
   - Include o esclude DB_TNS a scelta

## 🆘 Supporto

Per problemi o domande:
1. Consulta il README.md completo
2. Verifica log errori in console
3. Esegui `python test_platform.py` per diagnostica

## 🎓 Prossimi Passi

Dopo aver preso confidenza:
1. Esplora editor completo (tutte 26 colonne)
2. Usa visualizzazione gerarchia per organigramma
3. Sperimenta con ripristino backup
4. Personalizza config.py per le tue esigenze

---

**Buon lavoro! 🚀**
