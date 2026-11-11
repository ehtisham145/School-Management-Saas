"use client";

import { useEffect, useState, type ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Link, useRouter } from "@/i18n/navigation";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import {
  email,
  englishName,
  optionalArabicName,
  optionalRegistrationNumber,
  optionalSlug,
  required,
  requiredMobile,
  optionalPhone,
  sanitizeDigits,
  sanitizePhone,
  sanitizeRegistrationNumber,
  sanitizeSlug,
  useValidatedForm,
  wholeNumberInRange,
} from "@/lib/use-validated-form";
import { createSchool, getDemoRequest } from "../api";
import { EDUCATION_STAGES, SAUDI_REGIONS, SCHOOL_TYPES, type DemoRequest } from "../schemas";
import { useLoad } from "../use-load";
import { LoadFeedback, PageHeader } from "./panel-ui";

const ARABIC_LETTER = /[؀-ۿ]/;
const STAGE_SEPARATOR = ",";
const MAX_STUDENTS = 100_000;
const REGISTRATION_NUMBER_MAX = 20;
const COMPACT = "h-10";

const selectedStages = (value: string) => (value ? value.split(STAGE_SEPARATOR) : []);

function initialValues(demo?: DemoRequest) {
  const schoolName = demo?.school_name ?? "";
  const isArabicName = ARABIC_LETTER.test(schoolName);
  return {
    name_en: isArabicName ? "" : schoolName,
    name_ar: isArabicName ? schoolName : "",
    code: "",
    school_type: "",
    education_stages: "",
    estimated_students: "",
    email: "",
    phone: "",
    region: "",
    city: "",
    address: "",
    cr_number: "",
    moe_license_number: "",
    admin_name: demo?.name ?? "",
    admin_email: demo?.email ?? "",
    admin_phone: demo?.phone ?? "",
  };
}

function FormSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="gap-3 py-4">
      <CardHeader className="px-5">
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-x-4 gap-y-3 px-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {children}
      </CardContent>
    </Card>
  );
}

function SchoolForm({ demo }: { demo?: DemoRequest }) {
  const t = useTranslations("Platform.formPage");
  const tForm = useTranslations("Platform.form");
  const tOptions = useTranslations("Platform.options");
  const router = useRouter();

  const form = useValidatedForm({
    initial: initialValues(demo),
    idPrefix: "school-",
    validateWhileTyping: true,
    validators: {
      name_en: englishName(200),
      name_ar: optionalArabicName(200),
      code: optionalSlug(30),
      school_type: required(20),
      education_stages: required(100),
      estimated_students: wholeNumberInRange(1, MAX_STUDENTS, "students"),
      email,
      phone: optionalPhone,
      region: required(30),
      city: required(100),
      address: required(300),
      cr_number: optionalRegistrationNumber(REGISTRATION_NUMBER_MAX),
      moe_license_number: optionalRegistrationNumber(REGISTRATION_NUMBER_MAX),
      admin_name: required(120),
      admin_email: email,
      admin_phone: requiredMobile,
    },
    sanitizers: {
      code: sanitizeSlug,
      estimated_students: sanitizeDigits,
      phone: sanitizePhone,
      cr_number: sanitizeRegistrationNumber,
      moe_license_number: sanitizeRegistrationNumber,
      admin_phone: sanitizePhone,
    },
    rejectedInputErrors: {
      code: "slugCharacters",
      estimated_students: "digits",
      phone: "phoneCharacters",
      cr_number: "registrationNumber",
      moe_license_number: "registrationNumber",
      admin_phone: "phoneCharacters",
    },
    submit: async (values) => {
      await createSchool({
        ...values,
        education_stages: selectedStages(values.education_stages),
        estimated_students: Number(values.estimated_students),
        demo_request: demo?.id,
      });
    },
    onSuccess: (values) => {
      router.push(`/platform/schools?created=${encodeURIComponent(values.code)}`);
    },
    describeError: (error) => {
      if (!(error instanceof ApiError)) return null;
      if (error.fields?.demo_request) return t("errors.demoConverted");
      return error.fields ? null : t("errors.generic");
    },
    describeFieldError: (name) => {
      if (name === "code") return t("errors.codeTaken");
      return name === "email" || name === "admin_email" ? t("errors.emailTaken") : null;
    },
  });

  const stages = selectedStages(form.values.education_stages);

  function toggleStage(stage: string, checked: boolean) {
    const next = EDUCATION_STAGES.filter((option) =>
      option === stage ? checked : stages.includes(option),
    );
    form.setValue("education_stages", next.join(STAGE_SEPARATOR));
  }

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex max-w-5xl flex-col gap-3">
      {demo && (
        <p role="status" className="rounded-control bg-sky-50 p-3 text-sm text-sky-800">
          {t("fromDemo", { name: demo.name })}
        </p>
      )}

      <FormSection title={t("sectionSchool")}>
        <Field
          id="school-name_en"
          label={tForm("nameEn")}
          required
          error={form.errorFor("name_en")}
        >
          <Input
            {...form.bind("name_en")}
            dir="ltr"
            maxLength={200}
            className={`${COMPACT} rtl:text-end`}
          />
        </Field>
        <Field id="school-name_ar" label={tForm("nameAr")} error={form.errorFor("name_ar")}>
          <Input {...form.bind("name_ar")} dir="rtl" maxLength={200} className={COMPACT} />
        </Field>
        <Field
          id="school-code"
          label={tForm("code")}
          hint={tForm("codeHint")}
          error={form.errorFor("code")}
        >
          <Input
            {...form.bind("code")}
            dir="ltr"
            maxLength={30}
            className={`${COMPACT} rtl:text-end`}
          />
        </Field>
        <Field
          id="school-school_type"
          label={t("type")}
          required
          error={form.errorFor("school_type")}
        >
          <Select {...form.bind("school_type")} className={COMPACT}>
            <option value="">{t("typePlaceholder")}</option>
            {SCHOOL_TYPES.map((type) => (
              <option key={type} value={type}>
                {tOptions(`type.${type}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          id="school-estimated_students"
          label={t("students")}
          required
          error={form.errorFor("estimated_students")}
        >
          <Input
            {...form.bind("estimated_students")}
            dir="ltr"
            inputMode="numeric"
            maxLength={6}
            className={`${COMPACT} rtl:text-end`}
          />
        </Field>
        <Field id="school-cr_number" label={t("crNumber")} error={form.errorFor("cr_number")}>
          <Input
            {...form.bind("cr_number")}
            dir="ltr"
            maxLength={REGISTRATION_NUMBER_MAX}
            className={`${COMPACT} rtl:text-end`}
          />
        </Field>
        <Field
          id="school-moe_license_number"
          label={t("moeLicense")}
          error={form.errorFor("moe_license_number")}
        >
          <Input
            {...form.bind("moe_license_number")}
            dir="ltr"
            maxLength={REGISTRATION_NUMBER_MAX}
            className={`${COMPACT} rtl:text-end`}
          />
        </Field>
        <div className="flex flex-col gap-1 sm:col-span-2 lg:col-span-3 xl:col-span-4">
          <span id="school-stages-label" className="text-sm font-semibold text-ink">
            {t("stages")}
            <span aria-hidden="true" className="ms-0.5 text-red-700">
              *
            </span>
          </span>
          <div
            role="group"
            aria-labelledby="school-stages-label"
            className="grid grid-cols-2 gap-2 lg:grid-cols-4"
          >
            {EDUCATION_STAGES.map((stage) => (
              <label
                key={stage}
                className="flex min-h-10 cursor-pointer items-center gap-2 rounded-control border border-line px-3 text-sm text-ink transition-colors hover:border-navy-line has-checked:border-navy has-checked:bg-navy-soft"
              >
                <input
                  type="checkbox"
                  name="education_stages"
                  checked={stages.includes(stage)}
                  aria-invalid={Boolean(form.errorFor("education_stages"))}
                  onChange={(event) => toggleStage(stage, event.target.checked)}
                  className="size-4 accent-navy"
                />
                {tOptions(`stage.${stage}`)}
              </label>
            ))}
          </div>
          {form.errorFor("education_stages") && (
            <p role="alert" className="text-sm text-red-700">
              {form.errorFor("education_stages")}
            </p>
          )}
        </div>
      </FormSection>

      <FormSection title={t("sectionContact")}>
        <Field id="school-email" label={t("email")} required error={form.errorFor("email")}>
          <Input
            {...form.bind("email")}
            type="email"
            dir="ltr"
            maxLength={254}
            className={`${COMPACT} rtl:text-end`}
          />
        </Field>
        <Field
          id="school-phone"
          label={t("phone")}
          hint={t("phoneHint")}
          error={form.errorFor("phone")}
        >
          <Input
            {...form.bind("phone")}
            type="tel"
            dir="ltr"
            inputMode="tel"
            maxLength={20}
            className={`${COMPACT} rtl:text-end`}
          />
        </Field>
        <Field id="school-region" label={t("region")} required error={form.errorFor("region")}>
          <Select {...form.bind("region")} className={COMPACT}>
            <option value="">{t("regionPlaceholder")}</option>
            {SAUDI_REGIONS.map((region) => (
              <option key={region} value={region}>
                {tOptions(`region.${region}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field id="school-city" label={t("city")} required error={form.errorFor("city")}>
          <Input {...form.bind("city")} maxLength={100} className={COMPACT} />
        </Field>
        <div className="sm:col-span-2">
          <Field id="school-address" label={t("address")} required error={form.errorFor("address")}>
            <Input {...form.bind("address")} maxLength={300} className={COMPACT} />
          </Field>
        </div>
      </FormSection>

      <FormSection title={t("sectionAdmin")}>
        <Field
          id="school-admin_name"
          label={t("adminName")}
          required
          error={form.errorFor("admin_name")}
        >
          <Input {...form.bind("admin_name")} maxLength={120} className={COMPACT} />
        </Field>
        <Field
          id="school-admin_email"
          label={tForm("adminEmail")}
          required
          error={form.errorFor("admin_email")}
        >
          <Input
            {...form.bind("admin_email")}
            type="email"
            dir="ltr"
            maxLength={254}
            className={`${COMPACT} rtl:text-end`}
          />
        </Field>
        <Field
          id="school-admin_phone"
          label={t("adminPhone")}
          hint={t("adminPhoneHint")}
          required
          error={form.errorFor("admin_phone")}
        >
          <Input
            {...form.bind("admin_phone")}
            type="tel"
            dir="ltr"
            inputMode="tel"
            maxLength={20}
            className={`${COMPACT} rtl:text-end`}
          />
        </Field>
      </FormSection>

      {form.formError && (
        <p role="alert" className="rounded-control bg-red-50 p-3 text-sm text-red-800">
          {form.formError}
        </p>
      )}

      <div className="flex flex-wrap justify-end gap-2">
        <Link href="/platform/schools" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          {tForm("cancel")}
        </Link>
        <Button type="submit" size="sm" loading={form.saving}>
          {form.saving ? tForm("submitting") : tForm("submit")}
        </Button>
      </div>
    </form>
  );
}

function SchoolFormFromDemo({ demoId }: { demoId: number }) {
  const t = useTranslations("Platform.formPage");
  const { state, reload } = useLoad((signal) => getDemoRequest(demoId, signal), String(demoId));

  if (state.name !== "ready") {
    return (
      <>
        <LoadFeedback state={state} onRetry={reload} />
        {state.name === "failed" && <p className="text-sm text-ink-soft">{t("demoUnavailable")}</p>}
      </>
    );
  }
  if (state.data.status === "converted") {
    return (
      <p role="alert" className="rounded-control bg-amber-50 p-3 text-sm text-amber-800">
        {t("demoAlreadyConverted")}
      </p>
    );
  }
  return <SchoolForm demo={state.data} />;
}

function NewSchoolContent() {
  const t = useTranslations("Platform.formPage");
  const tForm = useTranslations("Platform.form");
  const demoParam = useSearchParams().get("demo");
  const demoId = demoParam && /^[0-9]+$/.test(demoParam) ? Number(demoParam) : null;

  return (
    <>
      <Link
        href="/platform/schools"
        className="inline-flex w-fit items-center gap-1.5 text-sm font-semibold text-navy hover:underline"
      >
        <ArrowLeft aria-hidden="true" className="size-4 rtl:rotate-180" />
        {t("back")}
      </Link>
      <PageHeader title={tForm("title")} subtitle={t("subtitle")} />
      {demoId ? <SchoolFormFromDemo key={demoId} demoId={demoId} /> : <SchoolForm />}
    </>
  );
}

export function NewSchoolPanel() {
  const [resetKey, setResetKey] = useState(0);

  // Next.js keeps this page's state after navigating away (cacheComponents).
  // Start clean on return, so the last school's details never come back.
  useEffect(() => () => setResetKey((current) => current + 1), []);

  return <NewSchoolContent key={resetKey} />;
}
