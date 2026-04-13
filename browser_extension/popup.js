/**
 * Runs when the user opens the extension popup.
 * Reads the active tab URL, POSTs JSON to Django, then shows the response.
 */

// Backend URL from your requirements (must match runserver address).
const API_URL = "http://127.0.0.1:8000/analyze/";

/**
 * Apply green/yellow/red styling to the trust score based on risk level.
 */
function styleScoreBadge(scoreEl, riskLevel) {
  scoreEl.classList.remove("safe", "moderate", "risky");
  if (riskLevel === "Safe") {
    scoreEl.classList.add("safe");
  } else if (riskLevel === "Moderate" || riskLevel === "Moderate Risk") {
    scoreEl.classList.add("moderate");
  } else {
    scoreEl.classList.add("risky");
  }
}

/**
 * Apply styles to the banner + meter based on risk level.
 */
function styleRiskUI(riskLevel) {
  const banner = document.getElementById("risk-banner");
  const meterFill = document.getElementById("score-fill");

  // Clear old state first.
  banner.classList.remove("safe", "moderate", "risky");
  meterFill.classList.remove("safe", "moderate", "risky");

  if (riskLevel === "Safe") {
    banner.classList.add("safe");
    meterFill.classList.add("safe");
  } else if (riskLevel === "Moderate" || riskLevel === "Moderate Risk") {
    banner.classList.add("moderate");
    meterFill.classList.add("moderate");
  } else {
    banner.classList.add("risky");
    meterFill.classList.add("risky");
  }
}

/**
 * Show a big purchase callout. If risky, make it very prominent.
 */
function showPurchaseCallout(data) {
  const callout = document.getElementById("purchase-callout");
  if (!callout) return;

  const risk = data.risk_level || "";
  const rec = data.purchase_recommendation || "";

  callout.classList.remove("safe", "moderate", "risky", "hidden");

  // If the backend sends a purchase recommendation, use it.
  if (rec === "Avoid" || risk === "High Risk") {
    callout.textContent = "AVOID THIS WEBSITE";
    callout.classList.add("risky");
    return;
  }

  if (rec === "COD") {
    callout.textContent = "PREFER CASH ON DELIVERY (COD)";
    callout.classList.add("moderate");
    return;
  }

  if (rec === "Online") {
    callout.textContent = "ONLINE PAYMENT OK";
    callout.classList.add("safe");
    return;
  }

  // Fallback (if backend doesn't send purchase_recommendation)
  if (risk === "Safe") {
    callout.textContent = "ONLINE PAYMENT OK";
    callout.classList.add("safe");
  } else if (risk === "Moderate Risk" || risk === "Moderate") {
    callout.textContent = "PREFER CASH ON DELIVERY (COD)";
    callout.classList.add("moderate");
  } else {
    callout.textContent = "AVOID THIS WEBSITE";
    callout.classList.add("risky");
  }
}

/**
 * Show error text in the status area and hide the result block.
 */
function showError(message) {
  const status = document.getElementById("status");
  const result = document.getElementById("result");
  status.textContent = message;
  status.classList.add("error");
  result.classList.add("hidden");
}

/**
 * Fill the popup with JSON returned by Django.
 */
function showResult(data) {
  const status = document.getElementById("status");
  const result = document.getElementById("result");
  const siteName = document.getElementById("site-name");
  const trustScore = document.getElementById("trust-score");
  const trustScoreText = document.getElementById("trust-score-text");
  const riskLevel = document.getElementById("risk-level");
  const riskTitle = document.getElementById("risk-title");
  const payment = document.getElementById("payment");
  const reasonsList = document.getElementById("reasons");
  const meterFill = document.getElementById("score-fill");

  status.textContent = "Done.";
  status.classList.remove("error");
  result.classList.remove("hidden");

  siteName.textContent = data.website_name || "—";
  const score =
    typeof data.trust_score === "number" ? data.trust_score : null;

  trustScore.textContent = score === null ? "—" : String(score);
  trustScoreText.textContent = score === null ? "—" : `${score}%`;

  const risk = data.risk_level || "—";
  riskLevel.textContent = risk;
  riskTitle.textContent =
    risk === "—" ? "RISK UNKNOWN" : `${risk.toUpperCase()} WEBSITE`;

  payment.textContent = data.payment_recommendation || "—";

  styleScoreBadge(trustScore, data.risk_level);
  styleRiskUI(data.risk_level);
  showPurchaseCallout(data);

  // Update the meter width (0–100%).
  const pct = score === null ? 0 : Math.max(0, Math.min(100, score));
  meterFill.style.width = `${pct}%`;

  reasonsList.innerHTML = "";
  const items = Array.isArray(data.reasons) ? data.reasons : [];
  items.forEach((r) => {
    const li = document.createElement("li");
    li.textContent = r;
    reasonsList.appendChild(li);
  });
}

/**
 * Main flow: get active tab → fetch analyze API → render UI.
 */
async function main() {
  const status = document.getElementById("status");
  const currentUrl = document.getElementById("current-url");

  try {
    // Ask Chrome for the URL of the tab you are looking at.
    const [tab] = await chrome.tabs.query({
      active: true,
      lastFocusedWindow: true,
    });

    if (!tab || !tab.url) {
      showError("Could not read the tab URL (try a normal web page).");
      return;
    }

    const url = tab.url;
    currentUrl.textContent = url;

    // Block special Chrome pages — they are not real shopping sites.
    if (url.startsWith("chrome://") || url.startsWith("edge://")) {
      showError("Open a normal website (not a browser internal page).");
      return;
    }

    status.textContent = "Contacting local server…";

    // POST JSON exactly as required: { "url": "..." }
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    const data = await response.json();

    if (!response.ok) {
      showError(data.error || `Server error (${response.status})`);
      return;
    }

    showResult(data);
  } catch (e) {
    showError(
      "Cannot reach Django. Is `python manage.py runserver` running? " +
        String(e.message || e)
    );
  }
}

document.addEventListener("DOMContentLoaded", main);
