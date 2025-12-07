# Orizon Zero Trust Enterprise SASE - Documentation Index

**Version 3.0.1** | **Last Updated: 2025-12-07**

---

## Quick Links / Link Rapidi

| Document | Description | Documento | Descrizione |
|----------|-------------|-----------|-------------|
| [ARCHITECTURE.md](../ARCHITECTURE.md) | Full architecture | Architettura completa |
| [ARCHITECTURE_EN.html](../ARCHITECTURE_EN.html) | Interactive docs (EN) | Docs interattivi (EN) |
| [ARCHITECTURE_IT.html](../ARCHITECTURE_IT.html) | Interactive docs (IT) | Docs interattivi (IT) |
| [QUICK_START.md](./QUICK_START.md) | Quick start guide | Guida rapida |
| [INFRASTRUCTURE.md](./INFRASTRUCTURE.md) | Infrastructure details | Dettagli infrastruttura |

---

## Documentation Structure / Struttura Documentazione

```
/
├── README.md                 # Project overview
├── ARCHITECTURE.md           # Complete architecture (Markdown)
├── ARCHITECTURE_EN.html      # Interactive documentation (English)
├── ARCHITECTURE_IT.html      # Interactive documentation (Italian)
├── CHANGELOG.md              # Version history
└── docs/
    ├── README.md             # This file - Documentation index
    ├── QUICK_START.md        # Quick start guide
    └── INFRASTRUCTURE.md     # Infrastructure & credentials reference
```

---

## For Developers / Per Sviluppatori

### Local Development
```bash
# Clone repository
git clone https://github.com/MarcoLorenzi1969/OrizonZeroTrustEnterpriseSASE.git
cd OrizonZeroTrustEnterpriseSASE

# Start services
docker compose up -d

# Frontend development
cd frontend && npm install && npm run dev

# Backend runs on :8000, Frontend on :5173
```

### Deployment to Hubs
```bash
# Sync to HUB
rsync -avz --exclude 'node_modules' --exclude '.git' ./ user@HUB_IP:/opt/orizon-ztc/

# Rebuild on HUB
ssh user@HUB_IP "cd /opt/orizon-ztc && docker compose build && docker compose up -d"
```

---

## Support / Supporto

- **GitHub Issues**: [Report bugs](https://github.com/MarcoLorenzi1969/OrizonZeroTrustEnterpriseSASE/issues)
- **Email**: marco@syneto.eu

---

© 2025 Syneto / Orizon - All Rights Reserved
