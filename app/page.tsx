const bookings = [
  { time: "09:00", customer: "Marina Costa", service: "Corte + escova", status: "Confirmado" },
  { time: "11:30", customer: "Rafael Nunes", service: "Corte masculino", status: "Confirmado" },
  { time: "14:00", customer: "Camila Rocha", service: "Manicure", status: "Cancelado" },
  { time: "16:30", customer: "Bianca Alves", service: "Coloração", status: "Confirmado" },
];

export default function Dashboard() {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="Agenda Cheia">
          <span className="brand-mark">A</span>
          <span>Agenda Cheia</span>
        </a>
        <nav className="side-nav" aria-label="Navegação principal">
          <a className="nav-item active" href="/">Agenda</a>
          <a className="nav-item" href="/customers">Clientes</a>
        </nav>
        <div className="sidebar-footer">
          <span className="avatar">JS</span>
          <div><strong>Juliana Silva</strong><small>Salão da Ju</small></div>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Quarta-feira, 19 de agosto</p>
            <h1>Bom dia, Ju.</h1>
          </div>
          <button className="primary-button">Importar agenda</button>
        </header>

        <div className="notice">
          <strong>Dados de demonstração</strong>
          <span>Conecte seu Google Agenda ou CRM para importar seus horários reais.</span>
        </div>

        <section className="metrics" aria-label="Resumo de hoje">
          <article><span>Agendamentos</span><strong>8</strong><small>para hoje</small></article>
          <article><span>Confirmados</span><strong>6</strong><small>75% da agenda</small></article>
          <article><span>Cancelados</span><strong>2</strong><small>R$ 216 em risco</small></article>
        </section>

        <section className="schedule-section">
          <div className="section-heading">
            <div><h2>Agenda de hoje</h2><p>4 de 8 horários exibidos</p></div>
            <button className="secondary-button">Ver agenda completa</button>
          </div>
          <div className="booking-list">
            {bookings.map((booking) => (
              <article className={`booking-row ${booking.status === "Cancelado" ? "cancelled" : ""}`} key={booking.time}>
                <time>{booking.time}</time>
                <div className="booking-person"><strong>{booking.customer}</strong><span>{booking.service}</span></div>
                <span className="status">{booking.status}</span>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
