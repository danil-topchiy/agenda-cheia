import type { Metadata } from "next";
import { DashboardClient } from "./components/dashboard-client";

export const metadata: Metadata = {
  title: "Agenda",
  description: "Acompanhe horários, confirmações e cancelamentos em uma única agenda.",
};

export default function DashboardPage() {
  return <DashboardClient />;
}
