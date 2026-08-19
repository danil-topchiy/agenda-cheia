import type { Metadata } from "next";
import { CustomersClient } from "../components/customers-client";

export const metadata: Metadata = {
  title: "Clientes",
  description: "Consulte clientes, histórico e preferências importados das suas fontes.",
};

export default function CustomersPage() {
  return <CustomersClient />;
}
