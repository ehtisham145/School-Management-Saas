import type { ReactNode } from "react";
import { IBM_Plex_Mono, IBM_Plex_Sans, IBM_Plex_Serif } from "next/font/google";
import { setRequestLocale } from "next-intl/server";
import { PageTransition } from "@/features/marketing/components/page-transition";
import { SiteFooter } from "@/features/marketing/components/site-footer";
import { SiteHeader } from "@/features/marketing/components/site-header";
import { WhatsAppFloat } from "@/features/marketing/components/whatsapp-float";

const plexSerif = IBM_Plex_Serif({
  variable: "--font-marketing-serif",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});
const plexSans = IBM_Plex_Sans({
  variable: "--font-marketing-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});
const plexMono = IBM_Plex_Mono({
  variable: "--font-marketing-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export default async function MarketingLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <div
      className={`marketing ${plexSerif.variable} ${plexSans.variable} ${plexMono.variable} flex min-h-full flex-1 flex-col bg-background text-foreground`}
    >
      <SiteHeader />
      <PageTransition>
        <main className="flex-1">{children}</main>
      </PageTransition>
      <SiteFooter />
      <WhatsAppFloat />
    </div>
  );
}
