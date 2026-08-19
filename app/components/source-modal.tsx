"use client";

import { useEffect } from "react";
import { CalendarBlank, Database, GoogleLogo, Info, X } from "@phosphor-icons/react";

type SourceModalProps = {
  open: boolean;
  onClose: () => void;
  mode: "agenda" | "customers";
};

const sources = [
  { name: "Google Agenda", copy: "Calendários e eventos", icon: GoogleLogo },
  { name: "Trinks", copy: "Agenda e cadastro de clientes", icon: CalendarBlank },
  { name: "AppBarber", copy: "Reservas e histórico", icon: Database },
];

export function SourceModal({ open, onClose, mode }: SourceModalProps) {
  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="source-modal" role="dialog" aria-modal="true" aria-labelledby="source-title">
        <div className="modal-heading">
          <div>
            <span className="modal-kicker">Integrações</span>
            <h2 id="source-title">Conectar {mode === "agenda" ? "uma agenda" : "uma fonte de clientes"}</h2>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Fechar"><X aria-hidden="true" /></button>
        </div>

        <div className="source-list">
          {sources.map(({ name, copy, icon: Icon }) => (
            <div className="source-option" key={name}>
              <span className="source-logo"><Icon aria-hidden="true" weight="bold" /></span>
              <div><strong>{name}</strong><span>{copy}</span></div>
              <span className="coming-soon">Em breve</span>
            </div>
          ))}
        </div>

        <div className="modal-note">
          <Info aria-hidden="true" />
          <p>Este primeiro MVP usa dados de demonstração. As conexões reais entram na próxima etapa.</p>
        </div>
        <button className="primary-button full-button" onClick={onClose}>Continuar no modo demonstração</button>
      </section>
    </div>
  );
}
