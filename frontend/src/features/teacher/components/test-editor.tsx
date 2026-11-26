"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Palette, Plus, RefreshCw, Sparkles, Trash2, X } from "lucide-react";
import { cn } from "cn";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { ActionMenu } from "@/components/ui/action-menu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DateField } from "@/components/ui/date-field";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { useLoad } from "@/features/platform/use-load";
import { ApiError } from "@/lib/api";
import {
  dayDate,
  dayDateToIso,
  isoToDayDate,
  maskDayDate,
  optional,
  optionalWholeNumber,
  required,
  requiredChoice,
  sanitizeDigits,
  useValidatedForm,
  type ErrorKey,
} from "@/lib/use-validated-form";
import { createExam, listClasses, regenerateExamQuestion, updateExam } from "../api";
import {
  QUESTION_KINDS,
  type ExamDetail,
  type ExamDraft,
  type ExamOptions,
  type ExamQuestion,
  type QuestionKind,
} from "../schemas";
import { marksValidator, sanitizeMarks, Stepper } from "./test-maker";
import { ErrorNote, useTeacherError, useWorkspace } from "./teacher-ui";

const MIN_OPTIONS = 2;
const MAX_OPTIONS = 6;
const LETTERS = {
  en: ["A", "B", "C", "D", "E", "F"],
  ar: ["أ", "ب", "ج", "د", "هـ", "و"],
} as const;
const BLANKS = /_{3,}/g;

type Item = {
  id: number;
  kind: QuestionKind;
  /** Ids of the choice inputs, in order. Multiple choice only. */
  options: number[];
  difficulty: ExamQuestion["difficulty"];
  sourcePage: number | null;
};

const key = (id: number, field: string) => `q${id}_${field}`;
const optionKey = (id: number, slot: number) => `q${id}_o${slot}`;

const blankQuestion = (kind: QuestionKind): ExamQuestion => ({
  kind,
  text: "",
  options: kind === "mcq" ? ["", "", "", ""] : [],
  correct_option: null,
  answer: "",
  explanation: "",
  marks: "1",
  difficulty: "medium",
  source_page: null,
});

/** "2.00" reads better as "2" in the form. */
const shortMarks = (marks: string) => (marks ? String(Number(marks)) : "");

/** The form values and the question list for one question. */
function questionState(question: ExamQuestion, id: number, nextSlot: () => number) {
  const slots = question.kind === "mcq" ? question.options.map(() => nextSlot()) : [];
  const values: Record<string, string> = {
    [key(id, "text")]: question.text,
    [key(id, "answer")]: question.answer,
    [key(id, "explanation")]: question.explanation,
    [key(id, "marks")]: shortMarks(question.marks),
    [key(id, "correct")]:
      question.correct_option !== null && slots[question.correct_option] !== undefined
        ? String(slots[question.correct_option])
        : "",
  };
  slots.forEach((slot, index) => {
    values[optionKey(id, slot)] = question.options[index] ?? "";
  });
  const item: Item = {
    id,
    kind: question.kind,
    options: slots,
    difficulty: question.difficulty,
    sourcePage: question.source_page,
  };
  return { item, values };
}

const sameText = (value: string) => value.trim().toLocaleLowerCase();

function QuestionCard({
  item,
  number,
  total,
  form,
  letters,
  canRewrite,
  rewriting,
  rewriteError,
  onRewrite,
  onMove,
  onRemove,
  onAddOption,
  onRemoveOption,
}: {
  item: Item;
  number: number;
  total: number;
  form: ReturnType<typeof useValidatedForm<Record<string, string>>>;
  letters: readonly string[];
  canRewrite: boolean;
  rewriting: boolean;
  rewriteError: string | null;
  onRewrite: () => void;
  onMove: (step: -1 | 1) => void;
  onRemove: () => void;
  onAddOption: () => void;
  onRemoveOption: (slot: number) => void;
}) {
  const t = useTranslations("Teacher.tests");
  const id = item.id;

  return (
    <li className="rounded-card border border-line bg-bg p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="flex flex-wrap items-center gap-2 text-sm font-bold text-navy-deep">
          {t("editor.questionLabel", { number })}
          <Badge tone="navy">{t(`kinds.${item.kind}`)}</Badge>
          {item.sourcePage && (
            <Badge tone="neutral">{t("editor.fromPage", { page: item.sourcePage })}</Badge>
          )}
        </p>
        {/* Phones: one "⋯" button in place of the row below. */}
        <ActionMenu
          className="sm:hidden"
          label={t("editor.more", { number })}
          items={[
            ...(canRewrite
              ? [
                  {
                    label: t("editor.rewrite"),
                    icon: <RefreshCw aria-hidden="true" className="size-4" />,
                    onSelect: onRewrite,
                    disabled: rewriting,
                  },
                ]
              : []),
            {
              label: t("editor.menuMoveUp"),
              icon: <ArrowUp aria-hidden="true" className="size-4" />,
              onSelect: () => onMove(-1),
              disabled: number === 1,
            },
            {
              label: t("editor.menuMoveDown"),
              icon: <ArrowDown aria-hidden="true" className="size-4" />,
              onSelect: () => onMove(1),
              disabled: number === total,
            },
            {
              label: t("editor.menuDelete"),
              icon: <Trash2 aria-hidden="true" className="size-4" />,
              onSelect: onRemove,
              tone: "danger",
            },
          ]}
        />
        <div className="hidden flex-wrap items-center gap-1 sm:flex">
          {canRewrite && (
            <Button type="button" variant="ghost" size="sm" loading={rewriting} onClick={onRewrite}>
              <RefreshCw aria-hidden="true" className="size-4" />
              {t("editor.rewrite")}
            </Button>
          )}
          <button
            type="button"
            disabled={number === 1}
            aria-label={t("editor.moveUp", { number })}
            onClick={() => onMove(-1)}
            className="flex size-9 cursor-pointer items-center justify-center rounded-control text-ink-soft hover:bg-navy-soft hover:text-navy disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ArrowUp aria-hidden="true" className="size-4" />
          </button>
          <button
            type="button"
            disabled={number === total}
            aria-label={t("editor.moveDown", { number })}
            onClick={() => onMove(1)}
            className="flex size-9 cursor-pointer items-center justify-center rounded-control text-ink-soft hover:bg-navy-soft hover:text-navy disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ArrowDown aria-hidden="true" className="size-4" />
          </button>
          <button
            type="button"
            aria-label={t("editor.remove", { number })}
            onClick={onRemove}
            className="flex size-9 cursor-pointer items-center justify-center rounded-control text-ink-soft hover:bg-red-50 hover:text-red-700"
          >
            <Trash2 aria-hidden="true" className="size-4" />
          </button>
        </div>
      </div>
      {rewriting && (
        <p role="status" className="mb-3 flex items-center gap-2 text-sm text-ink-soft sm:hidden">
          <Spinner />
          {t("editor.rewriting")}
        </p>
      )}

      <div className="flex flex-col gap-3">
        <Field
          id={`test-${key(id, "text")}`}
          label={t("editor.text")}
          required
          hint={item.kind === "fill_blank" ? t("editor.blankHint") : undefined}
          error={form.errorFor(key(id, "text"))}
        >
          <Textarea {...form.bind(key(id, "text"))} rows={2} dir="auto" />
        </Field>

        {item.kind === "mcq" && (
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 text-sm font-semibold text-ink">{t("editor.options")}</legend>
            {item.options.map((slot, index) => {
              const name = optionKey(id, slot);
              const correct = form.values[key(id, "correct")] === String(slot);
              return (
                <div key={slot} className="flex items-start gap-2">
                  <label
                    className={cn(
                      "flex min-h-11 shrink-0 cursor-pointer items-center gap-1.5 text-sm font-semibold",
                      correct ? "text-emerald-800" : "text-ink-soft",
                    )}
                  >
                    <input
                      type="radio"
                      name={key(id, "correct")}
                      value={String(slot)}
                      checked={correct}
                      onChange={() => form.setValue(key(id, "correct"), String(slot))}
                      className="size-4 accent-current"
                    />
                    <span aria-hidden="true">{letters[index]}</span>
                    <span className="sr-only">
                      {t("editor.markCorrect", { letter: letters[index] })}
                    </span>
                  </label>
                  <div className="flex min-w-0 flex-1 flex-col gap-1">
                    {/* The letter beside it is the label; screen readers hear "Choice A". */}
                    <Input
                      {...form.bind(name)}
                      aria-label={t("editor.option", { letter: letters[index] })}
                      className="h-11"
                      dir="auto"
                    />
                    {form.errorFor(name) && (
                      <p id={`test-${name}-error`} role="alert" className="text-sm text-red-700">
                        {form.errorFor(name)}
                      </p>
                    )}
                  </div>
                  {item.options.length > MIN_OPTIONS && (
                    <button
                      type="button"
                      aria-label={t("editor.removeOption", { letter: letters[index] })}
                      onClick={() => onRemoveOption(slot)}
                      className="mt-1 flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-control text-ink-soft hover:bg-navy-soft hover:text-navy"
                    >
                      <X aria-hidden="true" className="size-4" />
                    </button>
                  )}
                </div>
              );
            })}
            {form.errorFor(key(id, "correct")) && (
              <p role="alert" className="text-sm text-red-700">
                {t("editor.chooseCorrect")}
              </p>
            )}
            {item.options.length < MAX_OPTIONS && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="w-fit"
                onClick={onAddOption}
              >
                <Plus aria-hidden="true" className="size-4" />
                {t("editor.addOption")}
              </Button>
            )}
          </fieldset>
        )}

        <div className="grid gap-3 sm:grid-cols-[1fr_140px]">
          {item.kind === "true_false" && (
            <Field
              id={`test-${key(id, "answer")}`}
              label={t("editor.answer")}
              required
              error={form.errorFor(key(id, "answer"))}
            >
              <Select {...form.bind(key(id, "answer"))} className="h-11">
                <option value="">{t("editor.chooseAnswer")}</option>
                <option value="true">{t("editor.trueLabel")}</option>
                <option value="false">{t("editor.falseLabel")}</option>
              </Select>
            </Field>
          )}
          {item.kind === "fill_blank" && (
            <Field
              id={`test-${key(id, "answer")}`}
              label={t("editor.answer")}
              required
              error={form.errorFor(key(id, "answer"))}
            >
              <Input {...form.bind(key(id, "answer"))} className="h-11" dir="auto" />
            </Field>
          )}
          {item.kind === "short_answer" && (
            <Field
              id={`test-${key(id, "answer")}`}
              label={t("editor.modelAnswer")}
              error={form.errorFor(key(id, "answer"))}
            >
              <Textarea {...form.bind(key(id, "answer"))} rows={2} dir="auto" />
            </Field>
          )}
          {item.kind === "mcq" && <div aria-hidden="true" />}
          <Field
            id={`test-${key(id, "marks")}`}
            label={t("editor.marks")}
            required
            error={form.errorFor(key(id, "marks"))}
          >
            <Input {...form.bind(key(id, "marks"))} inputMode="decimal" className="h-11" />
          </Field>
        </div>

        <Field
          id={`test-${key(id, "explanation")}`}
          label={t("editor.explanation")}
          error={form.errorFor(key(id, "explanation"))}
        >
          <Input {...form.bind(key(id, "explanation"))} className="h-11" dir="auto" />
        </Field>
        <ErrorNote message={rewriteError} />
      </div>
    </li>
  );
}

function DiscardDialog({ onLeave, onStay }: { onLeave: () => void; onStay: () => void }) {
  const t = useTranslations("Teacher.tests.editor");
  const tCommon = useTranslations("Teacher.common");
  return (
    <Modal
      open
      onClose={onStay}
      title={t("discardTitle")}
      description={t("discardBody")}
      closeLabel={tCommon("close")}
    >
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm" onClick={onStay}>
          {t("keep")}
        </Button>
        <Button variant="destructive" size="sm" onClick={onLeave}>
          {t("discard")}
        </Button>
      </div>
    </Modal>
  );
}

/**
 * Review an AI draft, edit a saved test, or write one by hand, then set how the paper
 * looks. Nothing is saved until the teacher saves.
 */
export function TestEditor({
  options,
  draft,
  exam,
  onClose,
  onSaved,
}: {
  options: ExamOptions;
  draft?: ExamDraft;
  exam?: ExamDetail;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("Teacher.tests");
  const locale = useLocale();
  const describe = useTeacherError();
  // Classes belong to the school plan (ADR-0027), so the field shows only when on.
  const showClasses = useWorkspace().workspace.features.classes;
  const classes = useLoad(
    (signal) => (showClasses ? listClasses(signal) : Promise.resolve([])),
    `test-editor-classes:${showClasses}`,
  );
  const maxQuestions = options.limits.max_exam_questions;

  const [start] = useState(() => {
    let ids = 0;
    let slots = 0;
    const questions = exam?.questions ?? draft?.questions ?? [blankQuestion("mcq")];
    const settings = draft?.settings;
    const values: Record<string, string> = {
      title: exam?.title ?? settings?.title ?? "",
      subject: exam?.subject ?? settings?.subject ?? "",
      grade: exam?.grade ?? settings?.grade ?? "",
      language: exam?.language ?? settings?.language ?? (locale === "ar" ? "ar" : "en"),
      classroom: String(exam?.classroom ?? settings?.classroom ?? ""),
      exam_date: isoToDayDate(exam?.exam_date),
      duration: exam?.duration_minutes ? String(exam.duration_minutes) : "",
      instructions: exam?.instructions ?? "",
    };
    const items = questions.map((question) => {
      const state = questionState(question, ids++, () => slots++);
      Object.assign(values, state.values);
      return state.item;
    });
    return { values, items, ids, slots, snapshot: JSON.stringify({ values, items }) };
  });

  // New questions and choices get ids after the ones above.
  const nextId = useRef(start.ids);
  const nextSlot = useRef(start.slots);
  const [items, setItems] = useState<Item[]>(start.items);
  const [newKind, setNewKind] = useState<QuestionKind>("mcq");
  const [rewritesLeft, setRewritesLeft] = useState(draft?.regenerations_left ?? 0);
  const [rewriting, setRewriting] = useState<number | null>(null);
  const [rewriteErrors, setRewriteErrors] = useState<Record<number, string | null>>({});
  const [leaving, setLeaving] = useState(false);
  // A draft over a day old is gone; the test is then saved as the teacher's own.
  const [draftGone, setDraftGone] = useState(false);

  const validators: Record<
    string,
    (value: string, all: Record<string, string>) => ErrorKey | null
  > = {
    title: required(200),
    subject: optional(100),
    grade: optional(50),
    exam_date: dayDate(),
    duration: optionalWholeNumber(1, 600, "minutes"),
    instructions: optional(1000),
  };
  for (const item of items) {
    const id = item.id;
    validators[key(id, "text")] = (value) => {
      const error = required(1000)(value);
      if (error || item.kind !== "fill_blank") return error;
      return (value.match(BLANKS) ?? []).length === 1 ? null : "blankOnce";
    };
    validators[key(id, "marks")] = marksValidator;
    validators[key(id, "explanation")] = optional(1000);
    if (item.kind === "true_false") validators[key(id, "answer")] = requiredChoice;
    if (item.kind === "fill_blank") validators[key(id, "answer")] = required(200);
    if (item.kind === "short_answer") validators[key(id, "answer")] = optional(1000);
    if (item.kind === "mcq") {
      validators[key(id, "correct")] = (value) =>
        value && item.options.includes(Number(value)) ? null : "choose";
      for (const slot of item.options) {
        validators[optionKey(id, slot)] = (value, all) => {
          const error = required(300)(value);
          if (error) return error;
          const repeated = item.options.some(
            (other) =>
              other < slot && sameText(all[optionKey(id, other)] ?? "") === sameText(value),
          );
          return repeated ? "repeatedChoice" : null;
        };
      }
    }
  }

  const form = useValidatedForm<Record<string, string>>({
    initial: start.values,
    idPrefix: "test-",
    validators,
    sanitizers: {
      duration: sanitizeDigits,
      exam_date: maskDayDate,
      ...Object.fromEntries(items.map((item) => [key(item.id, "marks"), sanitizeMarks])),
    },
    submit: async (values) => {
      const body = {
        title: values.title.trim(),
        subject: values.subject.trim(),
        grade: values.grade.trim(),
        language: values.language === "ar" ? ("ar" as const) : ("en" as const),
        classroom: values.classroom ? Number(values.classroom) : null,
        exam_date: dayDateToIso(values.exam_date),
        duration_minutes: values.duration ? Number(values.duration) : null,
        instructions: values.instructions.trim(),
        questions: items.map((item): ExamQuestion => {
          const isMcq = item.kind === "mcq";
          return {
            kind: item.kind,
            text: values[key(item.id, "text")].trim(),
            options: isMcq
              ? item.options.map((slot) => values[optionKey(item.id, slot)].trim())
              : [],
            correct_option: isMcq
              ? item.options.indexOf(Number(values[key(item.id, "correct")]))
              : null,
            answer: isMcq ? "" : (values[key(item.id, "answer")] ?? "").trim(),
            explanation: values[key(item.id, "explanation")].trim(),
            marks: values[key(item.id, "marks")].trim(),
            difficulty: item.difficulty,
            source_page: item.sourcePage,
          };
        }),
      };
      if (exam) await updateExam(exam.id, body);
      else await createExam({ ...body, draft: draft && !draftGone ? draft.id : null });
    },
    onSuccess: onSaved,
    describeError: (error) => {
      if (error instanceof ApiError && error.status === 400 && error.fields) {
        if ("draft" in error.fields) {
          setDraftGone(true);
          return t("editor.draftExpired");
        }
        if ("questions" in error.fields) return t("editor.checkQuestions");
      }
      return describe(error);
    },
  });

  // The paper's letters follow the test's language, not the app's.
  const letters = LETTERS[form.values.language === "ar" ? "ar" : "en"];

  const dirty = useMemo(
    () => JSON.stringify({ values: form.values, items }) !== start.snapshot,
    [form.values, items, start.snapshot],
  );

  // Warns before the tab closes with unsaved work.
  useEffect(() => {
    if (!dirty || form.saving) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty, form.saving]);

  function close() {
    if (dirty) setLeaving(true);
    else onClose();
  }

  function addQuestion() {
    const id = nextId.current++;
    const state = questionState(blankQuestion(newKind), id, () => nextSlot.current++);
    for (const [name, value] of Object.entries(state.values)) form.setValue(name, value);
    setItems((current) => [...current, state.item]);
    requestAnimationFrame(() => document.getElementById(`test-${key(id, "text")}`)?.focus());
  }

  function move(id: number, step: -1 | 1) {
    setItems((current) => {
      const index = current.findIndex((item) => item.id === id);
      const target = index + step;
      if (index < 0 || target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function updateItem(id: number, change: (item: Item) => Item) {
    setItems((current) => current.map((item) => (item.id === id ? change(item) : item)));
  }

  function addOption(id: number) {
    const slot = nextSlot.current++;
    form.setValue(optionKey(id, slot), "");
    updateItem(id, (item) => ({ ...item, options: [...item.options, slot] }));
  }

  function removeOption(id: number, slot: number) {
    if (form.values[key(id, "correct")] === String(slot)) form.setValue(key(id, "correct"), "");
    updateItem(id, (item) => ({
      ...item,
      options: item.options.filter((other) => other !== slot),
    }));
  }

  async function rewrite(item: Item) {
    if (!draft) return;
    setRewriting(item.id);
    setRewriteErrors((current) => ({ ...current, [item.id]: null }));
    try {
      const result = await regenerateExamQuestion(draft.id, {
        kind: item.kind,
        difficulty: item.difficulty,
        source_page: item.sourcePage,
        avoid: items.map((other) => form.values[key(other.id, "text")]).filter(Boolean),
      });
      const question = { ...result.question, marks: form.values[key(item.id, "marks")] };
      const state = questionState(question, item.id, () => nextSlot.current++);
      // The teacher's marks stay; everything else is the new question.
      for (const [name, value] of Object.entries(state.values)) {
        if (name !== key(item.id, "marks")) form.setValue(name, value);
      }
      updateItem(item.id, () => state.item);
      setRewritesLeft(result.regenerations_left);
    } catch (err) {
      if (err instanceof ApiError && err.code === "regenerate_limit_reached") setRewritesLeft(0);
      setRewriteErrors((current) => ({
        ...current,
        [item.id]: describe(err) ?? t("editor.rewriteFailed"),
      }));
    } finally {
      setRewriting(null);
    }
  }

  const totalMarks = items.reduce(
    (sum, item) => sum + (Number(form.values[key(item.id, "marks")]) || 0),
    0,
  );
  const title = exam
    ? t("editor.editTitle")
    : draft
      ? t("editor.reviewTitle")
      : t("editor.newTitle");
  const fewer = draft && draft.questions.length < draft.requested;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3">
        <h1 className="text-2xl text-navy-deep">{title}</h1>
        {draft && <Stepper current="review" />}
      </div>

      {draft && (
        <p className="flex items-start gap-2 rounded-control bg-navy-soft p-3 text-sm text-navy-deep">
          <Sparkles aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {t("editor.reviewHint")}
        </p>
      )}
      {fewer && (
        <p role="status" className="rounded-control bg-amber-50 p-3 text-sm text-amber-800">
          {t("editor.fewer", { made: draft.questions.length, asked: draft.requested })}
        </p>
      )}

      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-5">
        <section className="flex flex-col gap-3 rounded-card border border-line bg-bg p-5">
          <h2 className="text-lg text-navy-deep">{t("editor.details")}</h2>
          <Field
            id="test-title"
            label={t("details.testTitle")}
            required
            error={form.errorFor("title")}
          >
            <Input {...form.bind("title")} dir="auto" />
          </Field>
          <div className="grid gap-3 sm:grid-cols-3">
            <Field id="test-subject" label={t("details.subject")} error={form.errorFor("subject")}>
              <Input {...form.bind("subject")} />
            </Field>
            <Field id="test-grade" label={t("details.grade")} error={form.errorFor("grade")}>
              <Input {...form.bind("grade")} />
            </Field>
            {showClasses && (
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
            )}
            <Field id="test-exam_date" label={t("editor.date")} error={form.errorFor("exam_date")}>
              <DateField
                {...form.bind("exam_date")}
                onPick={(value) => form.setValue("exam_date", value)}
                calendarLabel={t("editor.openCalendar")}
                className="h-11"
              />
            </Field>
            <Field
              id="test-duration"
              label={t("editor.duration")}
              error={form.errorFor("duration")}
            >
              <Input {...form.bind("duration")} inputMode="numeric" className="h-11" />
            </Field>
            <Field id="test-language" label={t("details.language")} hint={t("editor.languageHint")}>
              <Select {...form.bind("language")} className="h-11">
                <option value="en">English</option>
                <option value="ar">العربية</option>
              </Select>
            </Field>
          </div>
          <Field
            id="test-instructions"
            label={t("editor.instructions")}
            error={form.errorFor("instructions")}
          >
            <Textarea {...form.bind("instructions")} rows={2} dir="auto" />
          </Field>
        </section>

        <section className="flex flex-col gap-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg text-navy-deep">{t("editor.questions")}</h2>
            <p className="text-sm font-semibold text-navy-deep tabular-nums" aria-live="polite">
              {t("editor.total", {
                count: items.length,
                marks: Number(totalMarks.toFixed(2)),
              })}
            </p>
          </div>
          {draft && (
            <p className="text-xs text-ink-soft">
              {t("editor.rewritesLeft", { left: rewritesLeft })}
            </p>
          )}
          <ol className="flex flex-col gap-3">
            {items.map((item, index) => (
              <QuestionCard
                key={item.id}
                item={item}
                number={index + 1}
                total={items.length}
                form={form}
                letters={letters}
                canRewrite={Boolean(draft) && !draftGone && rewritesLeft > 0}
                rewriting={rewriting === item.id}
                rewriteError={rewriteErrors[item.id] ?? null}
                onRewrite={() => rewrite(item)}
                onMove={(step) => move(item.id, step)}
                onRemove={() =>
                  setItems((current) => current.filter((other) => other.id !== item.id))
                }
                onAddOption={() => addOption(item.id)}
                onRemoveOption={(slot) => removeOption(item.id, slot)}
              />
            ))}
          </ol>
          {items.length === 0 && (
            <p role="alert" className="text-sm text-red-700">
              {t("editor.noQuestions")}
            </p>
          )}
          {items.length < maxQuestions ? (
            <div className="flex flex-wrap items-end gap-2">
              <Field id="test-new-kind" label={t("editor.addKind")}>
                <Select
                  id="test-new-kind"
                  value={newKind}
                  onChange={(event) => setNewKind(event.target.value as QuestionKind)}
                  className="h-11"
                >
                  {QUESTION_KINDS.map((kind) => (
                    <option key={kind} value={kind}>
                      {t(`kinds.${kind}`)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Button type="button" variant="outline" size="sm" onClick={addQuestion}>
                <Plus aria-hidden="true" className="size-4" />
                {t("editor.addQuestion")}
              </Button>
            </div>
          ) : (
            <p className="text-sm text-ink-soft">
              {t("editor.maxQuestions", { max: maxQuestions })}
            </p>
          )}
        </section>

        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-control bg-bg p-3 text-sm text-ink-soft">
          <Palette aria-hidden="true" className="size-4 text-navy" />
          {t("editor.designNote")}
          <Link href="/teacher/paper-design" className="font-semibold text-navy hover:underline">
            {t("editor.designLink")}
          </Link>
        </p>

        <ErrorNote message={form.formError} />
        <div className="sticky bottom-[calc(4rem+env(safe-area-inset-bottom))] flex flex-wrap justify-end gap-2 border-t border-line bg-bg-tint py-3 lg:bottom-0">
          <Button type="button" variant="outline" size="sm" onClick={close}>
            {t("editor.back")}
          </Button>
          <Button type="submit" size="sm" loading={form.saving} disabled={items.length === 0}>
            {form.saving ? t("editor.saving") : t("editor.save")}
          </Button>
        </div>
      </form>

      {leaving && <DiscardDialog onLeave={onClose} onStay={() => setLeaving(false)} />}
    </div>
  );
}
