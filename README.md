# 🤖 Universal Form Bot

Bot universel qui découvre, soumet et collecte les données de **n'importe quel formulaire web**, avec dashboard React pour le configurer.

## Architecture

```
universal-bot/
├── backend/           ← FastAPI + Playwright + APScheduler
│   ├── main.py        ← API REST + scheduler
│   ├── scraper.py     ← Auto-découverte + soumission formulaires
│   ├── fetcher.py     ← Netlify / Supabase / Firebase / page scraping
│   ├── exporter.py    ← Export Excel
│   ├── config_manager.py
│   └── requirements.txt
│
└── frontend/          ← Dashboard React (Vite)
    ├── src/App.jsx    ← UI complète (4 onglets)
    └── package.json
```

## 🚀 Déploiement

### Backend → Railway

```bash
cd backend
git init && git add . && git commit -m "bot backend"
# Créer repo GitHub → Railway → New Project → Deploy from GitHub
```

Variables d'environnement Railway (optionnelles, tout est configurable via dashboard) :
```
PORT=8000
```

Commande de démarrage Railway :
```
playwright install chromium && playwright install-deps chromium && uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Frontend → Netlify / Vercel

```bash
cd frontend
cp .env.example .env
# Mettre l'URL du backend Railway dans VITE_API_URL
npm install
npm run build
# Déployer le dossier dist/ sur Netlify ou Vercel
```

## 📱 Onglets du dashboard

| Onglet | Fonction |
|---|---|
| **Dashboard** | Statuts, lancer le bot, télécharger Excel |
| **Config** | Configurer site cible, backend, scheduler |
| **Leads** | Tableau des leads récupérés en live |
| **Historique** | Log de tous les cycles effectués |

## 🔌 Backends supportés

| Backend | Config requise |
|---|---|
| Netlify Forms | Token + Site ID |
| Supabase | URL + Anon Key + Table |
| Firebase | Project ID + Collection |
| Page confirmation | URL de la page merci |
| Aucun | Soumission only (log local) |

## 🌐 API Backend

```
GET  /api/status        → état du bot
GET  /api/config        → config courante
POST /api/config        → sauvegarder config
POST /api/run           → lancer cycle manuellement
GET  /api/history       → historique des cycles
GET  /api/leads         → preview leads (50 max)
GET  /api/download      → télécharger dernier Excel
```
