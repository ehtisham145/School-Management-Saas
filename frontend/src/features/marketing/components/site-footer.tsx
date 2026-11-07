import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { INFO_EMAIL, SUPPORT_EMAIL, WHATSAPP_NUMBER_DISPLAY, WHATSAPP_URL } from "../contact-info";
import { Logo } from "./logo";

export async function SiteFooter() {
  const t = await getTranslations("Marketing.footer");
  const tNav = await getTranslations("Marketing.nav");

  const linkClass = "transition-colors hover:text-on-dark";
  const headingClass = "mb-3 text-sm font-bold tracking-normal text-on-dark";

  return (
    <footer className="bg-navy-deep text-[14.5px] text-on-dark-soft">
      <div className="page-wrap">
        <div className="grid grid-cols-2 gap-[26px] pt-14 pb-9 sm:gap-8 lg:grid-cols-[1.6fr_1fr_1fr_1.4fr]">
          <div className="col-span-2 sm:col-span-1">
            <Link href="/" className="inline-block rounded-btn bg-bg px-3.5 py-2.5">
              <Logo className="h-14 sm:h-14" />
            </Link>
            <p className="mt-3.5 max-w-[34ch]">{t("tag")}</p>
          </div>

          <div>
            <h3 className={headingClass}>{t("product")}</h3>
            <ul className="grid gap-2">
              <li>
                <Link href="/lms" className={linkClass}>
                  {tNav("lms")}
                </Link>
              </li>
              <li>
                <Link href="/pricing" className={linkClass}>
                  {tNav("pricing")}
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className={headingClass}>{t("company")}</h3>
            <ul className="grid gap-2">
              <li>
                <Link href="/about" className={linkClass}>
                  {tNav("about")}
                </Link>
              </li>
              <li>
                <Link href="/contact" className={linkClass}>
                  {tNav("contact")}
                </Link>
              </li>
            </ul>
          </div>

          <div className="col-span-2 sm:col-span-1">
            <h3 className={headingClass}>{t("talk")}</h3>
            <ul className="grid gap-2">
              <li>
                {t("general")}:{" "}
                <a href={`mailto:${INFO_EMAIL}`} className={linkClass}>
                  <bdi>{INFO_EMAIL}</bdi>
                </a>
              </li>
              <li>
                {t("support")}:{" "}
                <a href={`mailto:${SUPPORT_EMAIL}`} className={linkClass}>
                  <bdi>{SUPPORT_EMAIL}</bdi>
                </a>
              </li>
              <li>
                <a
                  href={WHATSAPP_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={linkClass}
                >
                  <bdi>{WHATSAPP_NUMBER_DISPLAY}</bdi>
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="flex flex-col gap-2 border-t border-on-dark-line py-[18px] text-[13px] sm:flex-row sm:items-center sm:justify-between">
          <p className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span>{t("copy")}</span>
            <Link href="/privacy" className={`${linkClass} underline underline-offset-4`}>
              {t("privacy")}
            </Link>
          </p>
          <p>{t("developedBy")}</p>
        </div>
      </div>
    </footer>
  );
}
