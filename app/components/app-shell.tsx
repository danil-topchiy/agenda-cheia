"use client";

import type { ReactNode } from "react";
import { CalendarCheck, UsersThree, PlugsConnected, Bell, CaretDown } from "@phosphor-icons/react";
import Link from "next/link";

type AppShellProps = {
  active: "agenda" | "customers";
  children: ReactNode;
};

export function AppShell({ active, children }: AppShellProps) {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="Agenda Cheia, página inicial">
          <span className="brand-mark"><CalendarCheck aria-hidden="true" weight="bold" /></span>
          <span>Agenda Cheia</span>
        </Link>

        <nav className="side-nav" aria-label="Navegação principal">
          <Link className={`nav-item ${active === "agenda" ? "active" : ""}`} href="/" aria-current={active === "agenda" ? "page" : undefined}>
            <CalendarCheck aria-hidden="true" />
            <span>Agenda</span>
          </Link>
          <Link className={`nav-item ${active === "customers" ? "active" : ""}`} href="/customers" aria-current={active === "customers" ? "page" : undefined}>
            <UsersThree aria-hidden="true" />
            <span>Clientes</span>
          </Link>
        </nav>

        <div className="sync-card">
          <span className="sync-icon"><PlugsConnected aria-hidden="true" /></span>
          <div>
            <strong>Modo demonstração</strong>
            <span>Fontes ainda não conectadas</span>
          </div>
        </div>

        <div className="sidebar-footer">
          <span className="avatar avatar-owner">JS</span>
          <div className="account-copy"><strong>Juliana Silva</strong><small>Salão da Ju</small></div>
          <button className="icon-button subtle" aria-label="Abrir menu da conta"><CaretDown aria-hidden="true" /></button>
        </div>
      </aside>

      <section className="workspace">
        <div className="mobile-topbar">
          <Link className="brand" href="/" aria-label="Agenda Cheia, página inicial">
            <span className="brand-mark"><CalendarCheck aria-hidden="true" weight="bold" /></span>
            <span>Agenda Cheia</span>
          </Link>
          <button className="icon-button" aria-label="Notificações"><Bell aria-hidden="true" /></button>
        </div>
        {children}
      </section>
    </main>
  );
}
