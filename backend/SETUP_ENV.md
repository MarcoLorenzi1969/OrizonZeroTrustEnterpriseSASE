# 🔧 Setup Environment Variables - Guida Completa

## Quick Start ⚡

### 1. Genera le chiavi segrete

```bash
cd backend
python3 generate_secret_key.py
```

Lo script genererà due chiavi sicure random di 64 caratteri.

### 2. Crea il file .env

```bash
cp .env.example .env
```

### 3. Modifica il file .env

Apri `.env` e sostituisci i valori delle chiavi con quelle generate:

```bash
nano .env
# oppure
code .env
```

---

## 🔐 Spiegazione JWT_SECRET_KEY

### Cos'è?

`JWT_SECRET_KEY` è una **chiave segreta** usata per:
- Firmare i token JWT di provisioning
- Garantire che i token non possano essere falsificati
- Verificare l'autenticità dei token quando un nodo scarica lo script

### A cosa serve nella tua app?

Quando crei un nodo:
1. Il backend genera un **token JWT** firmato con `JWT_SECRET_KEY`
2. Il token viene codificato nel **QR code**
3. L'utente scansiona il QR code sul telefono
4. Il backend **verifica** il token usando la stessa chiave
5. Se valido, il nodo può scaricare lo script di configurazione

### Perché è separato da SECRET_KEY?

- `SECRET_KEY`: Usato per l'autenticazione utenti (login, sessioni)
- `JWT_SECRET_KEY`: Usato solo per i token di provisioning nodi

**Separare le chiavi** è una best practice di sicurezza (principle of least privilege), ma **puoi anche usare la stessa chiave** se vuoi semplificare.

---

## 📝 Configurazione .env Completa

### Opzione 1: Chiavi Separate (Più sicuro) ✅

```env
# Application
SECRET_KEY=^y&e|,kd(w.brG74ztz|<%15CIJ!0n/u0slBQ'3*>jsfg9<:=~Bhi;b1n%d?9'rW
JWT_SECRET_KEY=^NX9wZw#D:d:bt8*$"u:S{W|SK0C#,_M5W>Lks8TMEPDcC>bzqP"!UKpG9o6:KQ+
API_BASE_URL=http://46.101.189.126
```

### Opzione 2: Stessa Chiave (Più semplice) 🔄

```env
# Application
SECRET_KEY=^y&e|,kd(w.brG74ztz|<%15CIJ!0n/u0slBQ'3*>jsfg9<:=~Bhi;b1n%d?9'rW
JWT_SECRET_KEY=^y&e|,kd(w.brG74ztz|<%15CIJ!0n/u0slBQ'3*>jsfg9<:=~Bhi;b1n%d?9'rW
API_BASE_URL=http://46.101.189.126
```

### Variabile API_BASE_URL

Questa è l'URL pubblico del tuo backend, usato per:
- Generare link di provisioning nel QR code
- Creare URL di download degli script

**Development:**
```env
API_BASE_URL=http://localhost:8000
```

**Production:**
```env
API_BASE_URL=http://46.101.189.126
# oppure
API_BASE_URL=https://ztc.yourdomain.com
```

---

## 🚀 Esempio .env Completo per Development

```env
# Application
ENVIRONMENT=development
SECRET_KEY=^y&e|,kd(w.brG74ztz|<%15CIJ!0n/u0slBQ'3*>jsfg9<:=~Bhi;b1n%d?9'rW
JWT_SECRET_KEY=^y&e|,kd(w.brG74ztz|<%15CIJ!0n/u0slBQ'3*>jsfg9<:=~Bhi;b1n%d?9'rW
API_BASE_URL=http://localhost:8000
DEBUG=true

# Database - PostgreSQL
POSTGRES_SERVER=localhost
POSTGRES_USER=orizon
POSTGRES_PASSWORD=orizon_secure_password_2024
POSTGRES_DB=orizon_ztc
POSTGRES_PORT=5432

# Database - MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=orizon_logs

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Tunnel Configuration
TUNNEL_SSH_PORT=2222
TUNNEL_HTTPS_PORT=8443
TUNNEL_HUB_HOST=46.101.189.126

# SSH Server
SSH_HOST_KEY_PATH=/etc/orizon/ssh_host_key
SSH_AUTHORIZED_KEYS_PATH=/etc/orizon/authorized_keys

# Monitoring
PROMETHEUS_ENABLED=true
SENTRY_DSN=

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/orizon/app.log

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

---

## 🚀 Esempio .env Completo per Production

```env
# Application
ENVIRONMENT=production
SECRET_KEY=<genera-una-nuova-chiave-diversa-da-dev>
JWT_SECRET_KEY=<genera-una-nuova-chiave-diversa-da-dev>
API_BASE_URL=http://46.101.189.126
DEBUG=false

# Database - PostgreSQL
POSTGRES_SERVER=localhost
POSTGRES_USER=orizon
POSTGRES_PASSWORD=<strong-random-password-here>
POSTGRES_DB=orizon_ztc
POSTGRES_PORT=5432

# Database - MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=orizon_logs

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<redis-password-here>
REDIS_DB=0

# Tunnel Configuration
TUNNEL_SSH_PORT=2222
TUNNEL_HTTPS_PORT=8443
TUNNEL_HUB_HOST=46.101.189.126

# SSH Server
SSH_HOST_KEY_PATH=/etc/orizon/ssh_host_key
SSH_AUTHORIZED_KEYS_PATH=/etc/orizon/authorized_keys

# Monitoring
PROMETHEUS_ENABLED=true
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project

# Logging
LOG_LEVEL=WARNING
LOG_FILE=/var/log/orizon/app.log

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

---

## ⚠️ Sicurezza - Best Practices

### ✅ DO

- Genera chiavi random di almeno 32 caratteri
- Usa chiavi diverse per development e production
- Aggiungi `.env` al `.gitignore` (già fatto)
- Ruota le chiavi periodicamente (ogni 6-12 mesi)
- Usa HTTPS in production per `API_BASE_URL`

### ❌ DON'T

- NON commitare il file `.env` su Git
- NON usare chiavi semplici tipo "secret123"
- NON condividere le chiavi via email/chat
- NON riutilizzare la stessa chiave su progetti diversi

---

## 🧪 Verifica Configurazione

Dopo aver configurato il `.env`, verifica che tutto funzioni:

```bash
# Avvia il backend
python -m uvicorn app.main:app --reload

# In un altro terminale, testa l'health check
curl http://localhost:8000/health
```

Dovresti vedere:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development"
}
```

---

## 🔄 Rigenerare le Chiavi

Se devi rigenerare nuove chiavi:

```bash
python3 generate_secret_key.py
```

Poi copia i nuovi valori nel `.env`.

**⚠️ ATTENZIONE:** Se cambi `JWT_SECRET_KEY` in production, tutti i token di provisioning esistenti diventeranno invalidi (scadono comunque dopo 24h).

---

## 📚 Riferimenti

- [JWT.io](https://jwt.io/) - Documentazione JWT
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/) - Guida sicurezza FastAPI
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

**Built with ❤️ for Enterprise Security**
