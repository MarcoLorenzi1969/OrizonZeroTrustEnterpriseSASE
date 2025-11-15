# 🔍 Sistema di Debug Completo - Orizon Zero Trust Connect

## Per: Marco @ Syneto/Orizon

Questo sistema di debug completo ti permette di catturare, analizzare ed esportare tutti i log e le informazioni di debug sia dal frontend che dal backend.

---

## 🎯 Frontend Debug System

### 1. **Debug Panel Visuale**

Il Debug Panel è un'interfaccia visuale completa per monitorare tutti i log del frontend in tempo reale.

#### Apertura/Chiusura
- **Keyboard Shortcut**: Premi `Ctrl + Shift + D` per aprire/chiudere
- **Click**: Clicca sul bottone "Debug" in basso a destra

#### Funzionalità
- ✅ **Auto-Refresh**: Aggiorna automaticamente i log ogni 2 secondi
- 📊 **Filtri**: All / Errors / Warnings / Info
- 💾 **Export**: Salva tutti i log in un file JSON
- 📋 **Copy**: Copia gli ultimi 50 log negli appunti
- 🗑️ **Clear**: Cancella tutti i log
- 📈 **System Info**: Mostra info di sistema, memoria, token status

#### Informazioni Visualizzate
```
- Platform & Screen Resolution
- Memory Usage (used/total)
- JWT Token Status (present/missing + length)
- Connection Status
```

### 2. **Categorie di Log**

Il sistema traccia automaticamente:

| Categoria | Descrizione | Esempio |
|-----------|-------------|---------|
| **API Request** | Tutte le chiamate API | Method, URL, Headers, Data |
| **API Response** | Risposte API | Status, Data, Headers |
| **API Error** | Errori API | Status, Message, Stack trace |
| **App Init** | Inizializzazione app | Token check, User load |
| **Login** | Processo di login | Form submit, Success, Error |
| **Redux Action** | Azioni Redux | Type, Payload, State changes |
| **Console Error** | Errori console | Captured errors |
| **Unhandled Error** | Errori non gestiti | Global error handler |

### 3. **Livelli di Log**

- 🐛 **DEBUG**: Informazioni dettagliate per debug
- ℹ️ **INFO**: Informazioni generali
- ⚠️ **WARN**: Avvisi
- ❌ **ERROR**: Errori
- ✅ **SUCCESS**: Operazioni completate con successo

### 4. **Export dei Log**

#### File JSON Export
Click su "Download" per esportare tutti i log in formato JSON:

```json
{
  "exportTime": "2025-11-07T10:50:00.000Z",
  "systemInfo": {
    "platform": "MacIntel",
    "screenResolution": "1920x1080",
    "memory": { "used": "45MB", "total": "512MB" },
    "localStorage": {
      "hasToken": true,
      "tokenLength": 198
    }
  },
  "logs": [...],
  "totalLogs": 500
}
```

#### Clipboard Copy
Click su "Copy" per copiare gli ultimi 50 log negli appunti (per inviarmi rapidamente).

---

## 🖥️ Backend Debug Endpoints

### 1. **Health Check**
```bash
GET http://46.101.189.126/api/v1/health
```
Response:
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### 2. **Debug Test**
```bash
GET http://46.101.189.126/api/v1/debug/test
```
Response:
```json
{
  "status": "ok",
  "message": "Backend is working",
  "timestamp": "2025-11-07T10:50:00.000000"
}
```

### 3. **System Info** (NEW!)
```bash
GET http://46.101.189.126/api/v1/debug/info
```
Response:
```json
{
  "status": "ok",
  "timestamp": "2025-11-07T10:50:00.000000",
  "system": {
    "platform": "Linux",
    "python_version": "3.10.12",
    "cpu_count": 2,
    "memory_percent": 45.2,
    "disk_percent": 38.1
  },
  "database": {
    "status": "connected",
    "users_count": 3
  }
}
```

### 4. **Request Headers** (NEW!)
```bash
GET http://46.101.189.126/api/v1/debug/headers
```
Response: Tutti gli headers della richiesta

### 5. **Token Debug** (NEW!)
```bash
POST http://46.101.189.126/api/v1/debug/token
Authorization: Bearer <your-token>
```
Response:
```json
{
  "token_length": 198,
  "payload": {
    "sub": "admin@nexus.local",
    "role": "superuser",
    "exp": 1765103799
  },
  "valid": true
}
```

---

## 🔍 Come Eseguire Test e Fornire Debug Info

### Scenario 1: Problema di Login

1. **Apri Debug Panel**: Premi `Ctrl + Shift + D`
2. **Filtra Errors**: Click su "Errors"
3. **Tenta Login**: Prova a fare login con le credenziali
4. **Osserva Logs**: Guarda i log in tempo reale
5. **Export**: Click su "Copy" per copiare i log
6. **Invio**: Incolla i log e descrivimi il problema

### Scenario 2: Problema dopo Login (Reload Loop, ecc.)

1. **Apri Debug Panel**: `Ctrl + Shift + D`
2. **Clear Logs**: Click su "Clear" per partire pulito
3. **Enable Auto-Refresh**: Assicurati che auto-refresh sia ON (verde)
4. **Riproduci Problema**: Esegui l'azione che causa il problema
5. **Export**: Click su "Download" per scaricare tutti i log
6. **Invio**: Inviami il file JSON

### Scenario 3: Errore API Specifico

1. **Apri Browser Console**: F12 → Console tab
2. **Apri Debug Panel**: `Ctrl + Shift + D`
3. **Filtra API Errors**: Cerca log con categoria "API Error"
4. **Copia Dettagli**:
   - URL della chiamata
   - Status code
   - Response body
   - Stack trace
5. **Test Backend**: Testa l'endpoint direttamente:
   ```bash
   curl http://46.101.189.126/api/v1/debug/headers \
     -H "Authorization: Bearer <token>"
   ```

### Scenario 4: Performance Issue

1. **Apri Debug Panel**
2. **Osserva**:
   - Numero totale di log (se cresce rapidamente = problema)
   - Memory usage (System Info in alto)
   - API requests ripetute
3. **Export**: Scarica i log per analisi

---

## 📋 Checklist per Segnalazione Bug

Quando mi segnali un problema, includi:

- [ ] **Descrizione**: Cosa stavi facendo quando è successo?
- [ ] **Screenshot**: Debug Panel aperto con i log visibili
- [ ] **Export Logs**: File JSON o log copiati negli appunti
- [ ] **System Info**: Visible nel Debug Panel (Platform, Memory, Token)
- [ ] **Browser Console**: Screenshot della console (F12)
- [ ] **Steps to Reproduce**: Come riprodurre il problema
- [ ] **Backend Logs** (opzionale): Se ho accesso SSH

---

## 🚀 Quick Commands per Debug

### Frontend
```bash
# Apri Debug Panel
Ctrl + Shift + D

# Export logs
Click "Download" nel Debug Panel

# Copy last 50 logs
Click "Copy" nel Debug Panel

# Clear all logs
Click "Trash" nel Debug Panel
```

### Backend
```bash
# Check health
curl http://46.101.189.126/api/v1/health

# Get system info
curl http://46.101.189.126/api/v1/debug/info

# Test token
curl -X POST http://46.101.189.126/api/v1/debug/token \
  -H "Authorization: Bearer YOUR_TOKEN"

# View live logs (SSH required)
ssh orizonai@46.101.189.126
sudo journalctl -u orizon-backend -f
```

---

## 🎓 Tips

1. **Auto-Refresh**: Tienilo ON per vedere i problemi in tempo reale
2. **Clear Logs**: Pulisci prima di riprodurre un problema per log più puliti
3. **Filter Errors**: Inizia sempre dai filtri "Errors" e "Warnings"
4. **System Info**: Controlla che "Token: Present" sia verde
5. **Export Often**: Esporta i log prima che si riempiano troppo

---

## 📞 Contatti

Se trovi problemi o hai domande sul sistema di debug:
- Inviami i log esportati
- Screenshot del Debug Panel
- Descrizione dettagliata del problema

**Il sistema di debug è ora completamente operativo! 🎉**
