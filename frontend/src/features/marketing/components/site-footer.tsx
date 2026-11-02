import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { CONTACT_EMAIL, WHATSAPP_NUMBER_DISPLAY, WHATSAPP_URL } from "../contact-info";
import { BrandMark, ChatIcon, MailIcon } from "../icons";

export async function SiteFooter() {
  const t = await getTranslations("Marketing.footer");
  const tNav = await getTranslations("Marketing.nav");

  return (
    <footer className="border-t border-border bg-muted">
      <div className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <Link
              href="/"
              className="font-display flex items-center gap-2 text-lg font-bold text-foreground"
            >
              <BrandMark className="h-6 w-6 text-primary" />
              {tNav("brand")}
            </Link>
            <p className="mt-3 max-w-[32ch] text-sm text-muted-foreground">{t("tagline")}</p>
          </div>

          <div>
            <h4 className="font-marketing-mono text-xs font-medium tracking-[0.1em] text-[var(--mk-ink-faint)] uppercase">
              {t("productHeading")}
            </h4>
            <ul className="mt-4 flex flex-col gap-2.5">
              <li>
                <Link href="/features" className="text-sm text-muted-foreground hover:text-primary">
                  {tNav("features")}
                </Link>
              </li>
              <li>
                <Link href="/pricing" className="text-sm text-muted-foreground hover:text-primary">
                  {tNav("pricing")}
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-marketing-mono text-xs font-medium tracking-[0.1em] text-[var(--mk-ink-faint)] uppercase">
              {t("companyHeading")}
            </h4>
            <ul className="mt-4 flex flex-col gap-2.5">
              <li>
                <Link href="/about" className="text-sm text-muted-foreground hover:text-primary">
                  {tNav("about")}
                </Link>
              </li>
              <li>
                <Link href="/contact" className="text-sm text-muted-foreground hover:text-primary">
                  {tNav("contact")}
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-marketing-mono text-xs font-medium tracking-[0.1em] text-[var(--mk-ink-faint)] uppercase">
              {t("talkHeading")}
            </h4>
            <div className="mt-4 flex flex-col gap-2.5">
              <a
                href={WHATSAPP_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary"
              >
                <ChatIcon className="h-4 w-4 shrink-0" />
                <span dir="ltr">{WHATSAPP_NUMBER_DISPLAY}</span>
              </a>
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary"
              >
                <MailIcon className="h-4 w-4 shrink-0" />
                <span dir="ltr">{CONTACT_EMAIL}</span>
              </a>
            </div>
          </div>
        </div>

        <div className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-6 text-xs text-muted-foreground">
          <span>{t("copyright")}</span>
          <span>{t("demoNote")}</span>
        </div>
      </div>
    </footer>
  );
}
