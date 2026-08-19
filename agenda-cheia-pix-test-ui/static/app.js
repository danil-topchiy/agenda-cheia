const state = {
  config: null,
  currentCharge: null,
  events: [],
  selectedEventId: null,
};

const el = {
  pixApiBaseUrl: document.querySelector("#pixApiBaseUrl"),
  webhookUrl: document.querySelector("#webhookUrl"),
  copyWebhookUrl: document.querySelector("#copyWebhookUrl"),
  chargeForm: document.querySelector("#chargeForm"),
  createButton: document.querySelector("#createButton"),
  valueReais: document.querySelector("#valueReais"),
  expiresIn: document.querySelector("#expiresIn"),
  correlationID: document.querySelector("#correlationID"),
  comment: document.querySelector("#comment"),
  customerName: document.querySelector("#customerName"),
  customerEmail: document.querySelector("#customerEmail"),
  customerPhone: document.querySelector("#customerPhone"),
  chargeSubtitle: document.querySelector("#chargeSubtitle"),
  chargeStatus: document.querySelector("#chargeStatus"),
  qrBox: document.querySelector("#qrBox"),
  chargeValue: document.querySelector("#chargeValue"),
  chargeExpires: document.querySelector("#chargeExpires"),
  providerChargeID: document.querySelector("#providerChargeID"),
  paymentLinkUrl: document.querySelector("#paymentLinkUrl"),
  brCode: document.querySelector("#brCode"),
  copyBrCode: document.querySelector("#copyBrCode"),
  refreshCharge: document.querySelector("#refreshCharge"),
  simulatePaid: document.querySelector("#simulatePaid"),
  simulateExpired: document.querySelector("#simulateExpired"),
  eventList: document.querySelector("#eventList"),
  payloadView: document.querySelector("#payloadView"),
  clearEvents: document.querySelector("#clearEvents"),
  streamState: document.querySelector("#streamState"),
  toast: document.querySelector("#toast"),
};

function initCorrelationId() {
  el.correlationID.value = `agenda-${Date.now()}`;
}

async function loadConfig() {
  const config = await apiFetch("/api/config");
  state.config = config;
  el.pixApiBaseUrl.textContent = config.pixApiBaseUrl;
  el.webhookUrl.textContent = config.webhookUrl;
}

async function loadEvents() {
  state.events = await apiFetch("/api/webhook-events");
  renderEvents();
}

function startEventStream() {
  const source = new EventSource("/api/webhook-events/stream");
  source.addEventListener("ready", () => {
    el.streamState.textContent = "Conectado";
  });
  source.addEventListener("webhook", (message) => {
    const event = JSON.parse(message.data);
    state.events = [event, ...state.events.filter((item) => item.id !== event.id)];
    state.selectedEventId = event.id;
    renderEvents();
    showPayload(event);

    const correlationID = event.summary?.correlationID;
    if (state.currentCharge?.correlationID && correlationID === state.currentCharge.correlationID) {
      refreshCharge(false);
    }
  });
  source.onerror = () => {
    el.streamState.textContent = "Reconectando";
  };
}

el.chargeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  el.createButton.disabled = true;
  try {
    const payload = buildChargePayload();
    const charge = await apiFetch("/api/charges", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setCurrentCharge(charge);
    toast("Cobrança criada");
  } catch (error) {
    toast(error.message);
  } finally {
    el.createButton.disabled = false;
  }
});

el.refreshCharge.addEventListener("click", () => refreshCharge(true));
el.simulatePaid.addEventListener("click", () => simulateWebhook("COMPLETED"));
el.simulateExpired.addEventListener("click", () => simulateWebhook("EXPIRED"));
el.clearEvents.addEventListener("click", clearEvents);
el.copyWebhookUrl.addEventListener("click", () => copyText(state.config?.webhookUrl || ""));
el.copyBrCode.addEventListener("click", () => copyText(el.brCode.value));

async function refreshCharge(showToast) {
  if (!state.currentCharge?.correlationID) {
    toast("Nenhuma cobrança selecionada");
    return;
  }
  try {
    const charge = await apiFetch(`/api/charges/${encodeURIComponent(state.currentCharge.correlationID)}`);
    setCurrentCharge({ ...state.currentCharge, ...charge });
    if (showToast) toast("Status atualizado");
  } catch (error) {
    if (showToast) toast(error.message);
  }
}

async function simulateWebhook(status) {
  if (!state.currentCharge?.correlationID) {
    toast("Crie uma cobrança antes de simular");
    return;
  }
  try {
    const payload = {
      correlationID: state.currentCharge.correlationID,
      value: state.currentCharge.value || parseMoneyToCents(el.valueReais.value),
      status,
      providerChargeID: state.currentCharge.providerChargeID,
      paymentLinkID: state.currentCharge.paymentLinkID,
    };
    await apiFetch("/api/simulate-webhook", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    toast(status === "COMPLETED" ? "Pagamento simulado" : "Expiração simulada");
  } catch (error) {
    toast(error.message);
  }
}

async function clearEvents() {
  await apiFetch("/api/webhook-events", { method: "DELETE", expectJson: false });
  state.events = [];
  state.selectedEventId = null;
  renderEvents();
  el.payloadView.textContent = "{}";
}

function buildChargePayload() {
  return {
    value: parseMoneyToCents(el.valueReais.value),
    expiresIn: Number(el.expiresIn.value),
    correlationID: el.correlationID.value.trim(),
    comment: emptyToUndefined(el.comment.value),
    customerName: emptyToUndefined(el.customerName.value),
    customerEmail: emptyToUndefined(el.customerEmail.value),
    customerPhone: emptyToUndefined(el.customerPhone.value),
  };
}

function setCurrentCharge(charge) {
  const normalized = normalizeCharge(charge);
  state.currentCharge = normalized;
  renderCharge(normalized);
}

function normalizeCharge(charge) {
  return {
    correlationID: charge.correlationID,
    value: charge.value,
    status: charge.status,
    expiresIn: charge.expiresIn,
    expiresDate: charge.expiresDate,
    brCode: charge.brCode,
    qrCodeImage: charge.qrCodeImage,
    paymentLinkUrl: charge.paymentLinkUrl,
    providerChargeID: charge.providerChargeID,
    paymentLinkID: charge.paymentLinkID,
    paidAt: charge.paidAt,
    raw: charge.raw || charge,
  };
}

function renderCharge(charge) {
  el.chargeSubtitle.textContent = charge.correlationID || "Sem correlation ID";
  el.chargeStatus.textContent = charge.status || "UNKNOWN";
  el.chargeStatus.className = "status-pill";
  if (!charge.status || charge.status === "ACTIVE") el.chargeStatus.classList.add("muted");
  if (charge.status === "EXPIRED") el.chargeStatus.classList.add("expired");

  el.chargeValue.textContent = charge.value ? formatMoney(charge.value) : "-";
  el.chargeExpires.textContent = charge.expiresDate || (charge.expiresIn ? `${charge.expiresIn}s` : "-");
  el.providerChargeID.textContent = charge.providerChargeID || "-";

  if (charge.paymentLinkUrl) {
    el.paymentLinkUrl.textContent = charge.paymentLinkUrl;
    el.paymentLinkUrl.href = charge.paymentLinkUrl;
  } else {
    el.paymentLinkUrl.textContent = "-";
    el.paymentLinkUrl.removeAttribute("href");
  }

  el.brCode.value = charge.brCode || "";
  el.qrBox.innerHTML = "";
  if (charge.qrCodeImage) {
    const image = document.createElement("img");
    image.src = charge.qrCodeImage;
    image.alt = "QRCode Pix";
    el.qrBox.appendChild(image);
  } else {
    const placeholder = document.createElement("span");
    placeholder.textContent = "QR";
    el.qrBox.appendChild(placeholder);
  }
}

function renderEvents() {
  if (!state.events.length) {
    el.eventList.innerHTML = `<div class="event-item"><div class="event-meta">Nenhum webhook recebido</div></div>`;
    return;
  }

  el.eventList.innerHTML = "";
  for (const event of state.events) {
    const summary = event.summary || {};
    const button = document.createElement("button");
    button.type = "button";
    button.className = `event-item${state.selectedEventId === event.id ? " active" : ""}`;
    button.innerHTML = `
      <div class="event-title">
        <strong>${escapeHtml(summary.event || "Webhook")}</strong>
        <span>${escapeHtml(summary.status || "-")}</span>
      </div>
      <div class="event-meta">${escapeHtml(summary.correlationID || "-")}</div>
      <div class="event-meta">${escapeHtml(event.receivedAt || "")} · ${escapeHtml(event.source || "-")}</div>
    `;
    button.addEventListener("click", () => {
      state.selectedEventId = event.id;
      renderEvents();
      showPayload(event);
    });
    el.eventList.appendChild(button);
  }
}

function showPayload(event) {
  el.payloadView.textContent = JSON.stringify(event, null, 2);
}

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || "GET",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    body: options.body,
  });

  if (options.expectJson === false && response.ok) return null;

  const text = await response.text();
  let body = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!response.ok) {
    const detail = body?.detail || body || `HTTP ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return body;
}

function parseMoneyToCents(value) {
  const normalized = value.trim().replace(/\./g, "").replace(",", ".");
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error("Valor inválido");
  }
  return Math.round(parsed * 100);
}

function formatMoney(cents) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(cents / 100);
}

function emptyToUndefined(value) {
  const trimmed = value.trim();
  return trimmed || undefined;
}

async function copyText(value) {
  if (!value) return;
  await navigator.clipboard.writeText(value);
  toast("Copiado");
}

function toast(message) {
  el.toast.textContent = message;
  el.toast.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => {
    el.toast.hidden = true;
  }, 2600);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

initCorrelationId();
loadConfig().catch((error) => toast(error.message));
loadEvents().catch((error) => toast(error.message));
startEventStream();

