"use client";

import { useState, type ReactNode } from "react";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Link, useRouter } from "@/i18n/navigation";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  dateFromToday,
  optional,
  percent,
  requiredChoice,
  sanitizeDigits,
  sanitizeMoney,
  toLatinDigits,
  todayInRiyadh,
  useValidatedForm,
} from "@/lib/use-validated-form";
import { createQuotation, getFormChoices, getQuotation, updateQuotation } from "../api";
import {
  BILLING_CYCLES,
  QUOTATION_LANGUAGES,
  type BillingCycle,
  type FormChoices,
  type Quotation,
  type QuotationLanguage,
} from "../schemas";
import { useLoad } from "../use-load";
import { LoadFeedback, localName, PageHeader } from "./panel-ui";

const MONEY_PATTERN = /^\d{1,9}(\.\d{1,2})?$/;
const MAX_ITEMS = 50;
const MAX_QUANTITY = 10_000;
const DESCRIPTION_MAX = 300;
const VALID_DAYS = 30;

type Line = { key: number; description: string; quantity: string; unit_price: string };
type LineField = "description" | "quantity" | "unit_price";

class LinesInvalid extends Error {}

let nextKey = 1;
const newLine = (line?: Partial<Line>): Line => ({
  key: nextKey++,
  description: "",
  quantity: "1",
  unit_price: "",
  ...line,
});

function lineError(line: Line, field: LineField) {
  if (field === "description") {
    if (!line.description.trim()) return "required";
    return line.description.length > DESCRIPTION_MAX ? "tooLong" : null;
  }
  if (field === "quantity") {
    const quantity = Number(line.quantity);
    return Number.isInteger(quantity) && quantity >= 1 && quantity <= MAX_QUANTITY
      ? null
      : "quantity";
  }
  if (!line.unit_price) return "required";
  return MONEY_PATTERN.test(line.unit_price) ? null : "money";
}

/** Riyals as text -> halalas as a whole number, so the preview never adds floats. */
function toHalalas(value: string) {
  if (!MONEY_PATTERN.test(value)) return 0;
  const [riyals, fraction = ""] = value.split(".");
  return Number(riyals) * 100 + Number(fraction.padEnd(2, "0"));
}

function previewTotals(lines: Line[], vatRate: string) {
  const subtotal = lines.reduce(
    (sum, line) => sum + (Number(line.quantity) || 0) * toHalalas(line.unit_price),
    0,
  );
  const basisPoints = toHalalas(vatRate);
  const vat = Math.round((subtotal * basisPoints) / 10_000);
  return { subtotal, vat, total: subtotal + vat };
}

function plusDays(isoDate: string, days: number) {
  const date = new Date(`${isoDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function initialRecipient(quotation?: Quotation, school?: string, demo?: string) {
  if (quotation?.school) return `school:${quotation.school.id}`;
  if (quotation?.demo_request) return `demo:${quotation.demo_request}`;
  if (demo) return `demo:${demo}`;
  if (school) return `school:${school}`;
  return "";
}

function parseRecipient(value: string) {
  const [kind, id] = value.split(":");
  return {
    school: kind === "school" ? Number(id) : null,
    demo_request: kind === "demo" ? Number(id) : null,
  };
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="gap-3 py-4">
      <CardHeader className="px-5">
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-x-4 gap-y-3 px-5 sm:grid-cols-2 lg:grid-cols-3">
        {children}
      </CardContent>
    </Card>
  );
}

function QuotationForm({
  choices,
  quotation,
  presetSchool,
  presetDemo,
}: {
  choices: FormChoices;
  quotation?: Quotation;
  presetSchool?: string;
  presetDemo?: string;
}) {
  const t = useTranslations("Platform.quotationForm");
  const tCommon = useTranslations("Platform.common");
  const tErrors = useTranslations("Leads.errors");
  const locale = useLocale();
  const router = useRouter();
  const editing = quotation !== undefined;

  const [lines, setLines] = useState<Line[]>(() =>
    quotation
      ? quotation.items.map((item) =>
          newLine({
            description: item.description,
            quantity: String(item.quantity),
            unit_price: item.unit_price,
          }),
        )
      : [newLine()],
  );
  const [linesTouched, setLinesTouched] = useState(false);

  const form = useValidatedForm({
    initial: {
      // "school:12" or "demo:5": one choice covers both kinds of recipient.
      recipient: initialRecipient(quotation, presetSchool, presetDemo),
      language: quotation?.language ?? (locale === "ar" ? "ar" : "en"),
      plan: quotation?.plan ? String(quotation.plan.id) : "",
      billing_cycle: quotation?.billing_cycle ?? "",
      valid_until: quotation?.valid_until ?? plusDays(todayInRiyadh(), VALID_DAYS),
      vat_rate: quotation?.vat_rate ?? "15.00",
      recipient_name: quotation?.recipient_name ?? "",
      recipient_email: quotation?.recipient_email ?? "",
      recipient_organization: quotation?.recipient_organization ?? "",
      notes: quotation?.notes ?? "",
    },
    validators: {
      recipient: requiredChoice,
      valid_until: dateFromToday,
      vat_rate: percent,
      recipient_name: optional(120),
      recipient_email: (value) =>
        value.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim()) ? "email" : null,
      recipient_organization: optional(200),
      notes: optional(2000),
    },
    sanitizers: { vat_rate: sanitizeMoney },
    rejectedInputErrors: { vat_rate: "moneyCharacters" },
    validateWhileTyping: true,
    idPrefix: "quote-",
    submit: async (values) => {
      setLinesTouched(true);
      const invalid = lines.find((line) =>
        (["description", "quantity", "unit_price"] as const).some((field) =>
          lineError(line, field),
        ),
      );
      if (invalid) {
        document.getElementById(`line-${invalid.key}-description`)?.focus();
        throw new LinesInvalid();
      }

      const body = {
        language: values.language as QuotationLanguage,
        plan: values.plan ? Number(values.plan) : null,
        billing_cycle: values.billing_cycle as BillingCycle | "",
        valid_until: values.valid_until,
        vat_rate: values.vat_rate,
        notes: values.notes.trim(),
        recipient_name: values.recipient_name.trim(),
        recipient_email: values.recipient_email.trim(),
        recipient_organization: values.recipient_organization.trim(),
        items: lines.map((line) => ({
          description: line.description.trim(),
          quantity: Number(line.quantity),
          unit_price: line.unit_price,
        })),
      };
      const saved = quotation
        ? await updateQuotation(quotation.id, body)
        : await createQuotation({ ...body, ...parseRecipient(values.recipient) });
      router.push(`/platform/quotations?saved=${encodeURIComponent(saved.number)}`);
    },
    describeError: (err) => (err instanceof LinesInvalid ? t("errors.lines") : null),
  });

  function updateLine(key: number, field: LineField, value: string) {
    const clean =
      field === "quantity"
        ? sanitizeDigits(value)
        : field === "unit_price"
          ? sanitizeMoney(value)
          : value;
    setLines((current) =>
      current.map((line) => (line.key === key ? { ...line, [field]: clean } : line)),
    );
  }

  /** Picking a plan fills the first empty line with its price. */
  function applyPlan(planId: string, cycle: string) {
    const plan = choices.plans.find((option) => String(option.id) === planId);
    if (!plan || !cycle) return;
    const price = cycle === "yearly" ? plan.yearly_price : plan.monthly_price;
    const description = t("planLine", {
      plan: localName(plan, form.values.language),
      cycle: tCommon(`cycles.${cycle as BillingCycle}`),
    });
    setLines((current) => {
      const empty = current.find((line) => !line.description && !line.unit_price);
      if (empty) {
        return current.map((line) =>
          line.key === empty.key ? { ...line, description, unit_price: price } : line,
        );
      }
      return [...current, newLine({ description, unit_price: price })];
    });
  }

  const totals = previewTotals(lines, form.values.vat_rate);
  const money = (halalas: number) =>
    (halalas / 100).toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const planBind = form.bind("plan");
  const cycleBind = form.bind("billing_cycle");

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-4">
      <Section title={t("sections.recipient")}>
        <div className="sm:col-span-2">
          <Field
            id="quote-recipient"
            label={t("fields.recipientType")}
            required
            hint={editing ? t("fields.recipientFixed") : undefined}
            error={form.errorFor("recipient")}
          >
            <Select {...form.bind("recipient")} disabled={editing} className="h-10">
              <option value="">{tCommon("choose")}</option>
              {editing && (
                <option value={form.values.recipient}>{quotation.recipient_organization}</option>
              )}
              {!editing && (
                <>
                  <optgroup label={t("recipientTypes.school")}>
                    {choices.schools.map((school) => (
                      <option key={school.id} value={`school:${school.id}`}>
                        {localName(school, locale)} ({school.code})
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label={t("recipientTypes.demo")}>
                    {choices.demo_requests.map((demo) => (
                      <option key={demo.id} value={`demo:${demo.id}`}>
                        {demo.school_name} ({demo.name})
                      </option>
                    ))}
                  </optgroup>
                </>
              )}
            </Select>
          </Field>
        </div>
        <Field id="quote-language" label={t("fields.language")} hint={t("fields.languageHint")}>
          <Select {...form.bind("language")} className="h-10">
            {QUOTATION_LANGUAGES.map((language) => (
              <option key={language} value={language}>
                {t(`languages.${language}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          id="quote-recipient_name"
          label={t("fields.recipientName")}
          hint={t("fields.fromRecipient")}
          error={form.errorFor("recipient_name")}
        >
          <Input {...form.bind("recipient_name")} className="h-10" />
        </Field>
        <Field
          id="quote-recipient_email"
          label={t("fields.recipientEmail")}
          hint={t("fields.fromRecipient")}
          error={form.errorFor("recipient_email")}
        >
          <Input {...form.bind("recipient_email")} type="email" dir="ltr" className="h-10" />
        </Field>
        <Field
          id="quote-recipient_organization"
          label={t("fields.organization")}
          hint={t("fields.fromRecipient")}
          error={form.errorFor("recipient_organization")}
        >
          <Input {...form.bind("recipient_organization")} className="h-10" />
        </Field>
      </Section>

      <Section title={t("sections.terms")}>
        <Field id="quote-plan" label={t("fields.plan")} hint={t("fields.planHint")}>
          <Select
            {...planBind}
            onChange={(event) => {
              planBind.onChange(event);
              applyPlan(event.target.value, form.values.billing_cycle);
            }}
            className="h-10"
          >
            <option value="">{t("noPlan")}</option>
            {choices.plans.map((plan) => (
              <option key={plan.id} value={plan.id}>
                {localName(plan, locale)}
              </option>
            ))}
          </Select>
        </Field>
        <Field id="quote-billing_cycle" label={t("fields.billingCycle")}>
          <Select
            {...cycleBind}
            onChange={(event) => {
              cycleBind.onChange(event);
              applyPlan(form.values.plan, event.target.value);
            }}
            className="h-10"
          >
            <option value="">{t("noCycle")}</option>
            {BILLING_CYCLES.map((cycle) => (
              <option key={cycle} value={cycle}>
                {tCommon(`cycles.${cycle}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          id="quote-valid_until"
          label={t("fields.validUntil")}
          required
          error={form.errorFor("valid_until")}
        >
          <Input {...form.bind("valid_until")} type="date" className="h-10" />
        </Field>
        <Field
          id="quote-vat_rate"
          label={t("fields.vatRate")}
          required
          hint={t("fields.vatRateHint")}
          error={form.errorFor("vat_rate")}
        >
          <Input {...form.bind("vat_rate")} inputMode="decimal" dir="ltr" className="h-10" />
        </Field>
        <div className="sm:col-span-2 lg:col-span-3">
          <Field id="quote-notes" label={t("fields.notes")} error={form.errorFor("notes")}>
            <Textarea {...form.bind("notes")} rows={3} placeholder={t("fields.notesPlaceholder")} />
          </Field>
        </div>
      </Section>

      <Card className="gap-3 py-4">
        <CardHeader className="px-5">
          <CardTitle>{t("sections.lines")}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 px-5">
          {lines.map((line, index) => {
            const errorFor = (field: LineField) => {
              if (!linesTouched) return undefined;
              const key = lineError(line, field);
              return key ? tErrors(key) : undefined;
            };
            return (
              <fieldset
                key={line.key}
                className="grid gap-3 rounded-control border border-line p-3 sm:grid-cols-[1fr_110px_160px_auto] sm:items-start"
              >
                <legend className="sr-only">{t("lineLabel", { number: index + 1 })}</legend>
                <Field
                  id={`line-${line.key}-description`}
                  label={t("fields.description")}
                  required
                  error={errorFor("description")}
                >
                  <Input
                    id={`line-${line.key}-description`}
                    value={line.description}
                    aria-invalid={Boolean(errorFor("description"))}
                    onChange={(event) => updateLine(line.key, "description", event.target.value)}
                    maxLength={DESCRIPTION_MAX + 1}
                    className="h-10"
                  />
                </Field>
                <Field
                  id={`line-${line.key}-quantity`}
                  label={t("fields.quantity")}
                  required
                  error={errorFor("quantity")}
                >
                  <Input
                    id={`line-${line.key}-quantity`}
                    value={line.quantity}
                    inputMode="numeric"
                    dir="ltr"
                    aria-invalid={Boolean(errorFor("quantity"))}
                    onChange={(event) =>
                      updateLine(line.key, "quantity", toLatinDigits(event.target.value))
                    }
                    className="h-10"
                  />
                </Field>
                <Field
                  id={`line-${line.key}-unit_price`}
                  label={t("fields.unitPrice")}
                  required
                  error={errorFor("unit_price")}
                >
                  <Input
                    id={`line-${line.key}-unit_price`}
                    value={line.unit_price}
                    inputMode="decimal"
                    dir="ltr"
                    aria-invalid={Boolean(errorFor("unit_price"))}
                    onChange={(event) => updateLine(line.key, "unit_price", event.target.value)}
                    className="h-10"
                  />
                </Field>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={t("removeLine", { number: index + 1 })}
                  disabled={lines.length === 1}
                  onClick={() => setLines((current) => current.filter((l) => l.key !== line.key))}
                  className="sm:mt-6"
                >
                  <Trash2 aria-hidden="true" />
                </Button>
              </fieldset>
            );
          })}

          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={lines.length >= MAX_ITEMS}
            onClick={() => setLines((current) => [...current, newLine()])}
            className="self-start"
          >
            <Plus aria-hidden="true" />
            {t("addLine")}
          </Button>

          <dl className="ms-auto grid w-full max-w-xs grid-cols-2 gap-x-4 gap-y-1 text-sm tabular-nums">
            <dt className="text-ink-soft">{t("subtotal")}</dt>
            <dd className="text-end">
              <bdi>{money(totals.subtotal)}</bdi> {tCommon("currency")}
            </dd>
            <dt className="text-ink-soft">{t("vat")}</dt>
            <dd className="text-end">
              <bdi>{money(totals.vat)}</bdi> {tCommon("currency")}
            </dd>
            <dt className="border-t border-line pt-1 font-bold text-navy-deep">{t("total")}</dt>
            <dd className="border-t border-line pt-1 text-end font-bold text-navy-deep">
              <bdi>{money(totals.total)}</bdi> {tCommon("currency")}
            </dd>
          </dl>
          <p className="text-end text-xs text-ink-soft">{t("totalsHint")}</p>
        </CardContent>
      </Card>

      {form.formError && (
        <p role="alert" className="rounded-control bg-red-50 p-3 text-sm text-red-800">
          {form.formError}
        </p>
      )}

      <div className="flex flex-wrap justify-end gap-2">
        <Link href="/platform/quotations" className={buttonVariants({ variant: "ghost" })}>
          {tCommon("cancel")}
        </Link>
        <Button type="submit" loading={form.saving}>
          {form.saving ? tCommon("saving") : editing ? t("saveChanges") : t("saveDraft")}
        </Button>
      </div>
    </form>
  );
}

export function QuotationFormPanel() {
  const t = useTranslations("Platform.quotationForm");
  const searchParams = useSearchParams();
  const editId = Number(searchParams.get("edit")) || null;
  const presetSchool = searchParams.get("school") ?? undefined;
  const presetDemo = searchParams.get("demo") ?? undefined;

  const data = useLoad(
    async (signal) => ({
      choices: await getFormChoices(signal),
      quotation: editId ? await getQuotation(editId, signal) : undefined,
    }),
    `form:${editId ?? "new"}`,
  );

  const ready = data.state.name === "ready" ? data.state.data : null;
  const notDraft = ready?.quotation !== undefined && ready.quotation.status !== "draft";

  return (
    <>
      <PageHeader
        title={editId ? t("editTitle") : t("newTitle")}
        subtitle={ready?.quotation ? ready.quotation.number : t("subtitle")}
        action={
          <Link
            href="/platform/quotations"
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            <ArrowLeft aria-hidden="true" className="rtl:rotate-180" />
            {t("back")}
          </Link>
        }
      />
      <LoadFeedback state={data.state} onRetry={data.reload} />
      {notDraft && (
        <p role="alert" className="rounded-control bg-amber-50 p-3 text-sm text-amber-800">
          {t("notDraft")}
        </p>
      )}
      {ready && !notDraft && (
        <QuotationForm
          key={editId ?? "new"}
          choices={ready.choices}
          quotation={ready.quotation}
          presetSchool={presetSchool}
          presetDemo={presetDemo}
        />
      )}
    </>
  );
}
