"use client";

import { useState } from "react";
import { Check } from "lucide-react";
import { cn } from "cn";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { LoadFeedback, PageHeader } from "@/features/platform/components/panel-ui";
import { useLoad } from "@/features/platform/use-load";
import { useValidatedForm } from "@/lib/use-validated-form";
import { getExamOptions, getPaperDesign, savePaperDesign } from "../api";
import { FONT_SIZES, type ExamOptions, type ExamTheme } from "../schemas";
import { ErrorNote, SavedNote, useTeacherError, useWorkspace } from "./teacher-ui";

const PREVIEW_TEXT = { small: "text-[11px]", normal: "text-xs", large: "text-sm" } as const;

/** A small picture of the paper, so the teacher sees the choice before saving. */
function Preview({
  values,
  accent,
  soft,
}: {
  values: Record<string, string>;
  accent: string;
  soft: string;
}) {
  const t = useTranslations("Teacher.paperDesign.preview");
  const size = PREVIEW_TEXT[values.font_size as ExamTheme["font_size"]] ?? PREVIEW_TEXT.normal;
  const twoColumns = values.columns === "2";
  const questions = [1, 2, 3, 4];

  return (
    <figure className="flex flex-col gap-2">
      <figcaption className="text-sm font-semibold text-ink">{t("label")}</figcaption>
      {/* The print colors come from the chosen theme, so they are set inline. */}
      <div
        aria-hidden="true"
        className={cn("rounded-control border border-line bg-bg p-4 text-ink shadow-soft", size)}
      >
        <p className="text-base font-bold" style={{ color: accent }}>
          {t("title")}
        </p>
        <div className="mt-1 mb-3 h-0.5" style={{ backgroundColor: accent }} />
        {values.name_line === "yes" && (
          <div className="mb-3 grid grid-cols-2 gap-4">
            <span className="border-b border-ink-soft pb-1">{t("name")}</span>
            <span className="border-b border-ink-soft pb-1">{t("number")}</span>
          </div>
        )}
        <p
          className="mb-2 border-s-4 px-2 py-1 font-bold"
          style={{ backgroundColor: soft, color: accent, borderColor: accent }}
        >
          {t("section")}
        </p>
        <ol className={cn("gap-x-4", twoColumns ? "columns-2" : "")}>
          {questions.map((number) => (
            <li key={number} className="mb-2 break-inside-avoid">
              <b>{number}.</b> {t("question")}
              <span className="mt-0.5 block ps-3 text-ink-soft">(A) … (B) … (C) …</span>
            </li>
          ))}
        </ol>
      </div>
    </figure>
  );
}

function DesignForm({ options, design }: { options: ExamOptions; design: ExamTheme }) {
  const t = useTranslations("Teacher.paperDesign");
  const tColors = useTranslations("Teacher.tests.editor");
  const describe = useTeacherError();
  const { workspace } = useWorkspace();
  const [saved, setSaved] = useState<string | null>(null);
  const readOnly = workspace.access.read_only;

  const form = useValidatedForm<Record<string, string>>({
    initial: {
      color: design.color,
      font_size: design.font_size,
      columns: String(design.columns),
      name_line: design.name_line ? "yes" : "no",
    },
    idPrefix: "paper-",
    validators: {},
    submit: async (values) => {
      await savePaperDesign({
        color: values.color,
        font_size: values.font_size as ExamTheme["font_size"],
        columns: values.columns === "2" ? 2 : 1,
        name_line: values.name_line === "yes",
      });
    },
    onSuccess: () => setSaved(t("saved")),
    describeError: describe,
  });

  const update = (name: string, value: string) => {
    setSaved(null);
    form.setValue(name, value);
  };
  const theme = options.themes.find((item) => item.key === form.values.color) ?? options.themes[0];

  return (
    <form
      onSubmit={form.handleSubmit}
      noValidate
      className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_360px]"
    >
      <section className="flex flex-col gap-5 rounded-card border border-line bg-bg p-5">
        <fieldset className="flex flex-col gap-2" disabled={readOnly}>
          <legend className="mb-1 text-sm font-semibold text-ink">{t("color")}</legend>
          <div className="flex flex-wrap gap-2">
            {options.themes.map((item) => {
              const chosen = form.values.color === item.key;
              return (
                <button
                  key={item.key}
                  type="button"
                  aria-pressed={chosen}
                  onClick={() => update("color", item.key)}
                  className={cn(
                    "flex min-h-11 cursor-pointer items-center gap-2 rounded-full border px-3 text-sm font-semibold transition-colors disabled:cursor-not-allowed",
                    chosen
                      ? "border-navy bg-navy-soft text-navy"
                      : "border-line text-ink hover:border-navy-line",
                  )}
                >
                  {/* The paper's own print color, shown as a sample. */}
                  <span
                    aria-hidden="true"
                    className="flex size-5 items-center justify-center rounded-full border border-line text-on-dark"
                    style={{ backgroundColor: item.accent }}
                  >
                    {chosen && <Check className="size-3" />}
                  </span>
                  {tColors(`colors.${item.key as "navy"}`)}
                </button>
              );
            })}
          </div>
        </fieldset>

        <div className="grid gap-3 sm:grid-cols-2">
          <Field id="paper-font_size" label={t("fontSize")}>
            <Select
              {...form.bind("font_size")}
              onChange={(event) => update("font_size", event.target.value)}
              disabled={readOnly}
              className="h-11"
            >
              {FONT_SIZES.map((size) => (
                <option key={size} value={size}>
                  {tColors(`fontSizes.${size}`)}
                </option>
              ))}
            </Select>
          </Field>
          <Field id="paper-columns" label={t("columns")}>
            <Select
              {...form.bind("columns")}
              onChange={(event) => update("columns", event.target.value)}
              disabled={readOnly}
              className="h-11"
            >
              <option value="1">{tColors("oneColumn")}</option>
              <option value="2">{tColors("twoColumns")}</option>
            </Select>
          </Field>
        </div>

        <label className="flex cursor-pointer items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={form.values.name_line === "yes"}
            disabled={readOnly}
            onChange={(event) => update("name_line", event.target.checked ? "yes" : "no")}
            className="size-4"
          />
          {t("nameLine")}
        </label>

        <p className="text-xs text-ink-soft">{t("appliesTo")}</p>
        <ErrorNote message={form.formError} />
        <SavedNote message={saved} />
        {!readOnly && (
          <Button type="submit" className="w-full sm:w-fit" loading={form.saving}>
            {form.saving ? t("saving") : t("save")}
          </Button>
        )}
      </section>

      <aside className="rounded-card border border-line bg-bg p-5 lg:sticky lg:top-20">
        {theme && <Preview values={form.values} accent={theme.accent} soft={theme.soft} />}
      </aside>
    </form>
  );
}

/** One look for every test paper and answer key: set once, used on every download. */
export function PaperDesignPanel() {
  const t = useTranslations("Teacher.paperDesign");
  const options = useLoad(getExamOptions, "paper-options");
  const design = useLoad(getPaperDesign, "paper-design");

  return (
    <>
      <PageHeader title={t("title")} subtitle={t("subtitle")} />
      {options.state.name !== "ready" ? (
        <LoadFeedback state={options.state} onRetry={options.reload} />
      ) : design.state.name !== "ready" ? (
        <LoadFeedback state={design.state} onRetry={design.reload} />
      ) : (
        <DesignForm options={options.state.data} design={design.state.data} />
      )}
    </>
  );
}
