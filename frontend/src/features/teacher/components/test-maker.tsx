"use client";

import { useEffect, useRef, useState, type DragEvent } from "react";
import {
  Bookmark,
  Check,
  FileText,
  FileUp,
  Minus,
  PencilLine,
  Plus,
  Shuffle,
  Sparkles,
  X,
  Zap,
} from "lucide-react";
import { cn } from "cn";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { useLoad } from "@/features/platform/use-load";
import { ApiError } from "@/lib/api";
import {
  optional,
  required,
  sanitizeDigits,
  useValidatedForm,
  wholeNumberInRange,
  type ErrorKey,
} from "@/lib/use-validated-form";
import {
  createExamDraft,
  createExamPattern,
  deleteExamPattern,
  getExamDraft,
  listClasses,
  listExamPatterns,
  uploadExamSource,
} from "../api";
import {
  DIFFICULTIES,
  QUESTION_KINDS,
  type Difficulty,
  type ExamDraft,
  type ExamOptions,
  type ExamSection,
  type QuestionKind,
  type SourceDocument,
} from "../schemas";
import { ConfirmDelete, ErrorNote, useTeacherError, useWorkspace } from "./teacher-ui";

const STEPS = ["upload", "pattern", "review", "design"] as const;
const UPLOAD_ERRORS = [
  "not_pdf",
  "pdf_locked",
  "pdf_too_many_pages",
  "pdf_unreadable",
  "pdf_no_text",
  "pdf_too_large",
] as const;
const WRITING_ERRORS = ["service_unavailable", "no_questions", "timed_out"] as const;
const WRITING_STEPS = ["read", "topics", "write", "check"] as const;
const POLL_MS = 2000;
/** About five minutes; the server gives up on a draft well before that. */
const MAX_POLLS = 150;
const MARKS_PATTERN = /^\d{1,3}(\.\d{1,2})?$/;

/** Marks from 0.25 to 100, with up to two decimals. Matches the API. */
export const marksValidator = (value: string): ErrorKey | null => {
  const trimmed = value.trim();
  if (!trimmed) return "required";
  const number = Number(trimmed);
  return MARKS_PATTERN.test(trimmed) && number >= 0.25 && number <= 100 ? null : "marks";
};

/** Digits and one decimal point, so marks can be typed with an Arabic keyboard too. */
export const sanitizeMarks = (value: string) =>
  value
    .replace(/[٠-٩]/g, (digit) => String(digit.charCodeAt(0) - 0x0660))
    .replace(/[٫،,]/g, ".")
    .replace(/[^0-9.]/g, "")
    .replace(/(\..*)\./g, "$1");

/** The four steps of making a test. The first two are here; the editor shows the rest. */
export function Stepper({ current }: { current: (typeof STEPS)[number] }) {
  const t = useTranslations("Teacher.tests.steps");
  const index = STEPS.indexOf(current);
  return (
    <ol className="flex flex-wrap items-center gap-2 text-sm" aria-label={t("label")}>
      {STEPS.map((step, position) => (
        <li
          key={step}
          aria-current={position === index ? "step" : undefined}
          className="flex items-center gap-2"
        >
          <span
            aria-hidden="true"
            className={cn(
              "flex size-7 items-center justify-center rounded-full border text-xs font-bold",
              position < index && "border-navy bg-navy text-on-dark",
              position === index && "border-navy text-navy",
              position > index && "border-line text-ink-soft",
            )}
          >
            {position < index ? <Check className="size-3.5" /> : position + 1}
          </span>
          <span className={position === index ? "font-semibold text-ink" : "text-ink-soft"}>
            {t(step)}
          </span>
          {position < STEPS.length - 1 && (
            <span aria-hidden="true" className="mx-1 h-px w-6 bg-line" />
          )}
        </li>
      ))}
    </ol>
  );
}

export function useAiTestAllowance() {
  const { workspace } = useWorkspace();
  const limit = workspace.limits.ai_exams;
  const used = workspace.usage.ai_exams_used;
  return { used, limit, left: Math.max(limit - used, 0), period: workspace.limits.ai_period };
}

type Details = {
  title: string;
  subject: string;
  grade: string;
  language: "en" | "ar";
  classroom: number | null;
  page_from: number;
  page_to: number;
};

// --- Step 1: the PDF and the test's details

function UploadStep({
  options,
  initial,
  onCancel,
  onNext,
}: {
  options: ExamOptions;
  initial: { source: SourceDocument | null; values: Record<string, string> } | null;
  onCancel: () => void;
  onNext: (source: SourceDocument, details: Details, values: Record<string, string>) => void;
}) {
  const t = useTranslations("Teacher.tests");
  const locale = useLocale();
  const describe = useTeacherError();
  const { workspace } = useWorkspace();
  const classes = useLoad(listClasses, "test-classes");
  const [source, setSource] = useState<SourceDocument | null>(initial?.source ?? null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const { max_pdf_mb: maxMb, max_pdf_pages: maxPages } = options.limits;

  const pageCount = source?.page_count ?? maxPages;
  const form = useValidatedForm<Record<string, string>>({
    initial: initial?.values ?? {
      title: "",
      subject: workspace.profile?.subject ?? "",
      grade: "",
      language: locale === "ar" ? "ar" : "en",
      classroom: "",
      page_from: "",
      page_to: "",
    },
    idPrefix: "test-",
    validators: {
      title: required(200),
      subject: optional(100),
      grade: optional(50),
      page_from: wholeNumberInRange(1, pageCount, "pageNumber"),
      page_to: (value, all) =>
        wholeNumberInRange(1, pageCount, "pageNumber")(value, all) ??
        (Number(value) < Number(all.page_from) ? "pageOrder" : null),
    },
    sanitizers: { page_from: sanitizeDigits, page_to: sanitizeDigits },
    submit: async (values) => {
      if (!source) {
        setUploadError(t("upload.needFile"));
        fileInput.current?.focus();
        return;
      }
      onNext(
        source,
        {
          title: values.title.trim(),
          subject: values.subject.trim(),
          grade: values.grade.trim(),
          language: values.language === "ar" ? "ar" : "en",
          classroom: values.classroom ? Number(values.classroom) : null,
          page_from: Number(values.page_from),
          page_to: Number(values.page_to),
        },
        values,
      );
    },
  });

  async function upload(file: File) {
    setUploadError(null);
    const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) return setUploadError(t("upload.errors.not_pdf"));
    if (file.size > maxMb * 1024 * 1024) {
      return setUploadError(t("upload.errors.pdf_too_large", { mb: maxMb }));
    }

    setUploading(true);
    try {
      const document = await uploadExamSource(file);
      setSource(document);
      const pages = document.text_pages;
      form.setValue("page_from", String(pages[0] ?? 1));
      form.setValue("page_to", String(pages.at(-1) ?? document.page_count));
      if (!form.values.title.trim()) {
        form.setValue("title", file.name.replace(/\.pdf$/i, "").slice(0, 200));
      }
    } catch (err) {
      const code = UPLOAD_ERRORS.find((item) => err instanceof ApiError && err.code === item);
      setUploadError(
        code
          ? t(`upload.errors.${code}`, { mb: maxMb, pages: maxPages })
          : (describe(err) ?? t("upload.errors.generic")),
      );
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file && !uploading) void upload(file);
  }

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-4">
      <section className="rounded-card border border-line bg-bg p-5">
        <h2 className="text-lg text-navy-deep">{t("upload.title")}</h2>
        <p className="mt-1 text-sm text-ink-soft">{t("upload.hint")}</p>
        <label
          htmlFor="test-file"
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={cn(
            "mt-4 flex cursor-pointer flex-col items-center gap-2 rounded-card border-2 border-dashed px-4 py-8 text-center transition-colors",
            dragging ? "border-navy bg-navy-soft" : "border-line hover:border-navy-line",
            uploadError && "border-red-600",
          )}
        >
          {uploading ? (
            <span role="status" className="flex items-center gap-2 text-sm text-ink">
              <Spinner />
              {t("upload.uploading")}
            </span>
          ) : (
            <>
              <FileUp aria-hidden="true" className="size-8 text-navy" />
              <span className="font-semibold text-navy">
                {source ? t("upload.replace") : t("upload.choose")}
              </span>
              <span className="text-sm text-ink-soft">{t("upload.drop")}</span>
              <span className="text-xs text-ink-soft">
                {t("upload.limits", { mb: maxMb, pages: maxPages })}
              </span>
            </>
          )}
          <input
            ref={fileInput}
            id="test-file"
            type="file"
            accept="application/pdf,.pdf"
            className="sr-only"
            disabled={uploading}
            aria-describedby={uploadError ? "test-file-error" : undefined}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file);
            }}
          />
        </label>
        {uploadError && (
          <p id="test-file-error" role="alert" className="mt-2 text-sm text-red-700">
            {uploadError}
          </p>
        )}
        {source && !uploading && (
          <div className="mt-3 rounded-control bg-bg-tint p-3 text-sm">
            <p className="font-semibold break-all text-ink">{source.filename}</p>
            <p className="mt-0.5 text-ink-soft">
              {t("upload.pages", { count: source.page_count })} ·{" "}
              {t("upload.textPages", { count: source.text_pages.length })}
            </p>
            {source.preview && (
              <p className="mt-2 line-clamp-3 text-ink-soft" dir="auto">
                {source.preview}
              </p>
            )}
          </div>
        )}
        <p className="mt-3 text-xs text-ink-soft">{t("upload.privacy")}</p>
      </section>

      <section className="flex flex-col gap-3 rounded-card border border-line bg-bg p-5">
        <h2 className="text-lg text-navy-deep">{t("details.title")}</h2>
        <Field
          id="test-title"
          label={t("details.testTitle")}
          required
          error={form.errorFor("title")}
        >
          <Input {...form.bind("title")} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field id="test-subject" label={t("details.subject")} error={form.errorFor("subject")}>
            <Input {...form.bind("subject")} />
          </Field>
          <Field id="test-grade" label={t("details.grade")} error={form.errorFor("grade")}>
            <Input {...form.bind("grade")} />
          </Field>
          <Field id="test-language" label={t("details.language")} hint={t("details.languageHint")}>
            <Select {...form.bind("language")} className="h-11">
              <option value="en">English</option>
              <option value="ar">العربية</option>
            </Select>
          </Field>
        </div>
        <Field id="test-classroom" label={t("details.classroom")}>
          <Select {...form.bind("classroom")} className="h-11">
            <option value="">{t("details.noClass")}</option>
            {classes.state.name === "ready" &&
              classes.state.data.map((classroom) => (
                <option key={classroom.id} value={classroom.id}>
                  {classroom.name}
                </option>
              ))}
          </Select>
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field
            id="test-page_from"
            label={t("details.pageFrom")}
            required
            error={form.errorFor("page_from")}
          >
            <Input {...form.bind("page_from")} inputMode="numeric" disabled={!source} />
          </Field>
          <Field
            id="test-page_to"
            label={t("details.pageTo")}
            required
            error={form.errorFor("page_to")}
          >
            <Input {...form.bind("page_to")} inputMode="numeric" disabled={!source} />
          </Field>
        </div>
        <p className="text-xs text-ink-soft">{t("details.pagesHint")}</p>
      </section>

      <ErrorNote message={form.formError} />
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" size="sm" onClick={onCancel}>
          {t("cancel")}
        </Button>
        <Button type="submit" size="sm" disabled={uploading}>
          {t("next")}
        </Button>
      </div>
    </form>
  );
}

// --- Step 2: the pattern

const CARD_ICONS = { quick_quiz: Zap, mixed: Shuffle, exam: FileText } as const;
const countKey = (kind: QuestionKind) => `${kind}_count`;
const marksKey = (kind: QuestionKind) => `${kind}_marks`;
/** Marks each kind gets when the teacher first ticks it. */
const START_MARKS: Record<QuestionKind, string> = {
  mcq: "1",
  true_false: "1",
  fill_blank: "1",
  short_answer: "3",
};
const START_COUNT = 5;

function totals(sections: ExamSection[]) {
  return {
    questions: sections.reduce((sum, section) => sum + section.count, 0),
    marks: Number(
      sections
        .reduce((sum, section) => sum + section.count * (Number(section.marks) || 0), 0)
        .toFixed(2),
    ),
  };
}

/** The editor's values from a pattern: one row per question type, 0 when it isn't used. */
function editorValues(sections: ExamSection[]) {
  const values: Record<string, string> = { name: "" };
  for (const kind of QUESTION_KINDS) {
    const used = sections.filter((section) => section.kind === kind);
    values[countKey(kind)] = String(used.reduce((sum, section) => sum + section.count, 0));
    values[marksKey(kind)] = used[0] ? String(Number(used[0].marks)) : START_MARKS[kind];
  }
  return values;
}

function PatternCard({
  title,
  lines,
  summary,
  icon: Icon,
  chosen,
  onChoose,
  onDelete,
  deleteLabel,
}: {
  title: string;
  lines: string[];
  summary: string;
  icon: typeof Zap;
  chosen: boolean;
  onChoose: () => void;
  onDelete?: () => void;
  deleteLabel?: string;
}) {
  return (
    <li className="relative">
      <button
        type="button"
        aria-pressed={chosen}
        onClick={onChoose}
        className={cn(
          "flex h-full w-full cursor-pointer flex-col items-start gap-2 rounded-card border-2 p-4 text-start transition-colors",
          chosen ? "border-navy bg-navy-soft" : "border-line bg-bg hover:border-navy-line",
        )}
      >
        <span className="flex w-full items-center justify-between gap-2">
          <span
            aria-hidden="true"
            className={cn(
              "flex size-9 items-center justify-center rounded-control",
              chosen ? "bg-navy text-on-dark" : "bg-bg-tint text-navy",
            )}
          >
            <Icon className="size-5" />
          </span>
          {chosen && <Check aria-hidden="true" className="size-5 text-navy" />}
        </span>
        <span className="font-bold text-navy-deep">{title}</span>
        <span className="flex flex-col text-sm text-ink-soft">
          {lines.map((line) => (
            <span key={line}>{line}</span>
          ))}
        </span>
        <span className="mt-auto pt-1 text-sm font-semibold text-navy tabular-nums">{summary}</span>
      </button>
      {onDelete && (
        <button
          type="button"
          aria-label={deleteLabel}
          onClick={onDelete}
          className="absolute end-3 bottom-3 flex size-8 cursor-pointer items-center justify-center rounded-control text-ink-soft hover:bg-bg hover:text-navy"
        >
          <X aria-hidden="true" className="size-4" />
        </button>
      )}
    </li>
  );
}

function PatternStep({
  options,
  details,
  sourceId,
  onBack,
  onStarted,
}: {
  options: ExamOptions;
  details: Details;
  sourceId: number;
  onBack: () => void;
  onStarted: (draft: ExamDraft) => void;
}) {
  const t = useTranslations("Teacher.tests");
  const describe = useTeacherError();
  const allowance = useAiTestAllowance();
  const patterns = useLoad(listExamPatterns, "exam-patterns");
  const maxCount = options.limits.max_section_questions;
  const firstPreset = options.presets[0];
  const [chosen, setChosen] = useState(firstPreset ? `preset:${firstPreset.key}` : "own");
  const [level, setLevel] = useState<Difficulty>("medium");
  const [saveIt, setSaveIt] = useState(false);
  const [removing, setRemoving] = useState<{ id: number; name: string } | null>(null);
  const own = chosen === "own";

  const savedPatterns = patterns.state.name === "ready" ? patterns.state.data : [];
  const chosenSections = (): ExamSection[] => {
    if (chosen.startsWith("preset:")) {
      return options.presets.find((preset) => `preset:${preset.key}` === chosen)?.sections ?? [];
    }
    if (chosen.startsWith("pattern:")) {
      return savedPatterns.find((pattern) => `pattern:${pattern.id}` === chosen)?.sections ?? [];
    }
    return [];
  };

  const countValidator = wholeNumberInRange(0, maxCount, "questionCount");
  const validators: Record<
    string,
    (value: string, all: Record<string, string>) => ErrorKey | null
  > = {};
  // The editor is checked only when the teacher is making their own pattern.
  if (own) {
    for (const kind of QUESTION_KINDS) {
      validators[countKey(kind)] = countValidator;
      validators[marksKey(kind)] = (value, all) =>
        Number(all[countKey(kind)]) > 0 ? marksValidator(value) : null;
    }
    if (saveIt) validators.name = required(100);
  }

  /** The sections to send: the chosen card's, or the editor's rows with questions in them. */
  const sectionsFrom = (values: Record<string, string>): ExamSection[] =>
    (own
      ? QUESTION_KINDS.filter((kind) => Number(values[countKey(kind)]) > 0).map((kind) => ({
          kind,
          count: Number(values[countKey(kind)]),
          marks: values[marksKey(kind)].trim(),
          difficulty: level,
        }))
      : chosenSections()
    ).map((section) => ({ ...section, difficulty: level }));

  const form = useValidatedForm<Record<string, string>>({
    initial: editorValues(firstPreset?.sections ?? []),
    idPrefix: "pattern-",
    validators,
    sanitizers: Object.fromEntries(
      QUESTION_KINDS.flatMap((kind) => [
        [countKey(kind), sanitizeDigits],
        [marksKey(kind), sanitizeMarks],
      ]),
    ),
    submit: async (values) => {
      const sections = sectionsFrom(values);
      if (own && saveIt) {
        const pattern = await createExamPattern({ name: values.name.trim(), sections });
        // Saved once: trying again after a failed draft doesn't save it twice.
        setSaveIt(false);
        setChosen(`pattern:${pattern.id}`);
        patterns.reload();
      }
      const draft = await createExamDraft({ ...details, source: sourceId, sections });
      onStarted(draft);
    },
    describeError: describe,
    describeFieldError: (name) => (name === "name" ? t("pattern.nameTaken") : null),
  });

  function choose(key: string) {
    // "Make my own" starts from what was chosen, so a ready pattern is easy to change.
    if (key === "own" && !own) form.reset(editorValues(chosenSections()));
    setChosen(key);
  }

  function setCount(kind: QuestionKind, value: number) {
    form.setValue(countKey(kind), String(Math.min(Math.max(value, 0), maxCount)));
  }

  const sections = sectionsFrom(form.values);
  const total = totals(sections);
  const tooMany = total.questions > options.limits.max_ai_questions;
  const empty = total.questions === 0;
  const cardSummary = (cardSections: ExamSection[]) => {
    const { questions, marks } = totals(cardSections);
    return t("pattern.summary", { questions, marks });
  };
  const cardLines = (cardSections: ExamSection[]) =>
    cardSections.map((section) =>
      t("pattern.kindCount", { count: section.count, kind: t(`kinds.${section.kind}`) }),
    );

  return (
    <>
      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-4">
        <section className="flex flex-col gap-4 rounded-card border border-line bg-bg p-5">
          <div>
            <h2 className="text-lg text-navy-deep">{t("pattern.title")}</h2>
            <p className="mt-1 text-sm text-ink-soft">{t("pattern.hint")}</p>
          </div>

          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {options.presets.map((preset) => (
              <PatternCard
                key={preset.key}
                title={t(`pattern.presets.${preset.key}`)}
                lines={cardLines(preset.sections)}
                summary={cardSummary(preset.sections)}
                icon={CARD_ICONS[preset.key]}
                chosen={chosen === `preset:${preset.key}`}
                onChoose={() => choose(`preset:${preset.key}`)}
              />
            ))}
            {savedPatterns.map((pattern) => (
              <PatternCard
                key={pattern.id}
                title={pattern.name}
                lines={cardLines(pattern.sections)}
                summary={cardSummary(pattern.sections)}
                icon={Bookmark}
                chosen={chosen === `pattern:${pattern.id}`}
                onChoose={() => choose(`pattern:${pattern.id}`)}
                onDelete={() => setRemoving({ id: pattern.id, name: pattern.name })}
                deleteLabel={t("pattern.deletePattern", { name: pattern.name })}
              />
            ))}
            <PatternCard
              title={t("pattern.own")}
              lines={[t("pattern.ownHint")]}
              summary={own ? t("pattern.summary", total) : ""}
              icon={PencilLine}
              chosen={own}
              onChoose={() => choose("own")}
            />
          </ul>

          {own && (
            <div className="flex flex-col gap-3 rounded-tile border border-line bg-bg-tint/40 p-3 sm:p-4">
              <div className="hidden grid-cols-[1fr_auto_120px] gap-3 px-1 text-xs font-bold tracking-wide text-ink-soft uppercase sm:grid">
                <span>{t("pattern.kind")}</span>
                <span className="w-[136px] text-center">{t("pattern.count")}</span>
                <span>{t("pattern.marks")}</span>
              </div>
              {QUESTION_KINDS.map((kind) => {
                const count = Number(form.values[countKey(kind)]) || 0;
                const kindName = t(`kinds.${kind}`);
                return (
                  <div
                    key={kind}
                    className={cn(
                      "grid grid-cols-[1fr_auto] items-start gap-3 rounded-control bg-bg p-3 sm:grid-cols-[1fr_auto_120px]",
                      count === 0 && "opacity-70",
                    )}
                  >
                    <label className="flex min-h-11 cursor-pointer items-center gap-2 text-sm font-semibold text-ink">
                      <input
                        type="checkbox"
                        checked={count > 0}
                        onChange={(event) => setCount(kind, event.target.checked ? START_COUNT : 0)}
                        className="size-4"
                      />
                      {kindName}
                    </label>
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          aria-label={t("pattern.fewer", { kind: kindName })}
                          disabled={count === 0}
                          onClick={() => setCount(kind, count - 1)}
                          className="flex size-11 cursor-pointer items-center justify-center rounded-control border border-line text-navy hover:bg-navy-soft disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          <Minus aria-hidden="true" className="size-4" />
                        </button>
                        <Input
                          {...form.bind(countKey(kind))}
                          aria-label={t("pattern.countFor", { kind: kindName })}
                          inputMode="numeric"
                          className="h-11 w-12 px-1 text-center tabular-nums"
                        />
                        <button
                          type="button"
                          aria-label={t("pattern.more", { kind: kindName })}
                          disabled={count >= maxCount}
                          onClick={() => setCount(kind, count + 1)}
                          className="flex size-11 cursor-pointer items-center justify-center rounded-control border border-line text-navy hover:bg-navy-soft disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          <Plus aria-hidden="true" className="size-4" />
                        </button>
                      </div>
                      {form.errorFor(countKey(kind)) && (
                        <p role="alert" className="text-xs text-red-700">
                          {form.errorFor(countKey(kind))}
                        </p>
                      )}
                    </div>
                    {count > 0 && (
                      <div className="col-span-2 sm:col-span-1">
                        <Field
                          id={`pattern-${marksKey(kind)}`}
                          label={t("pattern.marksFor", { kind: kindName })}
                          error={form.errorFor(marksKey(kind))}
                        >
                          <Input
                            {...form.bind(marksKey(kind))}
                            inputMode="decimal"
                            className="h-11"
                          />
                        </Field>
                      </div>
                    )}
                  </div>
                );
              })}

              <label className="flex cursor-pointer items-center gap-2 pt-1 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={saveIt}
                  onChange={(event) => setSaveIt(event.target.checked)}
                  className="size-4"
                />
                {t("pattern.saveAs")}
              </label>
              {saveIt && (
                <Field
                  id="pattern-name"
                  label={t("pattern.patternName")}
                  required
                  error={form.errorFor("name")}
                >
                  <Input {...form.bind("name")} className="h-11" />
                </Field>
              )}
            </div>
          )}

          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 text-sm font-semibold text-ink">{t("pattern.level")}</legend>
            <div className="inline-flex w-fit rounded-control border border-line bg-bg p-1">
              {DIFFICULTIES.map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={level === item}
                  onClick={() => setLevel(item)}
                  className={cn(
                    "min-h-10 cursor-pointer rounded-control px-4 text-sm font-semibold transition-colors",
                    level === item ? "bg-navy text-on-dark" : "text-navy hover:bg-navy-soft",
                  )}
                >
                  {t(`levels.${item}`)}
                </button>
              ))}
            </div>
          </fieldset>
          <p className="text-xs text-ink-soft">{t("upload.privacy")}</p>
        </section>

        <div className="sticky bottom-0 z-10 flex flex-col gap-2 rounded-card border border-line bg-bg p-4 shadow-soft">
          {tooMany && (
            <p role="alert" className="text-sm text-red-700">
              {t("pattern.tooMany", { max: options.limits.max_ai_questions })}
            </p>
          )}
          {empty && (
            <p role="alert" className="text-sm text-red-700">
              {t("pattern.noneChosen")}
            </p>
          )}
          <ErrorNote message={form.formError} />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-col">
              <span className="font-bold text-navy-deep tabular-nums" aria-live="polite">
                {t("pattern.summary", total)}
              </span>
              <span className="text-xs text-ink-soft">
                {t("pattern.aiLeft", { left: allowance.left, limit: allowance.limit })}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" size="sm" onClick={onBack}>
                {t("back")}
              </Button>
              <Button
                type="submit"
                variant="orange"
                size="sm"
                loading={form.saving}
                disabled={tooMany || empty || allowance.left === 0}
              >
                <Sparkles aria-hidden="true" className="size-4" />
                {t("pattern.make")}
              </Button>
            </div>
          </div>
        </div>
      </form>

      {removing && (
        <ConfirmDelete
          title={t("pattern.deleteTitle", { name: removing.name })}
          body={t("pattern.deleteBody")}
          onConfirm={async () => {
            await deleteExamPattern(removing.id);
            if (chosen === `pattern:${removing.id}`) {
              choose(firstPreset ? `preset:${firstPreset.key}` : "own");
            }
            patterns.reload();
          }}
          onClose={() => setRemoving(null)}
        />
      )}
    </>
  );
}

// --- Step 3: the AI writes

function Writing({
  draft,
  onReady,
  onFailed,
}: {
  draft: ExamDraft;
  onReady: (draft: ExamDraft) => void;
  onFailed: (error: string) => void;
}) {
  const t = useTranslations("Teacher.tests.writing");
  const [step, setStep] = useState(0);
  const callbacks = useRef({ onReady, onFailed });
  useEffect(() => {
    callbacks.current = { onReady, onFailed };
  });

  useEffect(() => {
    const timer = window.setInterval(
      () => setStep((current) => Math.min(current + 1, WRITING_STEPS.length - 1)),
      3500,
    );
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let timer = 0;
    let polls = 0;

    async function check() {
      try {
        const latest = await getExamDraft(draft.id, controller.signal);
        if (latest.status === "ready") return callbacks.current.onReady(latest);
        if (latest.status === "failed") return callbacks.current.onFailed(latest.error);
      } catch {
        // A dropped connection: try again on the next round.
        if (controller.signal.aborted) return;
      }
      polls += 1;
      if (polls >= MAX_POLLS) return callbacks.current.onFailed("timed_out");
      timer = window.setTimeout(check, POLL_MS);
    }

    timer = window.setTimeout(check, POLL_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [draft.id]);

  return (
    <section
      role="status"
      aria-live="polite"
      className="flex flex-col gap-4 rounded-card border border-line bg-bg p-5"
    >
      <h2 className="text-lg text-navy-deep">{t("title")}</h2>
      <div className="h-1.5 overflow-hidden rounded-full bg-bg-tint">
        <div
          className="h-full rounded-full bg-navy transition-[inline-size] duration-700"
          style={{ inlineSize: `${((step + 1) / WRITING_STEPS.length) * 100}%` }}
        />
      </div>
      <ol className="flex flex-col gap-2.5">
        {WRITING_STEPS.map((item, index) => (
          <li
            key={item}
            className={cn(
              "flex items-center gap-3 text-sm transition-opacity",
              index > step ? "opacity-40" : "opacity-100",
            )}
          >
            <span
              aria-hidden="true"
              className={cn(
                "flex size-6 shrink-0 items-center justify-center rounded-full border",
                index < step && "border-navy bg-navy text-on-dark",
                index === step && "animate-pulse border-navy text-navy",
                index > step && "border-line text-ink-soft",
              )}
            >
              {index < step ? <Check className="size-3.5" /> : index + 1}
            </span>
            <span className={index === step ? "font-semibold text-ink" : "text-ink-soft"}>
              {t(`steps.${item}`)}
            </span>
          </li>
        ))}
      </ol>
      <p className="text-xs text-ink-soft">{t("wait")}</p>
    </section>
  );
}

function WritingFailed({ error, onRetry }: { error: string; onRetry: () => void }) {
  const t = useTranslations("Teacher.tests.writing");
  const known = WRITING_ERRORS.find((item) => item === error) ?? "service_unavailable";
  return (
    <section className="flex flex-col items-start gap-3 rounded-card border border-line bg-bg p-5">
      <h2 className="text-lg text-navy-deep">{t("failedTitle")}</h2>
      <p role="alert" className="text-sm text-red-700">
        {t(`errors.${known}`)}
      </p>
      <p className="text-sm text-ink-soft">{t("notCounted")}</p>
      <Button size="sm" onClick={onRetry}>
        {t("tryAgain")}
      </Button>
    </section>
  );
}

type Step =
  | { name: "upload" }
  | { name: "pattern"; source: SourceDocument; details: Details }
  | { name: "writing"; draft: ExamDraft }
  | { name: "failed"; error: string };

/** Upload a PDF, choose a pattern, and wait while the AI writes. Ends with a draft. */
export function TestMaker({
  options,
  onCancel,
  onDraft,
}: {
  options: ExamOptions;
  onCancel: () => void;
  onDraft: (draft: ExamDraft) => void;
}) {
  const t = useTranslations("Teacher.tests");
  const { reload } = useWorkspace();
  const [step, setStep] = useState<Step>({ name: "upload" });
  // Kept, so going back to the first step shows what was chosen.
  const [first, setFirst] = useState<{
    source: SourceDocument | null;
    values: Record<string, string>;
    details: Details | null;
  } | null>(null);

  function started(draft: ExamDraft) {
    // The draft holds a place in the allowance while it is being written.
    reload();
    if (draft.status === "ready") onDraft(draft);
    else if (draft.status === "failed") setStep({ name: "failed", error: draft.error });
    else setStep({ name: "writing", draft });
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3">
        <h1 className="text-2xl text-navy-deep">{t("makeTitle")}</h1>
        <Stepper current={step.name === "upload" ? "upload" : "pattern"} />
      </div>

      {step.name === "upload" && (
        <UploadStep
          options={options}
          initial={first}
          onCancel={onCancel}
          onNext={(source, details, values) => {
            setFirst({ source, values, details });
            setStep({ name: "pattern", source, details });
          }}
        />
      )}
      {step.name === "pattern" && (
        <PatternStep
          options={options}
          details={step.details}
          sourceId={step.source.id}
          onBack={() => setStep({ name: "upload" })}
          onStarted={started}
        />
      )}
      {step.name === "writing" && (
        <Writing
          draft={step.draft}
          onReady={(draft) => {
            reload();
            onDraft(draft);
          }}
          onFailed={(error) => {
            reload();
            setStep({ name: "failed", error });
          }}
        />
      )}
      {step.name === "failed" && (
        <WritingFailed
          error={step.error}
          onRetry={() =>
            first?.source && first.details
              ? setStep({ name: "pattern", source: first.source, details: first.details })
              : setStep({ name: "upload" })
          }
        />
      )}
    </div>
  );
}
