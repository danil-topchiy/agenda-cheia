import type { Metadata } from "next";
import { requireChatGPTUser } from "../chatgpt-auth";
import { CustomersClient } from "../components/customers-client";
import { registerUser } from "../../db/users";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Clientes",
  description: "Consulte clientes, histórico e preferências importados das suas fontes.",
};

export default async function CustomersPage() {
  const user = await requireChatGPTUser("/customers");
  await registerUser({
    id: user.userId,
    email: user.email,
    name: user.fullName,
  });

  return <CustomersClient userName={user.displayName} />;
}
