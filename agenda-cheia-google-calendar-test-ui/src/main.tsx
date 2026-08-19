import React, { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  Bell,
  CalendarClock,
  CalendarPlus,
  CheckCircle2,
  ClipboardList,
  KeyRound,
  ListFilter,
  LogIn,
  Play,
  Radio,
  RefreshCw,
  Save,
  Search,
  Send,
  Square,
  Trash2,
  Wifi,
  WifiOff
} from "lucide-react";
import "./styles.css";

type AppointmentState = "scheduled" | "confirmed" | "cancelled" | "completed" | "no_show";
type SendUpdates = "none" | "all" | "externalOnly";
type Source = "google" | "local";

type Appointment = {
  appointment_id: string;
  calendar_id: string;
  state: string;
  google_status?: string | null;
  summary?: string | null;
  description?: string | null;
  location?: string | null;
  start_at?: string | null;
  end_at?: string | null;
  time_zone?: string | null;
  html_link?: string | null;
  etag?: string | null;
  updated_at?: string | null;
  deleted: boolean;
};

type SyncRun = {
  calendar_id: string;
  full_sync: boolean;
  changes_count: number;
  next_sync_token_saved: boolean;
  changes: Array<{ change_type: string; appointment: Appointment }>;
};

type WatchChannel = {
  user_id?: string | null;
  calendar_id?: string | null;
  channel_id: string;
  resource_id: string;
  resource_uri?: string | null;
  expiration_ms?: number | null;
  token?: string | null;
  active: boolean;
};

type WebhookNotification = {
  id: number;
  user_id?: string | null;
  calendar_id?: string | null;
  channel_id?: string | null;
  resource_id?: string | null;
  resource_state?: string | null;
  resource_uri?: string | null;
  message_number?: string | null;
  channel_token?: string | null;
  received_at: string;
};

type RequestLog = {
  id: number;
  label: string;
  status: "ok" | "error";
  detail: string;
  at: string;
};

type OAuthLogin = {
  authorization_url: string;
  state: string;
  user_id: string;
  calendar_id: string;
};

type OAuthConnection = {
  user_id: string;
  google_email?: string | null;
  calendar_id: string;
  scopes: string[];
  connected: boolean;
  expiry?: string | null;
  updated_at?: string | null;
};

const states: AppointmentState[] = ["scheduled", "confirmed", "cancelled", "completed", "no_show"];
const sendUpdateOptions: SendUpdates[] = ["none", "all", "externalOnly"];
const defaultBaseUrl = "http://127.0.0.1:8001";

function App() {
  const [baseUrl, setBaseUrl] = useState(localStorage.getItem("calendarApiBaseUrl") || defaultBaseUrl);
  const [activeTab, setActiveTab] = useState<"oauth" | "appointments" | "sync" | "webhook" | "output">("oauth");
  const [authUserId, setAuthUserId] = useState(localStorage.getItem("calendarUserId") || "demo-user");
  const [authCalendarId, setAuthCalendarId] = useState(localStorage.getItem("calendarId") || "primary");
  const [health, setHealth] = useState<"idle" | "ok" | "error">("idle");
  const [busy, setBusy] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<unknown>(null);
  const [logs, setLogs] = useState<RequestLog[]>([]);

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [oauthConnections, setOauthConnections] = useState<OAuthConnection[]>([]);
  const [channels, setChannels] = useState<WatchChannel[]>([]);
  const [notifications, setNotifications] = useState<WebhookNotification[]>([]);
  const [streamOpen, setStreamOpen] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const [createForm, setCreateForm] = useState({
    summary: "Consulta teste",
    description: "Criado pela test UI",
    location: "",
    start_at: nextLocalDateTime(1),
    end_at: nextLocalDateTime(2),
    time_zone: "America/Sao_Paulo",
    state: "scheduled" as AppointmentState,
    attendee_email: "",
    attendee_name: "",
    send_updates: "none" as SendUpdates
  });

  const [updateForm, setUpdateForm] = useState({
    appointment_id: "",
    summary: "",
    description: "",
    location: "",
    start_at: "",
    end_at: "",
    state: "confirmed" as AppointmentState,
    calendar_status: "",
    send_updates: "none" as SendUpdates
  });

  const [listForm, setListForm] = useState({
    state: "" as "" | AppointmentState,
    source: "google" as Source,
    include_deleted: false,
    time_min: "",
    time_max: ""
  });

  const [watchForm, setWatchForm] = useState({
    address: "",
    token: "",
    ttl_seconds: "604800",
    channel_id: "",
    resource_id: ""
  });

  const [webhookForm, setWebhookForm] = useState({
    channel_id: "ui-test-channel",
    resource_id: "ui-test-resource",
    resource_state: "exists",
    message_number: "1",
    channel_token: ""
  });

  const normalizedBaseUrl = useMemo(() => normalizeBaseUrl(baseUrl), [baseUrl]);

  useEffect(() => {
    localStorage.setItem("calendarApiBaseUrl", baseUrl);
  }, [baseUrl]);

  useEffect(() => {
    localStorage.setItem("calendarUserId", authUserId);
  }, [authUserId]);

  useEffect(() => {
    localStorage.setItem("calendarId", authCalendarId);
  }, [authCalendarId]);

  useEffect(() => {
    checkHealth();
    return () => closeStream();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function callApi<T>(label: string, path: string, options: RequestInit = {}): Promise<T> {
    setBusy(label);
    try {
      const response = await fetch(`${normalizedBaseUrl}${path}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {})
        }
      });
      const text = await response.text();
      const body = text ? JSON.parse(text) : null;
      setLastResponse(body);
      if (!response.ok) {
        throw new Error(typeof body?.detail === "string" ? body.detail : text || response.statusText);
      }
      addLog(label, "ok", `${response.status} ${response.statusText}`);
      return body as T;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setLastResponse({ error: message });
      addLog(label, "error", message);
      throw error;
    } finally {
      setBusy(null);
    }
  }

  function addLog(label: string, status: RequestLog["status"], detail: string) {
    setLogs((current) => [
      {
        id: Date.now() + Math.random(),
        label,
        status,
        detail,
        at: new Date().toLocaleTimeString()
      },
      ...current.slice(0, 79)
    ]);
  }

  async function checkHealth() {
    try {
      await callApi("health", "/health", { method: "GET" });
      setHealth("ok");
    } catch {
      setHealth("error");
    }
  }

  function calendarPath(path: string, params: Record<string, string | number | boolean | undefined> = {}) {
    const [pathname, query = ""] = path.split("?");
    const search = new URLSearchParams(query);
    if (authUserId.trim()) search.set("user_id", authUserId.trim());
    if (authCalendarId.trim()) search.set("calendar_id", authCalendarId.trim());
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") search.set(key, String(value));
    });
    const queryString = search.toString();
    return queryString ? `${pathname}?${queryString}` : pathname;
  }

  async function startOAuth() {
    const result = await callApi<OAuthLogin>(
      "google oauth login",
      `/auth/google/login?${new URLSearchParams({
        user_id: authUserId.trim(),
        calendar_id: authCalendarId.trim() || "primary"
      }).toString()}`
    );
    window.open(result.authorization_url, "_blank", "noopener,noreferrer");
  }

  async function refreshOauthConnections() {
    const result = await callApi<OAuthConnection[]>("list oauth connections", "/auth/google/connections");
    setOauthConnections(result);
  }

  async function disconnectOAuth(userId: string) {
    await callApi("disconnect oauth", `/auth/google/connections/${encodeURIComponent(userId)}`, {
      method: "DELETE"
    });
    await refreshOauthConnections();
  }

  async function createAppointment(event: FormEvent) {
    event.preventDefault();
    const attendees = createForm.attendee_email
      ? [
          {
            email: createForm.attendee_email,
            display_name: createForm.attendee_name || undefined
          }
        ]
      : [];
    const body = pruneEmpty({
      summary: createForm.summary,
      description: createForm.description,
      location: createForm.location,
      start_at: createForm.start_at,
      end_at: createForm.end_at,
      time_zone: createForm.time_zone,
      state: createForm.state,
      attendees,
      send_updates: createForm.send_updates
    });
    const created = await callApi<Appointment>("create appointment", calendarPath("/appointments"), {
      method: "POST",
      body: JSON.stringify(body)
    });
    setUpdateForm((current) => ({ ...current, appointment_id: created.appointment_id }));
  }

  async function updateAppointment(event: FormEvent) {
    event.preventDefault();
    if (!updateForm.appointment_id.trim()) return;
    const body = pruneEmpty({
      summary: updateForm.summary,
      description: updateForm.description,
      location: updateForm.location,
      start_at: updateForm.start_at,
      end_at: updateForm.end_at,
      state: updateForm.state,
      calendar_status: updateForm.calendar_status,
      send_updates: updateForm.send_updates
    });
    await callApi<Appointment>(`update ${updateForm.appointment_id}`, calendarPath(`/appointments/${updateForm.appointment_id}`), {
      method: "PATCH",
      body: JSON.stringify(body)
    });
  }

  async function getAppointment() {
    if (!updateForm.appointment_id.trim()) return;
    const appointment = await callApi<Appointment>(`get ${updateForm.appointment_id}`, calendarPath(`/appointments/${updateForm.appointment_id}`));
    setAppointments([appointment]);
  }

  async function listAppointments(event?: FormEvent) {
    event?.preventDefault();
    const result = await callApi<Appointment[]>(
      "list appointments",
      calendarPath("/appointments", {
        state: listForm.state,
        source: listForm.source,
        include_deleted: listForm.include_deleted,
        time_min: listForm.time_min,
        time_max: listForm.time_max
      })
    );
    setAppointments(result);
  }

  async function pollSync(forceFull: boolean) {
    const result = await callApi<SyncRun>("poll sync", calendarPath("/sync/poll", { force_full: forceFull }), {
      method: "POST",
      body: JSON.stringify({})
    });
    setAppointments(result.changes.map((change) => change.appointment));
  }

  async function createWatch(event: FormEvent) {
    event.preventDefault();
    const body = pruneEmpty({
      address: watchForm.address,
      token: watchForm.token,
      ttl_seconds: watchForm.ttl_seconds ? Number(watchForm.ttl_seconds) : undefined
    });
    const created = await callApi<WatchChannel>("create watch", calendarPath("/sync/watch"), {
      method: "POST",
      body: JSON.stringify(body)
    });
    setWatchForm((current) => ({
      ...current,
      channel_id: created.channel_id,
      resource_id: created.resource_id
    }));
    await refreshChannels();
  }

  async function refreshChannels() {
    const result = await callApi<WatchChannel[]>("list watch channels", "/sync/watch");
    setChannels(result);
  }

  async function stopWatch() {
    const body = pruneEmpty({
      channel_id: watchForm.channel_id,
      resource_id: watchForm.resource_id
    });
    await callApi("stop watch", calendarPath("/sync/watch/stop"), {
      method: "POST",
      body: JSON.stringify(body)
    });
    await refreshChannels();
  }

  async function refreshNotifications() {
    const result = await callApi<WebhookNotification[]>("list webhook logs", "/webhooks/google-calendar/notifications?limit=100");
    setNotifications(result);
  }

  function openStream() {
    closeStream();
    const source = new EventSource(`${normalizedBaseUrl}/webhooks/google-calendar/stream`);
    eventSourceRef.current = source;
    source.addEventListener("ready", () => {
      setStreamOpen(true);
      addLog("webhook stream", "ok", "connected");
    });
    source.addEventListener("notification", (event) => {
      const item = JSON.parse((event as MessageEvent).data) as WebhookNotification;
      setNotifications((current) => [...current.filter((existing) => existing.id !== item.id), item].slice(-100));
    });
    source.onerror = () => {
      setStreamOpen(false);
      addLog("webhook stream", "error", "connection interrupted");
    };
  }

  function closeStream() {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setStreamOpen(false);
  }

  async function sendSyntheticWebhook(event: FormEvent) {
    event.preventDefault();
    const headers = pruneEmpty({
      "x-goog-channel-id": webhookForm.channel_id,
      "x-goog-resource-id": webhookForm.resource_id,
      "x-goog-resource-state": webhookForm.resource_state,
      "x-goog-message-number": webhookForm.message_number,
      "x-goog-channel-token": webhookForm.channel_token
    }) as Record<string, string>;
    await callApi("synthetic webhook", "/webhooks/google-calendar", {
      method: "POST",
      headers,
      body: JSON.stringify({})
    });
    setWebhookForm((current) => ({
      ...current,
      message_number: String(Number(current.message_number || "0") + 1)
    }));
    await refreshNotifications();
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Agenda Cheia</p>
          <h1>Google Calendar Test UI</h1>
        </div>
        <div className="api-control">
          <label htmlFor="baseUrl">API</label>
          <input id="baseUrl" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
          <label htmlFor="userId">User</label>
          <input id="userId" value={authUserId} onChange={(event) => setAuthUserId(event.target.value)} />
          <label htmlFor="calendarId">Calendar</label>
          <input id="calendarId" value={authCalendarId} onChange={(event) => setAuthCalendarId(event.target.value)} />
          <button className="iconButton" onClick={checkHealth} title="Checar health">
            <RefreshCw size={18} />
          </button>
          <StatusPill state={health} />
        </div>
      </header>

      <nav className="tabs" aria-label="Views">
        <TabButton active={activeTab === "oauth"} onClick={() => setActiveTab("oauth")} icon={<KeyRound size={18} />} label="OAuth" />
        <TabButton active={activeTab === "appointments"} onClick={() => setActiveTab("appointments")} icon={<CalendarClock size={18} />} label="Appointments" />
        <TabButton active={activeTab === "sync"} onClick={() => setActiveTab("sync")} icon={<Radio size={18} />} label="Sync / Watch" />
        <TabButton active={activeTab === "webhook"} onClick={() => setActiveTab("webhook")} icon={<Bell size={18} />} label="Webhooks" />
        <TabButton active={activeTab === "output"} onClick={() => setActiveTab("output")} icon={<ClipboardList size={18} />} label="Output" />
      </nav>

      {activeTab === "oauth" && (
        <section className="grid two">
          <Panel title="Conectar Google Calendar" icon={<KeyRound size={18} />}>
            <div className="form">
              <div className="formRow">
                <TextField label="User ID" value={authUserId} onChange={setAuthUserId} />
                <TextField label="Calendar ID" value={authCalendarId} onChange={setAuthCalendarId} />
              </div>
              <div className="buttonRow">
                <button className="primary" onClick={startOAuth}>
                  <LogIn size={17} />
                  Abrir consentimento
                </button>
                <button className="secondary" onClick={refreshOauthConnections}>
                  <RefreshCw size={17} />
                  Atualizar conexões
                </button>
              </div>
              <p className="muted">
                Depois do callback, use o mesmo User ID nas abas de appointments, sync e watch.
              </p>
            </div>
          </Panel>

          <Panel title="Conexões OAuth" icon={<ClipboardList size={18} />}>
            <OAuthConnectionsTable connections={oauthConnections} onDisconnect={disconnectOAuth} />
          </Panel>
        </section>
      )}

      {activeTab === "appointments" && (
        <section className="grid two">
          <Panel title="Criar appointment" icon={<CalendarPlus size={18} />}>
            <form className="form" onSubmit={createAppointment}>
              <TextField label="Resumo" value={createForm.summary} onChange={(value) => setCreateForm({ ...createForm, summary: value })} required />
              <TextArea label="Descricao" value={createForm.description} onChange={(value) => setCreateForm({ ...createForm, description: value })} />
              <TextField label="Local" value={createForm.location} onChange={(value) => setCreateForm({ ...createForm, location: value })} />
              <div className="formRow">
                <TextField type="datetime-local" label="Inicio" value={createForm.start_at} onChange={(value) => setCreateForm({ ...createForm, start_at: value })} required />
                <TextField type="datetime-local" label="Fim" value={createForm.end_at} onChange={(value) => setCreateForm({ ...createForm, end_at: value })} required />
              </div>
              <div className="formRow">
                <TextField label="Timezone" value={createForm.time_zone} onChange={(value) => setCreateForm({ ...createForm, time_zone: value })} />
                <SelectField label="Estado" value={createForm.state} options={states} onChange={(value) => setCreateForm({ ...createForm, state: value as AppointmentState })} />
              </div>
              <div className="formRow">
                <TextField label="Email convidado" value={createForm.attendee_email} onChange={(value) => setCreateForm({ ...createForm, attendee_email: value })} />
                <TextField label="Nome convidado" value={createForm.attendee_name} onChange={(value) => setCreateForm({ ...createForm, attendee_name: value })} />
              </div>
              <SelectField label="Send updates" value={createForm.send_updates} options={sendUpdateOptions} onChange={(value) => setCreateForm({ ...createForm, send_updates: value as SendUpdates })} />
              <button className="primary" disabled={busy === "create appointment"}>
                <Save size={17} />
                Criar
              </button>
            </form>
          </Panel>

          <Panel title="Atualizar / buscar" icon={<Search size={18} />}>
            <form className="form" onSubmit={updateAppointment}>
              <TextField label="Appointment ID" value={updateForm.appointment_id} onChange={(value) => setUpdateForm({ ...updateForm, appointment_id: value })} required />
              <TextField label="Resumo" value={updateForm.summary} onChange={(value) => setUpdateForm({ ...updateForm, summary: value })} />
              <TextArea label="Descricao" value={updateForm.description} onChange={(value) => setUpdateForm({ ...updateForm, description: value })} />
              <TextField label="Local" value={updateForm.location} onChange={(value) => setUpdateForm({ ...updateForm, location: value })} />
              <div className="formRow">
                <TextField type="datetime-local" label="Inicio" value={updateForm.start_at} onChange={(value) => setUpdateForm({ ...updateForm, start_at: value })} />
                <TextField type="datetime-local" label="Fim" value={updateForm.end_at} onChange={(value) => setUpdateForm({ ...updateForm, end_at: value })} />
              </div>
              <div className="formRow">
                <SelectField label="Estado" value={updateForm.state} options={states} onChange={(value) => setUpdateForm({ ...updateForm, state: value as AppointmentState })} />
                <SelectField label="Google status" value={updateForm.calendar_status} options={["", "confirmed", "tentative", "cancelled"]} onChange={(value) => setUpdateForm({ ...updateForm, calendar_status: value })} />
              </div>
              <SelectField label="Send updates" value={updateForm.send_updates} options={sendUpdateOptions} onChange={(value) => setUpdateForm({ ...updateForm, send_updates: value as SendUpdates })} />
              <div className="buttonRow">
                <button className="primary" disabled={busy?.startsWith("update")}>
                  <Save size={17} />
                  Atualizar
                </button>
                <button type="button" className="secondary" onClick={getAppointment}>
                  <Search size={17} />
                  Buscar
                </button>
              </div>
            </form>
          </Panel>

          <Panel title="Listar por estado" icon={<ListFilter size={18} />} wide>
            <form className="toolbar" onSubmit={listAppointments}>
              <SelectField label="Estado" value={listForm.state} options={["", ...states]} onChange={(value) => setListForm({ ...listForm, state: value as "" | AppointmentState })} />
              <SelectField label="Fonte" value={listForm.source} options={["google", "local"]} onChange={(value) => setListForm({ ...listForm, source: value as Source })} />
              <TextField type="datetime-local" label="Min" value={listForm.time_min} onChange={(value) => setListForm({ ...listForm, time_min: value })} />
              <TextField type="datetime-local" label="Max" value={listForm.time_max} onChange={(value) => setListForm({ ...listForm, time_max: value })} />
              <label className="checkbox">
                <input type="checkbox" checked={listForm.include_deleted} onChange={(event) => setListForm({ ...listForm, include_deleted: event.target.checked })} />
                Deleted
              </label>
              <button className="primary">
                <Search size={17} />
                Listar
              </button>
            </form>
            <AppointmentsTable appointments={appointments} />
          </Panel>
        </section>
      )}

      {activeTab === "sync" && (
        <section className="grid two">
          <Panel title="Polling incremental" icon={<RefreshCw size={18} />}>
            <div className="buttonRow">
              <button className="primary" onClick={() => pollSync(false)}>
                <Play size={17} />
                Poll
              </button>
              <button className="secondary" onClick={() => pollSync(true)}>
                <RefreshCw size={17} />
                Full sync
              </button>
            </div>
            <p className="muted">O resultado aparece em Output e a tabela recebe os appointments alterados.</p>
          </Panel>

          <Panel title="Watch channel" icon={<Radio size={18} />}>
            <form className="form" onSubmit={createWatch}>
              <TextField label="Webhook address HTTPS" placeholder="https://sua-api.com/webhooks/google-calendar" value={watchForm.address} onChange={(value) => setWatchForm({ ...watchForm, address: value })} />
              <div className="formRow">
                <TextField label="Token" value={watchForm.token} onChange={(value) => setWatchForm({ ...watchForm, token: value })} />
                <TextField label="TTL seconds" value={watchForm.ttl_seconds} onChange={(value) => setWatchForm({ ...watchForm, ttl_seconds: value })} />
              </div>
              <div className="buttonRow">
                <button className="primary">
                  <Radio size={17} />
                  Criar watch
                </button>
                <button type="button" className="secondary" onClick={refreshChannels}>
                  <RefreshCw size={17} />
                  Atualizar
                </button>
              </div>
            </form>
            <div className="form compact">
              <div className="formRow">
                <TextField label="Channel ID" value={watchForm.channel_id} onChange={(value) => setWatchForm({ ...watchForm, channel_id: value })} />
                <TextField label="Resource ID" value={watchForm.resource_id} onChange={(value) => setWatchForm({ ...watchForm, resource_id: value })} />
              </div>
              <button className="danger" onClick={stopWatch}>
                <Trash2 size={17} />
                Parar watch
              </button>
            </div>
          </Panel>

          <Panel title="Canais" icon={<Activity size={18} />} wide>
            <ChannelsTable channels={channels} />
          </Panel>
        </section>
      )}

      {activeTab === "webhook" && (
        <section className="grid two">
          <Panel title="Stream de logs" icon={streamOpen ? <Wifi size={18} /> : <WifiOff size={18} />}>
            <div className="buttonRow">
              <button className="primary" onClick={openStream}>
                <Wifi size={17} />
                Conectar
              </button>
              <button className="secondary" onClick={closeStream}>
                <Square size={17} />
                Pausar
              </button>
              <button className="secondary" onClick={refreshNotifications}>
                <RefreshCw size={17} />
                Histórico
              </button>
            </div>
            <p className="muted">Consome `GET /webhooks/google-calendar/stream` via EventSource.</p>
          </Panel>

          <Panel title="Webhook sintético" icon={<Send size={18} />}>
            <form className="form" onSubmit={sendSyntheticWebhook}>
              <div className="formRow">
                <TextField label="Channel ID" value={webhookForm.channel_id} onChange={(value) => setWebhookForm({ ...webhookForm, channel_id: value })} />
                <TextField label="Resource ID" value={webhookForm.resource_id} onChange={(value) => setWebhookForm({ ...webhookForm, resource_id: value })} />
              </div>
              <div className="formRow">
                <SelectField label="Resource state" value={webhookForm.resource_state} options={["sync", "exists", "not_exists"]} onChange={(value) => setWebhookForm({ ...webhookForm, resource_state: value })} />
                <TextField label="Message number" value={webhookForm.message_number} onChange={(value) => setWebhookForm({ ...webhookForm, message_number: value })} />
              </div>
              <TextField label="Channel token" value={webhookForm.channel_token} onChange={(value) => setWebhookForm({ ...webhookForm, channel_token: value })} />
              <button className="primary">
                <Send size={17} />
                Enviar webhook
              </button>
            </form>
          </Panel>

          <Panel title="Webhook logs" icon={<Bell size={18} />} wide>
            <WebhookTable notifications={notifications} />
          </Panel>
        </section>
      )}

      {activeTab === "output" && (
        <section className="grid two">
          <Panel title="Última resposta" icon={<ClipboardList size={18} />}>
            <pre className="json">{JSON.stringify(lastResponse, null, 2)}</pre>
          </Panel>
          <Panel title="Request log" icon={<Activity size={18} />}>
            <div className="requestLog">
              {logs.map((entry) => (
                <div className="logLine" key={entry.id}>
                  {entry.status === "ok" ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                  <span>{entry.at}</span>
                  <strong>{entry.label}</strong>
                  <small>{entry.detail}</small>
                </div>
              ))}
            </div>
          </Panel>
        </section>
      )}
    </main>
  );
}

function Panel({ title, icon, children, wide = false }: { title: string; icon: React.ReactNode; children: React.ReactNode; wide?: boolean }) {
  return (
    <section className={`panel ${wide ? "wide" : ""}`}>
      <div className="panelHeader">
        <span>{icon}</span>
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button className={`tab ${active ? "active" : ""}`} onClick={onClick}>
      {icon}
      {label}
    </button>
  );
}

function StatusPill({ state }: { state: "idle" | "ok" | "error" }) {
  return <span className={`status ${state}`}>{state === "ok" ? "online" : state === "error" ? "offline" : "idle"}</span>;
}

function TextField({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  placeholder = ""
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type={type} value={value} required={required} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function TextArea({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option || "todos"}
          </option>
        ))}
      </select>
    </label>
  );
}

function AppointmentsTable({ appointments }: { appointments: Appointment[] }) {
  return (
    <div className="tableWrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Estado</th>
            <th>Resumo</th>
            <th>Inicio</th>
            <th>Fim</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {appointments.map((appointment) => (
            <tr key={appointment.appointment_id}>
              <td className="mono">{appointment.appointment_id}</td>
              <td>{appointment.state}</td>
              <td>{appointment.summary || "-"}</td>
              <td>{formatDate(appointment.start_at)}</td>
              <td>{formatDate(appointment.end_at)}</td>
              <td>{appointment.google_status || "-"}</td>
            </tr>
          ))}
          {!appointments.length && (
            <tr>
              <td colSpan={6} className="empty">Sem appointments carregados.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function ChannelsTable({ channels }: { channels: WatchChannel[] }) {
  return (
    <div className="tableWrap">
      <table>
        <thead>
          <tr>
            <th>User</th>
            <th>Calendar</th>
            <th>Channel</th>
            <th>Resource</th>
            <th>Expira</th>
            <th>Ativo</th>
          </tr>
        </thead>
        <tbody>
          {channels.map((channel) => (
            <tr key={channel.channel_id}>
              <td>{channel.user_id || "-"}</td>
              <td className="mono">{channel.calendar_id || "-"}</td>
              <td className="mono">{channel.channel_id}</td>
              <td className="mono">{channel.resource_id}</td>
              <td>{channel.expiration_ms ? new Date(channel.expiration_ms).toLocaleString() : "-"}</td>
              <td>{channel.active ? "sim" : "nao"}</td>
            </tr>
          ))}
          {!channels.length && (
            <tr>
              <td colSpan={6} className="empty">Sem canais carregados.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function WebhookTable({ notifications }: { notifications: WebhookNotification[] }) {
  const rows = [...notifications].sort((a, b) => b.id - a.id);
  return (
    <div className="tableWrap webhookRows">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>User</th>
            <th>Calendar</th>
            <th>State</th>
            <th>Channel</th>
            <th>Resource</th>
            <th>Msg</th>
            <th>Recebido</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((notification) => (
            <tr key={notification.id}>
              <td>{notification.id}</td>
              <td>{notification.user_id || "-"}</td>
              <td className="mono">{notification.calendar_id || "-"}</td>
              <td>{notification.resource_state || "-"}</td>
              <td className="mono">{notification.channel_id || "-"}</td>
              <td className="mono">{notification.resource_id || "-"}</td>
              <td>{notification.message_number || "-"}</td>
              <td>{formatDate(notification.received_at)}</td>
            </tr>
          ))}
          {!rows.length && (
            <tr>
              <td colSpan={8} className="empty">Sem notificacoes.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function OAuthConnectionsTable({
  connections,
  onDisconnect
}: {
  connections: OAuthConnection[];
  onDisconnect: (userId: string) => void;
}) {
  return (
    <div className="tableWrap">
      <table>
        <thead>
          <tr>
            <th>User</th>
            <th>Email</th>
            <th>Calendar</th>
            <th>Expira</th>
            <th>Status</th>
            <th>Ação</th>
          </tr>
        </thead>
        <tbody>
          {connections.map((connection) => (
            <tr key={connection.user_id}>
              <td>{connection.user_id}</td>
              <td>{connection.google_email || "-"}</td>
              <td className="mono">{connection.calendar_id || "-"}</td>
              <td>{formatDate(connection.expiry)}</td>
              <td>{connection.connected ? "conectado" : "sem token"}</td>
              <td>
                <button className="danger small" onClick={() => onDisconnect(connection.user_id)}>
                  <Trash2 size={14} />
                  Remover
                </button>
              </td>
            </tr>
          ))}
          {!connections.length && (
            <tr>
              <td colSpan={6} className="empty">Sem conexões OAuth.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function normalizeBaseUrl(value: string) {
  return value.trim().replace(/\/+$/, "");
}

function pruneEmpty<T extends Record<string, unknown>>(value: T): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== "" && item !== undefined && item !== null)
  );
}

function nextLocalDateTime(hoursAhead: number) {
  const value = new Date(Date.now() + hoursAhead * 60 * 60 * 1000);
  value.setMinutes(0, 0, 0);
  const offset = value.getTimezoneOffset();
  const local = new Date(value.getTime() - offset * 60 * 1000);
  return local.toISOString().slice(0, 16);
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

createRoot(document.getElementById("root")!).render(<App />);
