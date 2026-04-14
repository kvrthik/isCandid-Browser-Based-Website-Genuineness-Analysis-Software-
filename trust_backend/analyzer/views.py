"""
Views for the Trust Analysis API.
Rule-based score starting at 100, with HTTPS, SSL verification, WHOIS age, and simulated checks.
"""
import json
import os
import re
import socket
import ssl
import urllib.request
from urllib.error import URLError
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from urllib.parse import urlparse

from django.db import connection
from django.db.models import F
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from analyzer.models import WebsiteCache

# WHOIS lookup (install: pip install python-whois).
try:
    import whois
except ImportError:  # pragma: no cover - defensive if package missing
    whois = None

# Max seconds to wait for WHOIS (registrars can be slow).
WHOIS_TIMEOUT_SEC = 10.0
# RDAP is HTTP-based and often more reliable than WHOIS, but some servers are slow.
RDAP_TIMEOUT_SEC = 12.0
RDAP_BOOTSTRAP_TIMEOUT_SEC = 12.0

# Cache for IANA RDAP bootstrap (loaded once, reused).
_RDAP_TLD_TO_BASE_URLS: dict[str, list[str]] | None = None
DB_CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "86400"))

# Viva / report line (explainable AI style).
METHODOLOGY_EXPLANATION = (
    "The system calculates trust score using a rule-based approach where multiple risk "
    "factors such as SSL validity, domain age, and service indicators contribute to "
    "score reduction, making the system transparent and explainable."
)

# Simple lists for a beginner-friendly MVP.
# You can add your local brands here anytime.
KNOWN_BRANDS = {
    "amazon",
    "flipkart",
    "myntra",
    "ajio",
    "nykaa",
    "meesho",
    "snapdeal",
    "paytm",
    "phonepe",
    "gpay",
    "google",
    "apple",
    "microsoft",
}

# Curated outputs from provided dataset (domain SLD -> risk level override).
# Green -> Safe, Yellow -> Moderate Risk, Red -> High Risk.
CURATED_SITE_RISK_BY_SLD = {
    "amazon": "Safe",
    "flipkart": "Moderate Risk",
    "myntra": "Safe",
    "meesho": "High Risk",
    "souledstore": "High Risk",
    "thesouledstore": "High Risk",
    "nykaa": "Moderate Risk",
    "ajio": "Moderate Risk",
    "tatacliq": "Moderate Risk",
    "bewakoof": "Moderate Risk",
    "limeroad": "High Risk",
    "snapdeal": "High Risk",
    "paytmmall": "High Risk",
    "pepperfry": "Moderate Risk",
    "jiomart": "Safe",
    "instamart": "Safe",
    "swiggy": "Safe",
    "blinkit": "Safe",
    "zepto": "Safe",
    "bigbasket": "Moderate Risk",
    "reliancedigital": "Safe",
    "firstcry": "Safe",
    "healthkart": "Moderate Risk",
    "boat": "Moderate Risk",
    "croma": "Safe",
    "vijaysales": "Safe",
    "netmeds": "Safe",
    "1mg": "Safe",
    "pharmeasy": "Moderate Risk",
    "purplle": "Moderate Risk",
    "lenskart": "Safe",
    "mamaearth": "Moderate Risk",
    "dunzo": "Moderate Risk",
}

CURATED_REASON_TEMPLATES = {
    "High Risk": [
        "Bad delivery services reported",
        "Bad refund policy and poor return support",
        "More cases of bad product received",
    ],
    "Moderate Risk": [
        "Bad/slow refund and return policy",
        "Bad delivery service",
    ],
}

# Words that commonly appear in scammy URLs (very basic heuristic).
SUSPICIOUS_KEYWORDS = {
    # Keep this list small and explainable for college projects.
    "deal",
    "free",
    "bazaar",
    "loot",
    "win",
    "offer",
}

# Simple content keywords for service indicators.
RETURN_POLICY_KEYWORDS = (
    "return",
    "returns",
    "return policy",
    "return policies",
    "refund",
    "refunds",
    "refund policy",
    "refund policies",
    "return & refund",
    "return and refund",
    "cancellation",
    "cancel",
    "exchange",
    "exchange policy",
)

DELIVERY_KEYWORDS = (
    "shipping",
    "delivery",
    "track order",
    "order tracking",
    "estimated delivery",
    "delivery policy",
)

ECOMMERCE_KEYWORDS = (
    "add to cart",
    "buy now",
    "checkout",
    "shop now",
    "order now",
    "place order",
    "product details",
    "proceed to checkout",
    "secure checkout",
    "payment method",
    "cash on delivery",
    "wishlist",
)


def _verify_ssl_certificate(hostname: str, port: int) -> bool:
    """
    Try to complete a TLS handshake and validate the certificate using default CAs.
    Returns True if validation succeeds, False otherwise.
    """
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                # Handshake succeeded and cert verified by context.
                _ = ssock.getpeercert()
        return True
    except OSError:
        return False
    except ssl.SSLError:
        return False


def _normalize_creation_date(creation_date):
    """
    python-whois may return one datetime or a list of datetimes; pick the earliest.
    """
    if creation_date is None:
        return None
    if isinstance(creation_date, list):
        dates = [d for d in creation_date if d is not None]
        if not dates:
            return None
        return min(dates)
    return creation_date


def _domain_age_months(hostname: str):
    """
    Return domain age in months (float), or None if WHOIS lookup fails / is redacted.
    Runs WHOIS in a thread with a timeout so the API does not hang forever.
    """
    # Strip www. for a cleaner WHOIS query (common registrar behavior).
    query_host = hostname.lower().strip(".")
    if query_host.startswith("www."):
        query_host = query_host[4:]

    def _rdap_base_urls_for_tld(tld: str) -> list[str]:
        """
        Get RDAP base URLs for a TLD using the official IANA bootstrap file.
        This avoids relying on rdap.org (which can return 403 on some networks).
        """
        global _RDAP_TLD_TO_BASE_URLS
        tld = tld.lower().lstrip(".")

        # Load bootstrap once.
        if _RDAP_TLD_TO_BASE_URLS is None:
            mapping: dict[str, list[str]] = {}
            try:
                req = urllib.request.Request(
                    "https://data.iana.org/rdap/dns.json",
                    headers={"Accept": "application/json", "User-Agent": "TrustAnalyzerMVP/1.0"},
                    method="GET",
                )
                with urllib.request.urlopen(req, timeout=RDAP_BOOTSTRAP_TIMEOUT_SEC) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                services = data.get("services", []) or []
                # Each service entry is: [ [tld1, tld2, ...], [baseUrl1, baseUrl2, ...] ]
                for service in services:
                    if not isinstance(service, list) or len(service) != 2:
                        continue
                    tlds, urls = service
                    if not isinstance(tlds, list) or not isinstance(urls, list):
                        continue
                    for x in tlds:
                        if isinstance(x, str):
                            mapping[x.lower()] = [u for u in urls if isinstance(u, str)]
            except Exception:
                mapping = {}

            _RDAP_TLD_TO_BASE_URLS = mapping

        return _RDAP_TLD_TO_BASE_URLS.get(tld, []) if _RDAP_TLD_TO_BASE_URLS else []

    # First try RDAP (HTTP-based lookup). Many registries support RDAP even if WHOIS is blocked.
    # Note: Some domains may still hide dates or block automated lookups; in that case we return None.
    def _try_rdap():
        try:
            tld = query_host.split(".")[-1] if "." in query_host else query_host
            base_urls = _rdap_base_urls_for_tld(tld)

            for base in base_urls:
                # IANA base URLs usually end with a trailing slash.
                url = base.rstrip("/") + f"/domain/{query_host}"
                try:
                    req = urllib.request.Request(
                        url,
                        headers={
                            "User-Agent": "TrustAnalyzerMVP/1.0 (college-project)",
                            "Accept": "application/json",
                        },
                        method="GET",
                    )
                    with urllib.request.urlopen(req, timeout=RDAP_TIMEOUT_SEC) as resp:
                        raw = resp.read().decode("utf-8", errors="replace")
                    data = json.loads(raw)
                except Exception:
                    # Try next RDAP server if this one fails.
                    continue

                events = data.get("events", []) or []
                # RDAP eventAction values vary; check common ones.
                for ev in events:
                    action = (ev.get("eventAction") or "").lower()
                    if action in (
                        "registration",
                        "registered",
                        "domain registration",
                        "created",
                    ):
                        event_date = ev.get("eventDate")
                        if not event_date:
                            continue
                        # eventDate is usually ISO8601, often ending in Z.
                        ds = str(event_date).replace("Z", "+00:00")
                        created = datetime.fromisoformat(ds)
                        if created.tzinfo is None:
                            created = created.replace(tzinfo=timezone.utc)

                        now = datetime.now(timezone.utc)
                        delta = now - created
                        return delta.days / 30.44

        except Exception:
            return None

        return None

    age = _try_rdap()
    if age is not None:
        return age

    # Fallback to WHOIS (text-based lookup). This frequently fails because many registrars block it.
    if whois is None:
        return None

    def _lookup():
        w = whois.whois(query_host)
        created = _normalize_creation_date(getattr(w, "creation_date", None))
        if created is None:
            return None
        now = datetime.now(timezone.utc)
        if getattr(created, "tzinfo", None) is None:
            created = created.replace(tzinfo=timezone.utc)
        delta = now - created
        return delta.days / 30.44  # average month length

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_lookup)
            return future.result(timeout=WHOIS_TIMEOUT_SEC)
    except (FuturesTimeout, OSError, AttributeError, TypeError, ValueError):
        return None
    except Exception:
        # Many registrars return errors or block automated WHOIS; treat as unknown.
        return None


def _domain_name_suspicious(hostname: str) -> bool:
    """
    Heuristic: long hostnames, many hyphens, or lots of digits look less trustworthy.
    """
    h = hostname.lower()
    if len(h) > 25:
        return True
    if h.count("-") >= 3:
        return True
    digit_count = sum(c.isdigit() for c in h)
    if digit_count >= 4:
        return True
    if re.search(r"\d{3,}", h):
        return True
    return False


def _second_level_label(hostname: str) -> str:
    """
    Return the main label (simple SLD heuristic).
    Example: www.amazon.in -> amazon
    """
    host = hostname.lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    parts = [p for p in host.split(".") if p]
    if len(parts) < 2:
        return parts[0] if parts else ""
    return parts[-2]


def _is_known_brand(hostname: str) -> bool:
    """
    Very simple 'known brand' check for demos.
    """
    sld = _second_level_label(hostname)
    return sld in KNOWN_BRANDS


def _has_suspicious_keywords(url_string: str, hostname: str) -> bool:
    """
    Check keywords in the DOMAIN only (as per your final logic).
    """
    h = hostname.lower()
    return any(k in h for k in SUSPICIOUS_KEYWORDS)


def _payment_for_risk(risk_level: str) -> str:
    if risk_level == "Safe":
        return "Safe to use Online Payment"
    if risk_level == "Moderate Risk":
        return "Prefer Cash on Delivery (COD)"
    return "Avoid this Website"


def _purchase_for_risk(risk_level: str) -> str:
    if risk_level == "Safe":
        return "Online"
    if risk_level == "Moderate Risk":
        return "COD"
    return "Avoid"


def _remove_not_known_brand_reason(reasons: list[str]) -> list[str]:
    cleaned: list[str] = []
    for r in reasons:
        if (r or "").strip().lower() == "not a known brand":
            continue
        cleaned.append(r)
    return cleaned


def _fetch_page_text_for_checks(url_string: str) -> str | None:
    """
    Download a small amount of HTML text for simple keyword checks.
    Beginner note: this is NOT a real crawler; it just fetches one page.
    Returns lowercase text, or None if fetch fails.
    """
    try:
        parsed = urlparse(url_string.strip())
        if parsed.scheme not in ("http", "https"):
            return None

        # Try the given URL first. If it fails, fall back to the homepage.
        candidates = [url_string.strip()]
        if parsed.hostname:
            home = f"{parsed.scheme}://{parsed.hostname}/"
            if home not in candidates:
                candidates.append(home)

        for url in candidates:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "TrustAnalyzerMVP/1.0 (college-project)",
                    "Accept": "text/html,*/*",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                raw = resp.read(200_000)  # read up to ~200KB (enough for keyword scan)
            try:
                text = raw.decode("utf-8", errors="replace")
            except Exception:
                text = str(raw)
            return text.lower()
    except Exception:
        return None

    return None


def _return_policy_found(url_string: str, page_text: str | None) -> bool | None:
    """
    Return True/False if we can check; None if page text could not be fetched.
    """
    if page_text is not None and any(k in page_text for k in RETURN_POLICY_KEYWORDS):
        return True

    # Fallback for JS-heavy sites: check common policy URLs directly.
    parsed = urlparse(url_string.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None if page_text is None else False

    base = f"{parsed.scheme}://{parsed.hostname}"
    policy_paths = (
        "/returns",
        "/return-policy",
        "/refund-policy",
        "/cancellation-policy",
        "/exchange-policy",
        "/pages/returns",
        "/pages/return-policy",
        "/pages/refund-policy",
        "/policies/refund-policy",
        "/policies/shipping-policy",
    )
    for p in policy_paths:
        text = _fetch_page_text_for_checks(base + p)
        if text is not None and any(k in text for k in RETURN_POLICY_KEYWORDS):
            return True

    return None if page_text is None else False


def _delivery_info_found(page_text: str | None) -> bool | None:
    """
    Return True/False if we can check; None if page text could not be fetched.
    """
    if page_text is None:
        return None
    return any(k in page_text for k in DELIVERY_KEYWORDS)


def _is_ecommerce_website(url_string: str, page_text: str | None) -> bool:
    """
    Best-effort ecommerce detection for payment guidance.
    """
    u = url_string.lower()
    parsed = urlparse(url_string.strip())
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()

    # Strong URL/path signals.
    if any(
        x in (u + " " + path)
        for x in (
            "/product",
            "/products",
            "/shop",
            "/cart",
            "/checkout",
            "/buy",
            "/collections",
            "/collection",
            "/category",
            "/categories",
            "/order",
        )
    ):
        return True

    # Domain-level commerce signals (helps JS-heavy stores where keywords
    # may not appear in fetched HTML).
    if host.endswith(".store") or host.endswith(".shop"):
        return True
    if any(k in host for k in ("shop", "store", "boutique", "mart")):
        return True

    if page_text is None:
        return False

    # Avoid false positives on normal websites by requiring multiple strong signals.
    keyword_hits = sum(1 for k in ECOMMERCE_KEYWORDS if k in page_text)
    return keyword_hits >= 2


def _downgrade_purchase_level(level: str) -> str:
    """
    One-step downgrade: Online -> COD -> Avoid.
    """
    if level == "Online":
        return "COD"
    if level == "COD":
        return "Avoid"
    return "Avoid"


def _purchase_recommendation(
    trust_score: int,
    confidence_level: str,
    risk_level: str,
    return_policy_ok: bool | None,
    delivery_ok: bool | None,
) -> tuple[str, list[str]]:
    """
    Implements your Purchase Recommendation Algorithm.
    Returns (recommendation, reasons).
    """
    rec_reasons: list[str] = []

    # 1) Critical risk check
    if risk_level == "High Risk":
        return "Avoid", ["High Risk detected → Avoid Purchase"]

    # 2) Base recommendation (score)
    if trust_score >= 75:
        rec = "Online"
    elif trust_score >= 50:
        rec = "COD"
    else:
        rec = "Avoid"

    # 3) Adjust based on confidence
    if confidence_level == "Low":
        rec = _downgrade_purchase_level(rec)
        rec_reasons.append("Confidence is Low → downgraded recommendation")

    # 4) Return policy check
    if return_policy_ok is False or return_policy_ok is None:
        rec = _downgrade_purchase_level(rec)
        rec_reasons.append("Return/Refund policy not found → downgraded recommendation")
    else:
        rec_reasons.append("Return/Refund policy found")

    # 5) Delivery reliability check (basic)
    if delivery_ok is False or delivery_ok is None:
        rec = _downgrade_purchase_level(rec)
        rec_reasons.append("Delivery information is uncertain → downgraded recommendation")
    else:
        rec_reasons.append("Delivery information found")

    return rec, rec_reasons


def _risk_band(score: int) -> str:
    """
    Base risk classification by score.
    """
    if score >= 75:
        return "Safe"
    if score >= 50:
        return "Moderate Risk"
    return "High Risk"


def _downgrade_risk_one_level(risk_level: str) -> str:
    """
    Used when confidence is LOW (Safe->Moderate, Moderate->High).
    """
    if risk_level == "Safe":
        return "Moderate Risk"
    if risk_level == "Moderate Risk":
        return "High Risk"
    return "High Risk"


def _analyze_url(url_string: str, client_signals: dict | None = None) -> dict:
    """
    Apply the project’s trust rules: start at 100, subtract for risks, clamp, classify.
    """
    reasons: list[str] = []
    score = 100

    parsed = urlparse(url_string.strip())
    scheme = (parsed.scheme or "").lower()
    hostname = (parsed.hostname or "").lower()

    if not hostname:
        return {
            "website_name": "(invalid URL)",
            "trust_score": 0,
            "risk_level": "High Risk",
            "reasons": ["Could not read a valid hostname from the URL."],
            "payment_recommendation": "Avoid this Website",
            "confidence_level": "Low",
            "explanation": METHODOLOGY_EXPLANATION,
        }

    website_name = hostname
    https = scheme == "https"
    port = parsed.port or (443 if https else 80)

    # Track “suspicion signals” for combination logic.
    unknown_age = False
    suspicious_name = False
    suspicious_keywords = False
    not_known_brand = False
    ssl_valid = False

    # 2) HTTPS check
    if not https:
        score -= 30
        reasons.append("Website does not use HTTPS")
    else:
        reasons.append("HTTPS is enabled")

    # 3) SSL certificate validation (only meaningful when HTTPS; otherwise “missing”)
    if https:
        if _verify_ssl_certificate(hostname, port):
            ssl_valid = True
            reasons.append("Valid SSL certificate detected")
        else:
            score -= 20
            reasons.append("SSL certificate is invalid or missing")

    # 4) Domain age via WHOIS
    age_months = _domain_age_months(hostname)
    if age_months is None:
        score -= 25
        reasons.append("Domain age unknown")
        unknown_age = True
    elif age_months < 6:
        score -= 25
        reasons.append("Domain is very new")
    elif age_months < 12:
        score -= 10
        reasons.append("Domain is relatively new")
    else:
        reasons.append("Domain is old and trusted")

    # 5) Domain name quality
    if _domain_name_suspicious(hostname):
        score -= 20
        reasons.append("Suspicious domain name")
        suspicious_name = True

    # 5b) Known brand (very simple demo check)
    if not _is_known_brand(hostname):
        score -= 15
        reasons.append("Not a known brand")
        not_known_brand = True
    else:
        reasons.append("Known brand detected")

    # 5c) Suspicious keywords in URL / hostname
    if _has_suspicious_keywords(url_string, hostname):
        score -= 15
        reasons.append("Suspicious keywords found in domain")
        suspicious_keywords = True

    # 4-signal combination penalty (your Step 4).
    suspicion_signals = sum(
        1
        for x in (unknown_age, suspicious_name, suspicious_keywords, not_known_brand)
        if x
    )
    if suspicion_signals >= 2:
        score -= 20
        reasons.append("Multiple suspicion signals detected (extra penalty)")

    # -------- Confidence Level (High / Medium / Low) --------
    # Default to Medium, then promote to High or demote to Low based on your refined rules.
    confidence_level = "Medium"

    age_known = age_months is not None
    age_gt_1y = age_known and age_months >= 12
    age_6_12 = age_known and 6 <= age_months < 12

    # Low if domain age unknown AND at least 1 suspicious signal,
    # OR multiple checks fail (we treat 3+ major failures as "multiple").
    major_failures = 0
    if not https:
        major_failures += 1
    if https and not ssl_valid:
        major_failures += 1
    if unknown_age:
        major_failures += 1
    if suspicious_name:
        major_failures += 1
    if suspicious_keywords:
        major_failures += 1

    if (unknown_age and (suspicious_name or suspicious_keywords)) or major_failures >= 3:
        confidence_level = "Low"
    else:
        # High if age > 1 year, SSL valid, and no suspicious signals (clean domain).
        if age_gt_1y and ssl_valid and (not suspicious_name) and (not suspicious_keywords) and suspicion_signals == 0:
            confidence_level = "High"
        # Medium if ANY of these: age 6–12 months, exactly 1 suspicion signal,
        # or brand unknown but domain looks normal.
        elif age_6_12 or suspicion_signals == 1 or (not_known_brand and (not suspicious_name) and (not suspicious_keywords)):
            confidence_level = "Medium"
        else:
            confidence_level = "High"

    # 7) Clamp
    score = max(0, min(100, int(round(score))))

    # 8) Base risk classification
    risk_level = _risk_band(score)

    # 5) CRITICAL RISK OVERRIDES (apply after base classification)
    # Case 1: Domain age unknown AND suspicious domain name => FORCE High Risk + Avoid
    forced_high = False
    if unknown_age and suspicious_name:
        forced_high = True
        risk_level = "High Risk"
        reasons.append("Override: unknown domain age + suspicious domain name")

    # Case 2: Domain age < 6 months AND suspicious keywords => FORCE High Risk
    if (age_months is not None and age_months < 6) and suspicious_keywords:
        forced_high = True
        risk_level = "High Risk"
        reasons.append("Override: very new domain + suspicious keywords")

    # Case 3: Not a known brand AND multiple suspicion signals (>=2) => At least Moderate Risk
    if not_known_brand and suspicion_signals >= 2 and risk_level == "Safe":
        risk_level = "Moderate Risk"
        reasons.append("Override: unknown brand + multiple suspicion signals")

    # -------- Refined Step 9: Balanced Trust Cap --------
    # High risk cap (force High Risk):
    # Domain age unknown AND (suspicious domain name OR suspicious keywords)
    if unknown_age and (suspicious_name or suspicious_keywords):
        risk_level = "High Risk"
        reasons.append("Trust cap: unknown age + suspicious patterns => High Risk")

    # Moderate risk cap:
    # If domain age is unknown OR between 6–12 months AND no strong suspicious signals,
    # then MAX = Moderate Risk.
    strong_suspicion = suspicious_name or suspicious_keywords or suspicion_signals >= 2
    if (unknown_age or age_6_12) and (not strong_suspicion) and risk_level == "Safe":
        risk_level = "Moderate Risk"
        reasons.append("Trust cap: young/unknown age => max Moderate Risk")

    # Allow Safe ONLY if all safe conditions hold.
    safe_allowed = (
        age_gt_1y
        and ssl_valid
        and (not suspicious_name)
        and (not suspicious_keywords)
        and suspicion_signals <= 1
        and confidence_level == "High"
    )
    if safe_allowed:
        risk_level = "Safe"
        reasons.append("Trust cap: all safe conditions satisfied => Safe")

    # Confidence adjustment from your earlier steps still applies for LOW:
    # Downgrade one level if confidence is LOW.
    if confidence_level == "Low":
        risk_level = _downgrade_risk_one_level(risk_level)
        reasons.append("Confidence is LOW: risk level downgraded one step")

    # 9) Payment recommendation
    if risk_level == "Safe":
        payment = "Safe to use Online Payment"
    elif risk_level == "Moderate Risk":
        payment = "Prefer Cash on Delivery (COD)"
    else:
        payment = "Avoid this Website"

    # -------- Service indicators (Return Policy / Delivery) --------
    page_text = _fetch_page_text_for_checks(url_string)
    return_policy_ok = _return_policy_found(url_string, page_text)
    delivery_ok = _delivery_info_found(page_text)
    client_is_ecommerce = None

    # Optional client-side signals from extension DOM scan.
    if isinstance(client_signals, dict):
        c_ret = client_signals.get("return_policy_found")
        c_del = client_signals.get("delivery_info_found")
        c_ecom = client_signals.get("is_ecommerce")
        if c_ret is True:
            return_policy_ok = True
            reasons.append("Return/Refund policy found on page (extension DOM scan)")
        if c_del is True:
            delivery_ok = True
            reasons.append("Delivery/Shipping info found on page (extension DOM scan)")
        if isinstance(c_ecom, bool):
            client_is_ecommerce = c_ecom

    # Add simple transparency reasons (only add when we know).
    if return_policy_ok is True:
        reasons.append("Return/Refund policy seems present (keyword check)")
    elif return_policy_ok is False:
        reasons.append("Return/Refund policy not found (keyword check)")

    if delivery_ok is True:
        reasons.append("Delivery/Shipping info seems present (keyword check)")
    elif delivery_ok is False:
        reasons.append("Delivery/Shipping info not found (keyword check)")

    # -------- Purchase recommendation system --------
    is_ecommerce = _is_ecommerce_website(url_string, page_text)
    if client_is_ecommerce is True:
        is_ecommerce = True
    if is_ecommerce:
        purchase_rec, purchase_rec_reasons = _purchase_recommendation(
            trust_score=score,
            confidence_level=confidence_level,
            risk_level=risk_level,
            return_policy_ok=return_policy_ok,
            delivery_ok=delivery_ok,
        )
    else:
        payment = "No payment required (non-ecommerce website)"
        purchase_rec = "No Payment"
        purchase_rec_reasons = [
            "No ecommerce signals found, so payment recommendation is not applicable."
        ]
        reasons.append("This appears to be a non-ecommerce website")

    result = {
        "website_name": website_name,
        "trust_score": score,
        "risk_level": risk_level,
        "reasons": reasons,
        "payment_recommendation": payment,
        "confidence_level": confidence_level,
        "service_indicators": {
            "return_policy_found": return_policy_ok,
            "delivery_info_found": delivery_ok,
            "is_ecommerce": is_ecommerce,
        },
        "purchase_recommendation": purchase_rec,
        "purchase_recommendation_reasons": purchase_rec_reasons,
        "explanation": METHODOLOGY_EXPLANATION,
    }

    # For non-curated websites: if unknown brand still ends up Safe, downgrade to Moderate.
    sld = _second_level_label(hostname)
    curated_risk = CURATED_SITE_RISK_BY_SLD.get(sld)
    is_ecommerce_result = (
        isinstance(result.get("service_indicators"), dict)
        and result["service_indicators"].get("is_ecommerce") is True
    )
    if (
        not curated_risk
        and result.get("risk_level") == "Safe"
        and not _is_known_brand(hostname)
        and is_ecommerce_result
    ):
        result["risk_level"] = "Moderate Risk"
        result["payment_recommendation"] = _payment_for_risk("Moderate Risk")
        result["purchase_recommendation"] = _purchase_for_risk("Moderate Risk")
        reasons_list = result.get("reasons") or []
        reasons_list.append("Brand verification unavailable; classified as Moderate Risk")
        result["reasons"] = reasons_list

    # Final curated override for known websites from provided dataset.
    if curated_risk:
        result["risk_level"] = curated_risk
        result["payment_recommendation"] = _payment_for_risk(curated_risk)
        result["purchase_recommendation"] = _purchase_for_risk(curated_risk)
        if curated_risk in CURATED_REASON_TEMPLATES:
            result["reasons"] = CURATED_REASON_TEMPLATES[curated_risk]
        else:
            reasons_list = result.get("reasons") or []
            reasons_list.append("Curated override applied from verified website dataset")
            result["reasons"] = reasons_list

    # Never expose "Not a known brand" in final output.
    reasons_list = result.get("reasons")
    if isinstance(reasons_list, list):
        result["reasons"] = _remove_not_known_brand_reason(reasons_list)

    return result


def _normalized_url_key(url_string: str) -> str:
    """
    Create a stable cache key from URL parts (scheme + host + path + query).
    """
    p = urlparse(url_string.strip())
    scheme = (p.scheme or "https").lower()
    host = (p.hostname or "").lower()
    path = p.path or "/"
    query = f"?{p.query}" if p.query else ""
    return f"{scheme}://{host}{path}{query}"


def _ensure_non_ecommerce_reason(result: dict) -> dict:
    """
    Ensure non-ecommerce explanation is present whenever payment is not needed.
    """
    if not isinstance(result, dict):
        return result

    payment = (result.get("payment_recommendation") or "").lower()
    purchase = (result.get("purchase_recommendation") or "").lower()
    if "no payment" not in payment and purchase != "no payment":
        return result

    reasons = result.get("reasons")
    if not isinstance(reasons, list):
        reasons = []
    marker = "This appears to be a non-ecommerce website"
    if marker not in reasons:
        reasons.append(marker)
    result["reasons"] = reasons
    return result


def _db_cache_get(url_key: str) -> dict | None:
    """
    Fetch cached analysis result from local database cache.
    Returns None when not found/expired/error.
    """
    try:
        row = WebsiteCache.objects.filter(url_key=url_key).first()
        if row is None:
            return None

        age_seconds = (datetime.now(timezone.utc) - row.updated_at).total_seconds()
        if age_seconds > DB_CACHE_TTL_SECONDS:
            return None

        analysis = row.analysis_json
        if isinstance(analysis, dict):
            WebsiteCache.objects.filter(url_key=url_key).update(
                access_count=F("access_count") + 1,
                last_accessed_at=datetime.now(timezone.utc),
            )
            return analysis
        return None
    except Exception as exc:
        print(f"[db-cache] cache read failed for {url_key}: {exc}")
        return None


def _db_cache_set(url_key: str, url_string: str, result: dict) -> None:
    """
    Upsert cache record to local database cache.
    """
    try:
        now = datetime.now(timezone.utc)
        WebsiteCache.objects.update_or_create(
            url_key=url_key,
            defaults={
                "url": url_string,
                "website_name": result.get("website_name"),
                "trust_score": result.get("trust_score"),
                "risk_level": result.get("risk_level"),
                "confidence_level": result.get("confidence_level"),
                "analysis_json": result,
                "updated_at": now,
                "last_accessed_at": now,
                "access_count": 1,
            },
        )
    except Exception as exc:
        print(f"[db-cache] cache write failed for {url_key}: {exc}")
        return


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def analyze(request):
    """
    POST /analyze/
    Body JSON: {"url": "https://example.com"}
    Returns JSON with trust fields (OPTIONS is for CORS preflight).
    """
    if request.method == "OPTIONS":
        return JsonResponse({}, status=200)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Invalid JSON body. Send: {\"url\": \"https://...\"}"},
            status=400,
        )

    url = body.get("url")
    if not url or not isinstance(url, str):
        return JsonResponse(
            {"error": 'Missing or invalid "url" field (must be a string).'},
            status=400,
        )

    client_signals = body.get("client_signals")
    if not isinstance(client_signals, dict):
        client_signals = None

    url_key = _normalized_url_key(url)

    # 1) Try cache first.
    # Skip cache when client signals are present (page-specific dynamic content).
    cached = None if client_signals else _db_cache_get(url_key)
    if isinstance(cached, dict):
        cached = _ensure_non_ecommerce_reason(cached)
        cached["cache_hit"] = True
        return JsonResponse(cached)

    # 2) Run fresh analysis.
    result = _analyze_url(url, client_signals=client_signals)
    result = _ensure_non_ecommerce_reason(result)
    result["cache_hit"] = False

    # 3) Save in cache (best effort).
    if not client_signals:
        _db_cache_set(url_key, url, result)
    return JsonResponse(result)


@require_http_methods(["GET"])
def health(request):
    """
    Lightweight health endpoint for deployment checks.
    """
    engine = connection.settings_dict.get("ENGINE", "")
    if "postgresql" in engine:
        db_backend = "postgresql"
    elif "sqlite3" in engine:
        db_backend = "sqlite"
    else:
        db_backend = engine or "unknown"

    return JsonResponse(
        {
            "status": "ok",
            "db_backend": db_backend,
            "cache_ttl_seconds": DB_CACHE_TTL_SECONDS,
        }
    )
