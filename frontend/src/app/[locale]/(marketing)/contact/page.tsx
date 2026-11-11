import { getTranslations, setRequestLocale } from "next-intl/server";
import { HERO_IMAGES } from "@/features/marketing/hero-images";
import { buttonVariants } from "@/components/ui/button";
import { ContactForm } from "@/features/leads/components/contact-form";
import { CtaLinkBox, PageHero, Section } from "@/features/marketing/components/blocks";
import {
  INFO_EMAIL,
  SUPPORT_EMAIL,
  WHATSAPP_NUMBER_DISPLAY,
  WHATSAPP_URL,
} from "@/features/marketing/contact-info";
import { MailIcon } from "@/features/marketing/components/icons";
import { Reveal } from "@/features/marketing/components/reveal";
import { WhatsAppLogo } from "@/features/marketing/components/whatsapp-float";
import { pageMetadata } from "@/i18n/metadata";

export async function generateMetadata({ params }: PageProps<"/[locale]/contact">) {
  const { locale } = await params;
  return pageMetadata(locale, "contact", "/contact");
}

export default async function ContactPage({ params }: PageProps<"/[locale]/contact">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.contact");

  return (
    <>
      <PageHero
        image={HERO_IMAGES.contact}
        titleLead={t("hero.titleLead")}
        words={t.raw("hero.words") as string[]}
        locale={locale}
      />

      <Section>
        <div className="grid gap-8 lg:grid-cols-[1.25fr_1fr] lg:items-start lg:gap-12">
          <Reveal className="rounded-card border border-line bg-bg p-6 sm:p-8">
            <h2 className="text-[clamp(24px,2.6vw,30px)] text-navy-deep">{t("formHeading")}</h2>
            <p className="mt-2 mb-6 text-ink-soft">{t("formDescription")}</p>
            <ContactForm />
          </Reveal>

          <Reveal delayMs={120} className="flex flex-col gap-[18px]">
            <a
              href={WHATSAPP_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="block rounded-card border border-line bg-bg p-[26px] transition-[transform,box-shadow,border-color] duration-200 hover:-translate-y-[3px] hover:border-navy-line hover:shadow-soft"
            >
              <span className="grid size-[46px] place-items-center rounded-full bg-whatsapp text-on-dark">
                <WhatsAppLogo className="size-[26px]" />
              </span>
              <h3 className="mt-4 text-[18.5px] text-ink">{t("channels.whatsapp.title")}</h3>
              <p className="mt-2 text-[14.8px] text-ink-soft">
                {t("channels.whatsapp.description")}
              </p>
              <p className="mt-3 font-semibold text-navy">
                <bdi>{WHATSAPP_NUMBER_DISPLAY}</bdi>
              </p>
            </a>

            <div className="rounded-card border border-line bg-bg p-[26px]">
              <span className="grid size-[46px] place-items-center rounded-tile bg-navy-soft text-navy">
                <MailIcon aria-hidden="true" className="size-[23px]" />
              </span>
              <h3 className="mt-4 text-[18.5px] text-ink">{t("channels.email.title")}</h3>
              <p className="mt-2 text-[14.8px] text-ink-soft">{t("channels.email.description")}</p>
              <dl className="mt-3 grid gap-2.5 text-[14.8px]">
                <div>
                  <dt className="text-ink-soft">{t("channels.email.general")}</dt>
                  <dd className="font-semibold text-navy">
                    <a href={`mailto:${INFO_EMAIL}`} className="hover:underline">
                      <bdi>{INFO_EMAIL}</bdi>
                    </a>
                  </dd>
                </div>
                <div>
                  <dt className="text-ink-soft">{t("channels.email.support")}</dt>
                  <dd className="font-semibold text-navy">
                    <a href={`mailto:${SUPPORT_EMAIL}`} className="hover:underline">
                      <bdi>{SUPPORT_EMAIL}</bdi>
                    </a>
                  </dd>
                </div>
              </dl>
            </div>
          </Reveal>
        </div>
      </Section>

      <CtaLinkBox title={t("cta.title")} description={t("cta.description")}>
        <a
          href={WHATSAPP_URL}
          target="_blank"
          rel="noopener noreferrer"
          className={buttonVariants({ variant: "orange", className: "w-full sm:w-auto" })}
        >
          {t("cta.button")}
        </a>
      </CtaLinkBox>
    </>
  );
}
