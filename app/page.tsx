import type { Metadata } from "next";
import { requireChatGPTUser } from "./chatgpt-auth";
import { DashboardClient } from "./components/dashboard-client";
import { registerUser } from "../db/users";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Agenda",
  description: "Acompanhe horários, confirmações e cancelamentos em uma única agenda.",
};

export default async function DashboardPage() {
  const user = await requireChatGPTUser("/");
  await registerUser({
    id: user.userId,
    email: user.email,
    name: user.fullName,
  });

  return <DashboardClient userName={user.displayName} />;
}
