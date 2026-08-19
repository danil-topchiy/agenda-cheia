export type BookingStatus = "Confirmado" | "Aguardando" | "Cancelado";

export type Booking = {
  id: number;
  day: "Hoje" | "Amanhã";
  time: string;
  customer: string;
  initials: string;
  service: string;
  professional: string;
  source: string;
  value: string;
  status: BookingStatus;
};

export const bookings: Booking[] = [
  { id: 1, day: "Hoje", time: "09:00", customer: "Marina Costa", initials: "MC", service: "Corte + escova", professional: "Juliana", source: "Google Agenda", value: "R$ 130", status: "Confirmado" },
  { id: 2, day: "Hoje", time: "10:30", customer: "Rafael Nunes", initials: "RN", service: "Corte masculino", professional: "Bruno", source: "Trinks", value: "R$ 70", status: "Confirmado" },
  { id: 3, day: "Hoje", time: "12:00", customer: "Larissa Melo", initials: "LM", service: "Manicure", professional: "Priscila", source: "Google Agenda", value: "R$ 55", status: "Aguardando" },
  { id: 4, day: "Hoje", time: "14:00", customer: "Camila Rocha", initials: "CR", service: "Corte feminino", professional: "Juliana", source: "AppBarber", value: "R$ 120", status: "Cancelado" },
  { id: 5, day: "Hoje", time: "15:30", customer: "Bruno Tavares", initials: "BT", service: "Barba", professional: "Bruno", source: "Trinks", value: "R$ 48", status: "Confirmado" },
  { id: 6, day: "Hoje", time: "16:30", customer: "Bianca Alves", initials: "BA", service: "Coloração", professional: "Juliana", source: "Google Agenda", value: "R$ 220", status: "Confirmado" },
  { id: 7, day: "Hoje", time: "18:00", customer: "Renato Freire", initials: "RF", service: "Corte + barba", professional: "Bruno", source: "Trinks", value: "R$ 110", status: "Confirmado" },
  { id: 8, day: "Hoje", time: "19:00", customer: "Fernanda Reis", initials: "FR", service: "Escova", professional: "Juliana", source: "Google Agenda", value: "R$ 96", status: "Cancelado" },
  { id: 9, day: "Amanhã", time: "09:30", customer: "Paula Gama", initials: "PG", service: "Corte feminino", professional: "Juliana", source: "Google Agenda", value: "R$ 120", status: "Confirmado" },
  { id: 10, day: "Amanhã", time: "11:00", customer: "Caio Bernardes", initials: "CB", service: "Corte masculino", professional: "Bruno", source: "AppBarber", value: "R$ 70", status: "Aguardando" },
  { id: 11, day: "Amanhã", time: "14:30", customer: "Nina Prado", initials: "NP", service: "Manicure", professional: "Priscila", source: "Trinks", value: "R$ 55", status: "Confirmado" },
];

export type Customer = {
  id: number;
  name: string;
  initials: string;
  phone: string;
  email: string;
  favoriteService: string;
  source: string;
  visits: number;
  lastVisit: string;
  nextBooking: string;
  segment: "Ativo" | "Lista de espera" | "Sem retorno";
};

export const customers: Customer[] = [
  { id: 1, name: "Marina Costa", initials: "MC", phone: "+55 11 99824-1741", email: "marina.costa@email.com", favoriteService: "Corte + escova", source: "Google Agenda", visits: 7, lastVisit: "8 ago 2026", nextBooking: "Hoje, 09:00", segment: "Ativo" },
  { id: 2, name: "Rafael Nunes", initials: "RN", phone: "+55 11 99143-8820", email: "rafael.nunes@email.com", favoriteService: "Corte masculino", source: "Trinks", visits: 11, lastVisit: "2 ago 2026", nextBooking: "Hoje, 10:30", segment: "Ativo" },
  { id: 3, name: "Larissa Melo", initials: "LM", phone: "+55 11 98310-4702", email: "larissa.melo@email.com", favoriteService: "Manicure", source: "Google Agenda", visits: 4, lastVisit: "21 jul 2026", nextBooking: "Hoje, 12:00", segment: "Ativo" },
  { id: 4, name: "Camila Rocha", initials: "CR", phone: "+55 11 99570-3168", email: "camila.rocha@email.com", favoriteService: "Corte feminino", source: "AppBarber", visits: 3, lastVisit: "17 jul 2026", nextBooking: "Nenhum", segment: "Sem retorno" },
  { id: 5, name: "Bruno Tavares", initials: "BT", phone: "+55 11 98846-9251", email: "bruno.tavares@email.com", favoriteService: "Barba", source: "Trinks", visits: 9, lastVisit: "10 ago 2026", nextBooking: "Hoje, 15:30", segment: "Ativo" },
  { id: 6, name: "Nina Prado", initials: "NP", phone: "+55 11 99662-5419", email: "nina.prado@email.com", favoriteService: "Manicure", source: "Trinks", visits: 5, lastVisit: "5 ago 2026", nextBooking: "Amanhã, 14:30", segment: "Lista de espera" },
  { id: 7, name: "Paula Gama", initials: "PG", phone: "+55 11 98740-6033", email: "paula.gama@email.com", favoriteService: "Corte feminino", source: "Google Agenda", visits: 6, lastVisit: "28 jul 2026", nextBooking: "Amanhã, 09:30", segment: "Ativo" },
  { id: 8, name: "Caio Bernardes", initials: "CB", phone: "+55 11 99315-2077", email: "caio.bernardes@email.com", favoriteService: "Corte masculino", source: "AppBarber", visits: 2, lastVisit: "14 jun 2026", nextBooking: "Amanhã, 11:00", segment: "Lista de espera" },
];
