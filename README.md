# isCandid-Browser-Based-Website-Genuineness-Analysis-Software
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
[![Framework](https://img.shields.io/badge/Backend-Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Extension](https://img.shields.io/badge/Chrome-Extension-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](#license)
[![Status](https://img.shields.io/badge/Status-Active%20Development-orange?style=for-the-badge)](#)
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

The information that could have warned you — domain age, business registration, review sentiment, SSL validity — was always there. It just wasn't visible, accessible, or understandable to an ordinary person in the two minutes before they hit *Pay Now*.

**That's the exact problem this project solves.**

---

## 🚀 What It Does

**isCandid** is a Chrome browser extension that silently watches out for you as you browse. When you visit any website, click the extension icon and get an instant, plain-language verdict:

<br/>

<div align="center">

| 🟢 **SAFE** | 🟡 **NEUTRAL** | 🔴 **RISKY** |
|:-----------:|:--------------:|:------------:|
| All trust signals pass | Mixed signals detected | Multiple red flags found |
| Online payment is fine | Proceed with caution | **Use Cash on Delivery** |

</div>

<br/>

No jargon. No confusing scores. Just three words and a clear action — exactly what you need, exactly when you need it.

---

## ⚙️ How It Works

Under the hood, the extension runs a **5-signal trust analysis** on every site you ask it to check:

```
URL Submitted
     │
     ▼
┌─────────────────────────────────────────────────────┐
│              ANALYSIS ENGINE (Python)               │
│                                                     │
│  🔒 SSL Check     →  Is the connection encrypted?  │
│  📅 Domain Age    →  How old is this website?       │
│  🏢 Registration  →  Is this a real business?       │
│  ™️  Trademark     →  Is the brand verified?         │
│  ⭐ Reviews       →  What are customers saying?     │
│                                                     │
│              ↓ Weighted Scoring ↓                   │
│                                                     │
│         SAFE  ──  NEUTRAL  ──  RISKY               │
└─────────────────────────────────────────────────────┘
     │
     ▼
   Popup displays result + payment recommendation
```

Each signal contributes to a **composite trust score**. The score isn't hidden — the popup shows you exactly what passed and what didn't, in language that makes sense.

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Browser Extension** | HTML · CSS · JavaScript | Native browser support, zero overhead |
| **Backend Server** | Python + Flask | Minimal, fast, easy to debug |
| **API** | REST (HTTP/JSON) | Simple, universal communication |
| **Domain Analysis** | `python-whois` | Retrieves domain registration age |
| **SSL Validation** | `ssl` (stdlib) | Certificate authority verification |
| **Review Scraping** | `requests` | Fetches user-generated review content |
| **Sentiment Analysis** | `TextBlob` / `nltk` | Classifies review tone as positive/negative |
| **Recommendation** | Custom if-else logic | Transparent, explainable decisions |
| **Database** | MongoDB *(optional)* | Result caching for faster repeat lookups |
| **Version Control** | Git | Collaborative development |

---

## 📁 Project Structure

```
isCandid/
│
├── extension/                  # Chrome Extension (Frontend)
│   ├── manifest.json           # Extension config & permissions
│   ├── popup/
│   │   ├── popup.html          # Extension UI
│   │   ├── popup.css           # Styling & trust level colors
│   │   └── popup.js            # API calls & DOM rendering
│   └── content/
│       └── content.js          # Reads current tab URL
│
├── backend/                    # Flask Server (Backend)
│   ├── app.py                  # Flask app & API endpoint
│   ├── analysis_engine/
│   │   ├── ssl_check.py        # SSL certificate validator
│   │   ├── domain_age.py       # WHOIS domain age checker
│   │   ├── registration.py     # MCA / MSME / GST checker
│   │   ├── trademark.py        # Trademark signal detector
│   │   └── review_sentiment.py # Review scraper + NLP scorer
│   └── recommendation_engine/
│       └── recommender.py      # Trust score → COD/payment advice
│
├── requirements.txt            # Python dependencies
├── README.md                   # You are here
└── LICENSE
```

---

<div align="center">

*Department of Computer Science &  Systems Engineering | Academic Year 2025–2026*

</div>
