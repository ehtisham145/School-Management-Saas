import type { ComponentType, ReactNode } from "react";
import {
  BarChart3,
  Building2,
  ClipboardCheck,
  ClipboardList,
  FileBarChart2,
  LayoutDashboard,
  Presentation,
  Repeat2,
  Sparkles,
  UploadCloud,
  UsersRound,
} from "lucide-react";
import { getTranslations } from "next-intl/server";
import { cn } from "cn";
import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import { Section, SectionHeading } from "./blocks";
import { Reveal } from "./reveal";

type Icon = ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
type Item = { title: string; desc: string; pro?: boolean };

const SCHOOL_ITEM_ICONS: Icon[] = [
  LayoutDashboard,
  UsersRound,
  ClipboardList,
  FileBarChart2,
  BarChart3,
];

const TEACHER_ITEM_ICONS: Icon[] = [
  Presentation,
  Sparkles,
  ClipboardCheck,
  UploadCloud,
  Repeat2,
  FileBarChart2,
];

function PathCard({
  tone,
  icon: IconComponent,
  badge,
  title,
  tagline,
  description,
  listLabel,
  items,
  itemIcons,
  proLabel,
  cta,
  href,
  note,
}: {
  tone: "navy" | "orange";
  icon: Icon;
  badge?: string;
  title: string;
  tagline: string;
  description?: string;
  listLabel: string;
  items: Item[];
  itemIcons: Icon[];
  proLabel?: string;
  cta: string;
  href: string;
  note?: string;
}) {
  return (
    <article className="flex h-full flex-col rounded-cta border border-line bg-bg p-8">
      {badge && (
        <span
          className={cn(
            "mb-4 w-fit rounded-full px-3 py-1 text-[11px] font-bold tracking-wide uppercase",
            tone === "navy" ? "bg-navy-soft text-navy" : "bg-orange-soft text-orange-text",
          )}
        >
          {badge}
        </span>
      )}

      <span
        className={cn(
          "grid size-[46px] shrink-0 place-items-center rounded-tile",
          tone === "navy" ? "bg-navy-soft text-navy" : "bg-orange-soft text-orange-text",
        )}
      >
        <IconComponent aria-hidden className="size-[23px]" />
      </span>

      <h3 className="mt-4 text-[20px] text-navy-deep">{title}</h3>
      <p
        className={cn(
          "mt-1 text-[13.5px] font-bold",
          tone === "navy" ? "text-navy" : "text-orange-text",
        )}
      >
        {tagline}
      </p>
      {description && <p className="mt-2 text-[14.5px] text-ink-soft">{description}</p>}

      <p className="mt-6 mb-4 border-t border-line pt-6 text-[13px] font-bold text-navy-deep">
        {listLabel}
      </p>
      <ul className="flex flex-1 flex-col gap-3.5">
        {items.map((item, index) => {
          const ItemIcon = itemIcons[index];
          return (
            <li key={item.title} className="flex items-start gap-3">
              <span
                className={cn(
                  "mt-0.5 grid size-7 shrink-0 place-items-center rounded-control",
                  tone === "navy" ? "bg-navy-soft text-navy" : "bg-orange-soft text-orange-text",
                )}
              >
                <ItemIcon aria-hidden className="size-4" />
              </span>
              <div>
                <p className="flex flex-wrap items-center gap-2 text-[14.5px] font-semibold text-ink">
                  {item.title}
                  {item.pro && proLabel && (
                    <span className="rounded-full bg-orange-soft px-2 py-0.5 text-[11px] font-bold text-orange-text">
                      {proLabel}
                    </span>
                  )}
                </p>
                <p className="text-[13px] text-ink-soft">{item.desc}</p>
              </div>
            </li>
          );
        })}
      </ul>

      <Link
        href={href}
        className={buttonVariants({
          variant: tone === "navy" ? "default" : "orange",
          className: "mt-7 w-full",
        })}
      >
        {cta}
      </Link>
      {note && <p className="mt-3 text-center text-[12.5px] text-ink-soft">{note}</p>}
    </article>
  );
}

export async function ChoosePathSection(): Promise<ReactNode> {
  const t = await getTranslations("Marketing.home.choosePath");
  const schoolItems = t.raw("school.items") as Item[];
  const teacherItems = t.raw("teacher.items") as Item[];

  return (
    <Section tinted>
      <SectionHeading kicker={t("eyebrow")} title={t("title")} description={t("description")} />
      <div className="grid items-stretch gap-6 md:grid-cols-2">
        <Reveal className="h-full">
          <PathCard
            tone="navy"
            icon={Building2}
            title={t("school.title")}
            tagline={t("school.tagline")}
            listLabel={t("school.listLabel")}
            items={schoolItems}
            itemIcons={SCHOOL_ITEM_ICONS}
            cta={t("school.cta")}
            href="/pricing#schools"
          />
        </Reveal>
        <Reveal delayMs={110} className="h-full">
          <PathCard
            tone="orange"
            icon={Presentation}
            badge={t("teacher.badge")}
            title={t("teacher.title")}
            tagline={t("teacher.tagline")}
            description={t("teacher.description")}
            listLabel={t("teacher.listLabel")}
            items={teacherItems}
            itemIcons={TEACHER_ITEM_ICONS}
            proLabel={t("teacher.proLabel")}
            cta={t("teacher.cta")}
            href="/start-trial"
            note={t("teacher.note")}
          />
        </Reveal>
      </div>
      <p className="mx-auto mt-8 max-w-[70ch] text-center text-sm text-ink-soft">{t("footnote")}</p>
    </Section>
  );
}
