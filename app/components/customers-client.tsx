"use client";

import { useMemo, useState } from "react";
import { MagnifyingGlass, UploadSimple, UsersThree } from "@phosphor-icons/react";
import { AppShell } from "./app-shell";
import { SourceModal } from "./source-modal";
import { customers } from "../data";

type CustomerFilter = "Todos" | "Ativo" | "Lista de espera" | "Sem retorno";

export function CustomersClient({ userName }: { userName: string }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<CustomerFilter>("Todos");
  const [modalOpen, setModalOpen] = useState(false);

  const visibleCustomers = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("pt-BR");
    return customers.filter((customer) => {
      const matchesFilter = filter === "Todos" || customer.segment === filter;
      const matchesQuery = !normalizedQuery || [customer.name, customer.phone, customer.email, customer.favoriteService]
        .some((value) => value.toLocaleLowerCase("pt-BR").includes(normalizedQuery));
      return matchesFilter && matchesQuery;
    });
  }, [filter, query]);

  return (
    <AppShell active="customers" userName={userName}>
      <header className="page-header">
        <div>
          <p className="page-date">Base unificada</p>
          <h1>Clientes</h1>
          <p className="page-subtitle">Histórico e preferências importados das suas fontes.</p>
        </div>
        <button className="primary-button" onClick={() => setModalOpen(true)}>
          <UploadSimple aria-hidden="true" />
          Importar clientes
        </button>
      </header>

      <section className="metric-strip customer-metrics" aria-label="Resumo da base de clientes">
        <article><span>Total de clientes</span><strong>142</strong><small>8 exibidos na demonstração</small></article>
        <article><span>Ativos nos últimos 90 dias</span><strong>118</strong><small>83% da base</small></article>
        <article><span>Lista de espera</span><strong>12</strong><small>prontos para um encaixe</small></article>
      </section>

      <section className="panel customers-panel">
        <div className="customer-toolbar">
          <label className="search-field">
            <span className="sr-only">Buscar clientes</span>
            <MagnifyingGlass aria-hidden="true" />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por nome, contato ou serviço" />
          </label>
          <label className="select-field">
            <span className="sr-only">Filtrar clientes</span>
            <select value={filter} onChange={(event) => setFilter(event.target.value as CustomerFilter)}>
              <option>Todos</option>
              <option>Ativo</option>
              <option>Lista de espera</option>
              <option>Sem retorno</option>
            </select>
          </label>
        </div>

        <div className="customer-table" role="table" aria-label="Clientes importados">
          <div className="customer-table-head" role="row">
            <span role="columnheader">Cliente</span>
            <span role="columnheader">Serviço frequente</span>
            <span role="columnheader">Origem</span>
            <span role="columnheader">Visitas</span>
            <span role="columnheader">Próximo horário</span>
            <span role="columnheader">Situação</span>
          </div>
          {visibleCustomers.length > 0 ? visibleCustomers.map((customer) => (
            <div className="customer-row" role="row" key={customer.id}>
              <div className="customer-identity" role="cell">
                <span className="avatar">{customer.initials}</span>
                <div><strong>{customer.name}</strong><a href={`tel:${customer.phone.replace(/\D/g, "")}`}>{customer.phone}</a></div>
              </div>
              <div className="customer-cell" role="cell" data-label="Serviço"><strong>{customer.favoriteService}</strong><span>Última visita: {customer.lastVisit}</span></div>
              <div className="customer-cell" role="cell" data-label="Origem"><span>{customer.source}</span></div>
              <div className="customer-cell numeric" role="cell" data-label="Visitas"><strong>{customer.visits}</strong></div>
              <div className="customer-cell" role="cell" data-label="Próximo horário"><strong>{customer.nextBooking}</strong></div>
              <div className="customer-cell" role="cell" data-label="Situação"><span className={`segment-badge segment-${customer.segment.toLowerCase().replaceAll(" ", "-")}`}>{customer.segment}</span></div>
            </div>
          )) : (
            <div className="empty-state customer-empty">
              <UsersThree aria-hidden="true" />
              <strong>Nenhum cliente encontrado</strong>
              <span>Tente outro termo ou limpe os filtros.</span>
              <button className="text-button" onClick={() => { setQuery(""); setFilter("Todos"); }}>Limpar busca</button>
            </div>
          )}
        </div>
        <footer className="table-footer"><span>{visibleCustomers.length} clientes exibidos</span><span>Dados de demonstração</span></footer>
      </section>

      <SourceModal open={modalOpen} onClose={() => setModalOpen(false)} mode="customers" />
    </AppShell>
  );
}
