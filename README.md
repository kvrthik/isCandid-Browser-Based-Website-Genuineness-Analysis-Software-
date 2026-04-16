<div align="center">

<br/>

```
  _      ___              _ _    _ 
 (_)    / __|__ _ _ _  __| (_)__| |
 | |__ | (__/ _` | ' \/ _` | / _` |
 |____| \___\__,_|_||_\__,_|_\__,_|
```

### 🛡️ Browser-Based Website Genuineness Analysis & Purchase Recommendation System

**Know before you buy. Trust before you pay.**

<br/>

[![Made With](https://img.shields.io/badge/Made%20With-Python%20%2B%20JS-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Backend-Django-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Deployed On](https://img.shields.io/badge/Deployed%20On-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)
[![Extension](https://img.shields.io/badge/Chrome-Extension%20MV3-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](#license)
[![DT%26I](https://img.shields.io/badge/Design%20Thinking-%26%20Innovation-purple?style=for-the-badge)](#)

<br/>

> *"Every day, thousands of people lose money to fake online stores. Most of them had no idea the site was dangerous — until it was too late."*

<br/>

</div>

---

## 🤔 Why Does This Exist?

Picture this: you find a great deal on a website you've never heard of. The site looks professional. It has product photos, reviews, even a padlock icon in the address bar. You enter your card details and check out.

Three weeks later — nothing has arrived. You try to contact the seller. No response. You request a refund. Ignored. The website is gone.

**This happens to millions of people every year.** And almost every single one of them had the same thought afterwards: *"I wish I had known."*

The information that could have warned you — domain age, SSL validity, suspicious domain patterns, service signals — was always there. It just wasn't visible, accessible, or understandable to an ordinary person in the two minutes before they hit *Pay Now*.

**That's the exact problem isCandid solves.**

---

## 🚀 What It Does

**isCandid** is a Chrome browser extension (Manifest V3) that silently watches out for you as you browse. Click the extension icon on any website and get an instant, plain-language verdict:

<br/>

<div align="center">

| 🟢 **SAFE** | 🟡 **MODERATE RISK** | 🔴 **HIGH RISK** |
|:-----------:|:--------------------:|:----------------:|
| Trust score ≥ 75 | Trust score 50–74 | Trust score < 50 |
| Online payment is fine | Prefer Cash on Delivery | **Avoid this website** |

</div>

<br/>

No jargon. No confusing numbers. Just a color-coded verdict and a clear payment action — exactly what you need, exactly when you need it.

---

## ⚙️ How It Works

The extension and backend work together in a clean two-step process:

**Step 1 — The extension scans the page locally:**

Before calling the backend, `popup.js` runs a lightweight scan of the currently open page — reading visible text and links to detect whether the site is an e-commerce platform and whether it displays return/delivery information. This happens entirely inside your browser, instantly.

**Step 2 — The backend does the deep analysis:**

```
Your Browser                          Backend (Vercel)
──────────────────────────────────────────────────────────────
  popup.js scans page signals
        │
        │  POST { url, client_signals }
        ▼
  https://trustbackend-one.vercel.app/analyze/
        │
        ├─ 🔒 HTTPS check + SSL certificate validation
        ├─ 📅 Domain age  (RDAP first → WHOIS fallback)
        ├─ 🔍 Domain name suspiciousness heuristics
        ├─ 🏷️  Known-brand recognition
        ├─ ⚠️  Suspicious keyword detection in URL/domain
        ├─ 🔗 Combination penalty (2+ suspicion signals)
        ├─ 📦 Return policy & delivery info detection
        └─ 🛒 E-commerce detection
              │
              ▼
        Trust Score (0–100)
              │
              ▼
        Risk Level  ──→  Payment Recommendation
              │
              ▼
   Extension renders traffic-light banner + purchase callout
```

Every signal that fires is surfaced in the response — the popup shows you exactly what passed, what failed, and the reasoning behind the final verdict.

---

## 🛠️ Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| **Browser Extension** | HTML · CSS · JavaScript (MV3) | UI, local page scanning, API communication |
| **Backend Framework** | Python + Django | REST API, trust analysis orchestration |
| **Deployment** | Vercel (serverless) | Hosts live backend at `trustbackend-one.vercel.app` |
| **Serverless Entry** | `api/index.py` (Django WSGI) | Bridges Vercel → Django |
| **Domain Age** | RDAP (IANA bootstrap) + `python-whois` | Age lookup with automatic fallback |
| **SSL Validation** | Python `ssl` stdlib | TLS handshake + certificate authority check |
| **Page Fetching** | `requests` | Fetches up to ~200 KB of page HTML for keyword analysis |
| **Database** | PostgreSQL (`DATABASE_URL` env) / SQLite (local dev) | Result caching via `WebsiteCache` model |
| **CORS** | `django-cors-headers` | Allows extension → backend cross-origin requests |
| **Version Control** | Git | Collaborative development |

---

## 📁 Project Structure

```
isCandid/
│
├── browser_extension/              # Chrome Extension (Frontend)
│   ├── manifest.json               # MV3 config, permissions, host permissions
│   ├── popup.html                  # Extension popup UI
│   ├── popup.css                   # Styling + traffic-light banner colors
│   └── popup.js                    # Page scanner, API call, result renderer
│
├── trust_backend/                  # Django Backend
│   ├── manage.py
│   ├── requirements.txt
│   ├── vercel.json                 # Routes all traffic → api/index.py
│   ├── api/
│   │   └── index.py                # Vercel serverless entrypoint (Django WSGI)
│   ├── trust_project/
│   │   ├── settings.py             # Django config, CORS, DB, cache TTL
│   │   └── urls.py                 # /analyze/ and /health/ routes
│   └── analyzer/
│       ├── views.py                # Core trust scoring + all analysis logic
│       ├── models.py               # WebsiteCache model
│       └── migrations/
│           └── 0001_initial.py     # DB schema
│
├── privacy.html                    # Privacy policy (extension store listing)
├── PRIVACY_POLICY.md
├── README.md                       # You are here
└── LICENSE
```

---

<div align="center">

*Department of Computer Science &  Systems Engineering | Academic Year 2024–2025*

</div>
