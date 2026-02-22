/**
 * app.js – KreaImgGen frontend helpers
 * Handles: JWT storage, authenticated fetch, UI guards, generate form.
 */

const API_BASE = "/api/v1";
const POLL_INTERVAL_MS = 3000;
const POLL_MAX_ATTEMPTS = 100; // ~5 minutes

// ── JWT helpers ──────────────────────────────────────────────────────────────

function getToken() {
  return localStorage.getItem("jwt_token");
}

function logout() {
  localStorage.removeItem("jwt_token");
  window.location.href = "login.html";
}

/**
 * Authenticated fetch wrapper.
 * Automatically attaches Authorization header and redirects on 401.
 */
async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    logout();          // redirects – nothing below this runs in practice
    return null;
  }
  return res;
}

// ── Decode JWT (no verification – display only) ──────────────────────────────

function parseJwtPayload(token) {
  try {
    const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(b64));
  } catch {
    return null;
  }
}

// ── Page-load init ───────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  const token = getToken();

  const navAuth = document.getElementById("nav-auth");
  const navUser = document.getElementById("nav-user");
  const navUsername = document.getElementById("nav-username");
  const authMsg = document.getElementById("auth-required-msg");
  const generateForm = document.getElementById("generate-form");

  if (token) {
    const payload = parseJwtPayload(token);
    // Expired?
    if (payload && payload.exp && Date.now() / 1000 > payload.exp) {
      logout();
      return;
    }
    if (navAuth) navAuth.classList.add("d-none");
    if (navUser) navUser.classList.remove("d-none");
    if (navUsername && payload) navUsername.textContent = `👤 ${payload.sub}`;
    if (generateForm) generateForm.classList.remove("d-none");
    if (authMsg) authMsg.classList.add("d-none");
  } else {
    if (authMsg) authMsg.classList.remove("d-none");
  }

  // Attach generate form handler only on index page
  if (generateForm) {
    generateForm.addEventListener("submit", handleGenerate);
  }
});

// ── Generate flow ─────────────────────────────────────────────────────────────

async function handleGenerate(e) {
  e.preventDefault();

  const spinner   = document.getElementById("spinner");
  const spinnerMsg = document.getElementById("spinner-msg");
  const resultArea = document.getElementById("result-area");
  const resultImg  = document.getElementById("result-img");
  const dlLink     = document.getElementById("download-link");
  const errMsg     = document.getElementById("error-msg");

  resultArea.classList.add("d-none");
  errMsg.classList.add("d-none");
  spinner.style.display = "flex";
  spinnerMsg.textContent = "Queuing your request…";

  const payload = {
    prompt:               document.getElementById("prompt").value,
    negative_prompt:      document.getElementById("neg-prompt").value || null,
    width:                parseInt(document.getElementById("width").value),
    height:               parseInt(document.getElementById("height").value),
    num_inference_steps:  parseInt(document.getElementById("steps").value),
    guidance_scale:       parseFloat(document.getElementById("guidance").value),
  };

  try {
    // ── Submit task ──────────────────────────────────────────────────────────
    const submitRes = await authFetch(`${API_BASE}/generate`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });
    if (!submitRes) return;  // redirected to login
    if (!submitRes.ok) {
      const detail = (await safeJson(submitRes)).detail || "Submission failed";
      throw new Error(detail);
    }
    const { task_id } = await safeJson(submitRes);

    // ── Poll for result ──────────────────────────────────────────────────────
    spinnerMsg.textContent = "Generating image… (this may take up to 2 minutes)";
    const imageUrl = await pollTask(task_id);

    resultImg.src = imageUrl;
    dlLink.href   = imageUrl;
    resultArea.classList.remove("d-none");
  } catch (err) {
    errMsg.textContent = `Error: ${err.message}`;
    errMsg.classList.remove("d-none");
  } finally {
    spinner.style.display = "none";
  }
}

async function pollTask(taskId) {
  let transientErrors = 0;
  const MAX_TRANSIENT = 5;  // tolerate up to 5 consecutive 502/503/504s before giving up

  for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt++) {
    await sleep(POLL_INTERVAL_MS);

    const res = await authFetch(`${API_BASE}/generate/status/${taskId}`);
    if (!res) return null;  // redirected to login

    // Transient upstream errors – retry rather than abort
    if (res.status === 502 || res.status === 503 || res.status === 504) {
      transientErrors++;
      if (transientErrors >= MAX_TRANSIENT) {
        throw new Error(`Server unreachable after ${MAX_TRANSIENT} retries (${res.status} ${res.statusText})`);
      }
      continue;
    }
    transientErrors = 0;  // reset on any non-transient response

    if (!res.ok) {
      const detail = (await safeJson(res)).detail || "Failed to check task status";
      throw new Error(detail);
    }

    const data = await safeJson(res);

    if (data.status === "success") {
      const urls = data.result?.image_urls;
      if (!urls || !urls.length) throw new Error("No images returned");
      return urls[0];
    }
    if (data.status === "failure") {
      throw new Error(data.error || "Task failed on the server");
    }
    // states: pending, started, progress → keep polling
  }
  throw new Error("Task timed out after waiting too long. Please try again.");
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Safely parse JSON from a Response. Falls back to HTTP status text when the
 * body is not valid JSON (e.g. nginx 502/504 HTML error pages).
 */
async function safeJson(res) {
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try { return await res.json(); } catch { /* fall through */ }
  }
  return { detail: `${res.status} ${res.statusText}` };
}
