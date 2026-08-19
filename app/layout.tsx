import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { headers } from "next/headers";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const baseUrl = new URL(`${protocol}://${host}`);
  const description = "Acompanhe agendamentos, cancelamentos e clientes em uma visão simples.";

  return {
    metadataBase: baseUrl,
    title: {
      default: "Agenda Cheia | Sua agenda em um só lugar",
      template: "%s | Agenda Cheia",
    },
    description,
    icons: {
      icon: "/favicon.svg",
      shortcut: "/favicon.svg",
    },
    openGraph: {
      title: "Agenda Cheia | Sua agenda em um só lugar",
      description,
      type: "website",
      locale: "pt_BR",
      images: [{ url: new URL("/og.png", baseUrl).toString(), width: 1792, height: 938, alt: "Agenda Cheia: sua agenda, sob controle." }],
    },
    twitter: {
      card: "summary_large_image",
      title: "Agenda Cheia | Sua agenda em um só lugar",
      description,
      images: [new URL("/og.png", baseUrl).toString()],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
