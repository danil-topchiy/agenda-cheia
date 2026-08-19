"use client";

import type { ReactNode } from "react";
import { CalendarCheck, UsersThree, PlugsConnected, Bell, SignOut } from "@phosphor-icons/react";
import Link from "next/link";

type AppShellProps = {
  active: "agenda" | "customers";
  children: ReactNode;
  userName: string;
};

function initials(value: string) {
  const parts = value.trim().split(/\s+/).filter(Boolean);
  return (parts.length > 1 ? `${parts[0][0]}${parts.at(-1)?.[0]}` : parts[0]?.slice(0, 2))
    ?.toLocaleUpperCase("pt-BR") || "AC";
}

export function AppShell({ active, children, userName }: AppShellProps) {
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
          <span className="avatar avatar-owner">{initials(userName)}</span>
          <div className="account-copy"><strong>{userName}</strong><small>Conta registrada</small></div>
          <a className="icon-button subtle" href="/signout-with-chatgpt?return_to=%2F" aria-label="Sair da conta"><SignOut aria-hidden="true" /></a>
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
