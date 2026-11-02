import { getTranslations } from "next-intl/server";
import { WHATSAPP_URL } from "../contact-info";
import { ChatIcon } from "../icons";

export async function WhatsAppFloat() {
  const t = await getTranslations("Marketing.common");

  return (
    <a
      href={WHATSAPP_URL}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={t("whatsappLabel")}
      className="fixed end-6 bottom-6 z-50 flex h-14 w-14 items-center justify-center rounded-[var(--radius)] bg-[var(--mk-teal)] text-white shadow-lg shadow-black/20 transition-transform hover:-translate-y-0.5"
    >
      <ChatIcon className="h-7 w-7" />
    </a>
  );
}
