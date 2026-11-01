import { Suspense } from "react";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { buttonVariants } from "@/components/ui/button";
import { PageHero } from "@/features/marketing/components/page-hero";
import { Reveal } from "@/features/marketing/components/reveal";
import { ContactForm } from "@/features/marketing/components/contact-form";
import { CONTACT_EMAIL, WHATSAPP_URL } from "@/features/marketing/contact-info";
import { ChatIcon, MailIcon } from "@/features/marketing/icons";

const PLAN_KEYS = ["starter", "growth", "network"] as const;

export default async function ContactPage({ params, searchParams }: PageProps<"/[locale]/contact">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.contact");

  const words = t.raw("hero.words") as string[];

  return (
    <>
      <PageHero
        eyebrow={t("hero.eyebrow")}
        titleLead={t("hero.titleLead")}
        words={words}
        lede={t("hero.lede")}
      />

      <section className="mx-auto max-w-6xl px-6 pt-16 sm:pt-20">
        <div className="grid gap-6 sm:grid-cols-2">
          <Reveal>
            <a
              href={WHATSAPP_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex h-full flex-col gap-3 border border-border bg-card p-7 transition-colors hover:bg-accent"
            >
              <span className="flex h-11 w-11 items-center justify-center rounded-[var(--radius)] bg-[var(--mk-teal-soft)] text-[var(--mk-teal)]">
                <ChatIcon className="h-5 w-5" />
              </span>
              <h3 className="font-display text-lg font-semibold text-card-foreground">
                {t("channels.whatsapp.title")}
              </h3>
              <p className="text-sm text-muted-foreground">{t("channels.whatsapp.description")}</p>
              <span dir="ltr" className="font-marketing-mono text-sm text-primary">
                {t("channels.whatsapp.value")}
              </span>
            </a>
          </Reveal>

          <Reveal delayMs={90}>
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="group flex h-full flex-col gap-3 border border-border bg-card p-7 transition-colors hover:bg-accent"
            >
              <span className="flex h-11 w-11 items-center justify-center rounded-[var(--radius)] bg-accent text-primary">
                <MailIcon className="h-5 w-5" />
              </span>
              <h3 className="font-display text-lg font-semibold text-card-foreground">
                {t("channels.email.title")}
              </h3>
              <p className="text-sm text-muted-foreground">{t("channels.email.description")}</p>
              <span dir="ltr" className="font-marketing-mono text-sm text-primary">
                {t("channels.email.value")}
              </span>
            </a>
          </Reveal>
        </div>
      </section>

      <section className="mx-auto max-w-2xl px-6 py-16 sm:py-20">
        <Reveal>
          <h2 className="font-display text-2xl font-semibold text-foreground">
            {t("form.heading")}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">{t("form.description")}</p>
          <div className="mt-8">
            <Suspense fallback={<ContactForm />}>
              <ContactFormWithPlan searchParams={searchParams} />
            </Suspense>
          </div>
        </Reveal>
      </section>

      <section className="bg-[var(--mk-band-bg)] text-[var(--mk-band-text)]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-8 px-6 py-16 sm:py-20">
          <div>
            <h2 className="max-w-[20ch] text-balance font-display text-3xl font-semibold text-[var(--mk-band-text)] sm:text-4xl">
              {t("cta.title")}
            </h2>
            <p className="mt-3 max-w-[42ch] text-[var(--mk-band-text)] opacity-80">
              {t("cta.description")}
            </p>
          </div>
          <a
            href={WHATSAPP_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonVariants({ size: "lg" })}
          >
            {t("cta.button")}
          </a>
        </div>
      </section>
    </>
  );
}

async function ContactFormWithPlan({
  searchParams,
}: {
  searchParams: PageProps<"/[locale]/contact">["searchParams"];
}) {
  const resolved = await searchParams;
  const planParam = typeof resolved.plan === "string" ? resolved.plan : undefined;
  const plan = PLAN_KEYS.find((key) => key === planParam);

  let planLabel: string | undefined;
  if (plan) {
    const tTiers = await getTranslations("Marketing.pricing.tiers");
    planLabel = tTiers(`${plan}.name`);
  }

  return <ContactForm planLabel={planLabel} />;
}
