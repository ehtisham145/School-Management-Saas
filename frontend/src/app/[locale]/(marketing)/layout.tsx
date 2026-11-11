import { setRequestLocale } from "next-intl/server";
import { DemoDialogProvider } from "@/features/leads/components/demo-dialog";
import { SiteFooter } from "@/features/marketing/components/site-footer";
import { SiteHeader } from "@/features/marketing/components/site-header";
import { HeroPreloader } from "@/features/marketing/components/hero-preloader";
import { WhatsAppFloat } from "@/features/marketing/components/whatsapp-float";

export default async function MarketingLayout({ children, params }: LayoutProps<"/[locale]">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <DemoDialogProvider>
      <noscript>
        <style>
          {".reveal{opacity:1!important;translate:none!important;scale:none!important}"}
        </style>
      </noscript>
      <div className="flex min-h-full flex-1 flex-col">
        <SiteHeader />
        <main id="top" className="flex-1">
          {children}
        </main>
        <SiteFooter />
        <WhatsAppFloat />
        <HeroPreloader />
      </div>
    </DemoDialogProvider>
  );
}
