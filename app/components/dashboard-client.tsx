"use client";

import { useMemo, useState } from "react";
import { ArrowsClockwise, CalendarBlank, CheckCircle, Clock, PlugsConnected, WarningCircle } from "@phosphor-icons/react";
import { AppShell } from "./app-shell";
import { SourceModal } from "./source-modal";
import { bookings, type BookingStatus } from "../data";

const statusFilters: Array<"Todos" | BookingStatus> = ["Todos", "Confirmado", "Aguardando", "Cancelado"];

export function DashboardClient() {
  const [day, setDay] = useState<"Hoje" | "Amanhã" | "Semana">("Hoje");
  const [status, setStatus] = useState<"Todos" | BookingStatus>("Todos");
  const [modalOpen, setModalOpen] = useState(false);

  const visibleBookings = useMemo(() => {
    const byDay = day === "Semana" ? bookings : bookings.filter((booking) => booking.day === day);
    return status === "Todos" ? byDay : byDay.filter((booking) => booking.status === status);
  }, [day, status]);

  const today = bookings.filter((booking) => booking.day === "Hoje");
  const confirmedCount = today.filter((booking) => booking.status === "Confirmado").length;
  const cancelled = today.filter((booking) => booking.status === "Cancelado");

  return (
    <AppShell active="agenda">
      <header className="page-header">
        <div>
          <p className="page-date">Quarta-feira, 19 de agosto</p>
          <h1>Agenda</h1>
          <p className="page-subtitle">Seus horários, cancelamentos e fontes em um só lugar.</p>
        </div>
        <button className="primary-button" onClick={() => setModalOpen(true)}>
          <PlugsConnected aria-hidden="true" />
          Conectar fonte
        </button>
      </header>

      <div className="demo-notice" role="note">
        <span className="notice-icon"><ArrowsClockwise aria-hidden="true" /></span>
        <div><strong>Dados de demonstração</strong><span>Conecte seu Google Agenda ou CRM para importar horários reais.</span></div>
        <button onClick={() => setModalOpen(true)}>Ver fontes</button>
      </div>

      <section className="metric-strip" aria-label="Resumo de hoje">
        <article><span>Agendamentos hoje</span><strong>{today.length}</strong><small>3 profissionais</small></article>
        <article><span>Confirmados</span><strong>{confirmedCount}</strong><small>{Math.round((confirmedCount / today.length) * 100)}% da agenda</small></article>
        <article className="danger-metric"><span>Cancelados</span><strong>{cancelled.length}</strong><small>R$ 216 em risco</small></article>
        <article><span>Fontes conectadas</span><strong>0</strong><small>usando dados de exemplo</small></article>
      </section>

      <div className="dashboard-grid">
        <section className="panel schedule-panel">
          <div className="panel-heading schedule-heading">
            <div>
              <h2>Próximos horários</h2>
              <p>{visibleBookings.length} agendamentos exibidos</p>
            </div>
            <div className="segmented-control" aria-label="Período da agenda">
              {(["Hoje", "Amanhã", "Semana"] as const).map((item) => (
                <button className={day === item ? "selected" : ""} onClick={() => setDay(item)} key={item} aria-pressed={day === item}>{item}</button>
              ))}
            </div>
          </div>

          <div className="filter-row" aria-label="Filtrar por status">
            {statusFilters.map((item) => (
              <button className={status === item ? "active" : ""} onClick={() => setStatus(item)} key={item} aria-pressed={status === item}>
                {item === "Confirmado" ? "Confirmados" : item === "Cancelado" ? "Cancelados" : item}
              </button>
            ))}
          </div>

          <div className="booking-list">
            {visibleBookings.length > 0 ? visibleBookings.map((booking) => (
              <article className={`booking-row status-${booking.status.toLowerCase()}`} key={booking.id}>
                <time><strong>{booking.time}</strong><span>{booking.day}</span></time>
                <span className="avatar">{booking.initials}</span>
                <div className="booking-person"><strong>{booking.customer}</strong><span>{booking.service} com {booking.professional}</span></div>
                <div className="booking-source"><span>{booking.source}</span><strong>{booking.value}</strong></div>
                <span className={`status-badge status-${booking.status.toLowerCase()}`}>{booking.status}</span>
              </article>
            )) : (
              <div className="empty-state">
                <CalendarBlank aria-hidden="true" />
                <strong>Nenhum horário neste filtro</strong>
                <span>Escolha outro período ou status para continuar.</span>
                <button className="text-button" onClick={() => setStatus("Todos")}>Limpar filtro</button>
              </div>
            )}
          </div>
        </section>

        <aside className="side-stack">
          <section className="panel cancellation-panel">
            <div className="panel-heading"><div><h2>Cancelamentos</h2><p>Ocorridos hoje</p></div><WarningCircle aria-hidden="true" /></div>
            <div className="cancellation-list">
              {cancelled.map((booking) => (
                <article key={booking.id}>
                  <div><strong>{booking.time} · {booking.customer}</strong><span>{booking.service}</span></div>
                  <strong>{booking.value}</strong>
                </article>
              ))}
            </div>
            <button className="secondary-button full-button" onClick={() => setStatus("Cancelado")}>Ver cancelados</button>
          </section>

          <section className="panel source-summary">
            <div className="panel-heading"><div><h2>Fontes</h2><p>Última sincronização</p></div><Clock aria-hidden="true" /></div>
            <div className="source-summary-row"><span className="source-mini google">G</span><div><strong>Google Agenda</strong><span>Aguardando conexão</span></div></div>
            <div className="source-summary-row"><span className="source-mini crm">T</span><div><strong>CRM</strong><span>Aguardando conexão</span></div></div>
            <button className="text-button" onClick={() => setModalOpen(true)}>Configurar fontes</button>
          </section>

          <section className="quiet-summary" aria-label="Saúde da agenda">
            <CheckCircle aria-hidden="true" weight="fill" />
            <div><strong>5 horários confirmados</strong><span>Próximo atendimento às 09:00.</span></div>
          </section>
        </aside>
      </div>

      <SourceModal open={modalOpen} onClose={() => setModalOpen(false)} mode="agenda" />
    </AppShell>
  );
}
