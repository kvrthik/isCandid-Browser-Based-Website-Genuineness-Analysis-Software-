/**
 * Runs when the user opens the extension popup.
 * Reads the active tab URL, POSTs JSON to Django, then shows the response.
 */

// Hosted backend URL for production extension use.
const API_URL = "https://trustbackend.vercel.app/analyze/";
const EXT_API =
  typeof browser !== "undefined" ? browser : chrome;

function styleRiskBanner(riskLevel, score) {
  const banner = document.getElementById("risk-banner");
  const trafficLight = document.getElementById("traffic-light");
  banner.classList.remove("safe", "moderate", "risky");
  trafficLight.classList.remove("green", "yellow", "red");

  if (riskLevel === "Safe") {
    banner.classList.add("safe");
  } else if (riskLevel === "Moderate" || riskLevel === "Moderate Risk") {
    banner.classList.add("moderate");
  } else {
    banner.classList.add("risky");
  }

  if (typeof score === "number") {
    if (score >= 75) {
      trafficLight.classList.add("green");
    } else if (score >= 50) {
      trafficLight.classList.add("yellow");
    } else {
      trafficLight.classList.add("red");
    }
    return;
  }

  if (riskLevel === "Safe") {
    trafficLight.classList.add("green");
  } else if (riskLevel === "Moderate" || riskLevel === "Moderate Risk") {
    trafficLight.classList.add("yellow");
  } else {
    trafficLight.classList.add("red");
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

  if (rec === "No Payment") {
    callout.textContent = "NO PAYMENT NEEDED";
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
  const frontView = document.getElementById("front-view");
  const backView = document.getElementById("back-view");
  const siteName = document.getElementById("site-name");
  const trustScoreText = document.getElementById("trust-score-text");
  const riskLevel = document.getElementById("risk-level");
  const riskTitle = document.getElementById("risk-title");
  const reasonsList = document.getElementById("reasons");
  const moreBtn = document.getElementById("more-btn");
  const backBtn = document.getElementById("back-btn");

  status.textContent = "Done.";
  status.classList.remove("error");
  result.classList.remove("hidden");
  frontView.classList.remove("hidden");
  backView.classList.add("hidden");

  siteName.textContent = data.website_name || "—";
  const score =
    typeof data.trust_score === "number" ? data.trust_score : null;

  trustScoreText.textContent = score === null ? "—" : `${score}%`;

  const risk = data.risk_level || "—";
  riskLevel.textContent = risk;
  riskTitle.textContent =
    risk === "—" ? "RISK UNKNOWN" : `${risk.toUpperCase()} WEBSITE`;

  styleRiskBanner(data.risk_level, score);
  showPurchaseCallout(data);

  reasonsList.innerHTML = "";
  const items = Array.isArray(data.reasons) ? data.reasons : [];
  items.forEach((r) => {
    const li = document.createElement("li");
    li.textContent = r;
    reasonsList.appendChild(li);
  });

  moreBtn.onclick = () => {
    frontView.classList.add("hidden");
    backView.classList.remove("hidden");
  };

  backBtn.onclick = () => {
    backView.classList.add("hidden");
    frontView.classList.remove("hidden");
  };
}

/**
 * Main flow: get active tab → fetch analyze API → render UI.
 */
async function main() {
  const status = document.getElementById("status");

  try {
    // Ask browser API for current tab URL (Firefox + Chrome compatible).
    const [tab] = await EXT_API.tabs.query({
      active: true,
      lastFocusedWindow: true,
    });

    if (!tab || !tab.url) {
      showError("Could not read the tab URL (try a normal web page).");
      return;
    }

    const url = tab.url;

    // Block special Chrome pages — they are not real shopping sites.
    if (
      url.startsWith("chrome://") ||
      url.startsWith("edge://") ||
      url.startsWith("about:")
    ) {
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
