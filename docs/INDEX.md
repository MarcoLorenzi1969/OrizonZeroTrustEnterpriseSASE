# Orizon Zero Trust Connect - Documentazione

**Versione:** 2.0.2 | **Aggiornamento:** 28 Novembre 2025

---

## Guida Rapida

| Obiettivo | Documento | Lingua |
|-----------|-----------|--------|
| Panoramica progetto | [README](../README.md) | EN |
| Usare la piattaforma | [USER_GUIDE](./USER_GUIDE.md) | IT |
| Integrare con API | [API_REFERENCE](./API_REFERENCE.md) | IT |
| Capire l'architettura | [ARCHITECTURE](./ARCHITECTURE.md) | IT |
| Sicurezza | [SECURITY_GUIDE](./SECURITY_GUIDE.md) | IT |
| Multi-tenant | [MULTI_TENANT_SYSTEM](./MULTI_TENANT_SYSTEM.md) | IT |
| Deploy produzione | [DEPLOYMENT_GUIDE](./DEPLOYMENT_GUIDE.md) | EN |
| Sviluppo locale | [DEVELOPMENT_GUIDE](./DEVELOPMENT_GUIDE.md) | EN |
| Script edge nodes | [scripts/README](../scripts/README.md) | IT |

---

## Pagine Dashboard (6)

| Pagina | Route | Ruolo Minimo |
|--------|-------|--------------|
| Dashboard | `/dashboard` | User |
| Tunnels Dashboard | `/tunnels-dashboard` | User |
| Nodes | `/nodes` | User |
| Edge Provisioning | `/provision` | Admin |
| Groups | `/groups` | Admin |
| RDP Direct | `/rdp-direct` | Admin |

---

## Gerarchia Ruoli

```
SuperUser → SuperAdmin → Admin → User
```

| Ruolo | Permessi |
|-------|----------|
| SuperUser | Accesso completo, gestione tenant |
| SuperAdmin | Gestione utenti e configurazioni |
| Admin | Gestione nodi e gruppi |
| User | Visualizzazione dashboard e nodi |

---

## Link Utili

- **Server Produzione:** 139.59.149.48
- **API Docs:** http://139.59.149.48:8000/docs
- **Dashboard:** http://139.59.149.48/dashboard

---

## Struttura Repository

```
OrizonZeroTrustEnterpriseSASE/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── core/           # Config, security
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic
│   └── alembic/            # Database migrations
├── frontend/               # React frontend
│   └── src/
│       ├── pages/          # 6 pagine core
│       ├── components/     # UI components
│       ├── services/       # API services
│       └── store/          # Redux store
├── scripts/                # Script installazione edge nodes
├── docs/                   # Documentazione (questo file)
└── docker-compose.yml      # Orchestrazione container
```

---

## Contatti

- **Autore:** Marco @ Syneto
- **Progetto:** Orizon Zero Trust Connect
