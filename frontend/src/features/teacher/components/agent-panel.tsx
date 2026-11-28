"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, ShieldCheck, Square } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { LoadFeedback, PageHeader, Pagination } from "@/features/platform/components/panel-ui";
import { useLoad } from "@/features/platform/use-load";
import { ApiError } from "@/lib/api";
import { required, useValidatedForm } from "@/lib/use-validated-form";
import {
  acceptAgentConsent,
  agentSocketUrl,
  cancelAgentTask,
  getAgentStatus,
  getAgentTask,
  listAgentTasks,
  startAgentTask,
} from "../api";
import {
  ACTIVE_AGENT_STATUSES,
  type AgentStatus,
  type AgentStep,
  type AgentTask,
  type AgentTaskDetail,
  type AgentTaskStatus,
  type AgentUpdate,
} from "../schemas";
import {
  ErrorNote,
  Panel,
  UpgradeLink,
  useFormatDate,
  useTeacherError,
  useWorkspace,
} from "./teacher-ui";

const POLL_MS = 4000;
const GOAL_MAX = 2000;
const URL_PATTERN = /^https?:\/\/[^\s/]+\.[^\s]+$/i;

const AGENT_ERRORS = [
  "agent_quota_reached",
  "consent_required",
  "task_already_running",
  "browser_agent_busy",
  "browser_agent_budget_reached",
  "browser_agent_disabled",
] as const;

const STATUS_TONES: Record<AgentTaskStatus, "neutral" | "info" | "warning" | "success" | "danger"> =
  {
    queued: "neutral",
    running: "info",
    awaiting_user: "warning",
    done: "success",
    failed: "danger",
    cancelled: "neutral",
    limit_reached: "warning",
  };

const BLOCK_REASONS = [
  "blocked_domain",
  "domain_not_allowed",
  "private_address",
  "internal_name",
  "port",
  "personal_data_in_url",
  "scheme",
  "unresolvable",
] as const;

const STEP_ACTIONS = [
  "goto",
  "click",
  "type",
  "select",
  "scroll",
  "back",
  "wait",
  "extract",
  "done",
] as const;

const isActive = (status: AgentTaskStatus) => ACTIVE_AGENT_STATUSES.includes(status);

/** Groups the many failure codes into the few messages a teacher needs. */
function failureKey(reason: string) {
  if (["max_steps", "max_seconds", "max_tokens", "max_pages", "time_limit"].includes(reason))
    return "limit";
  if (reason === "max_cost") return "cost";
  if (reason === "monthly_budget") return "budget";
  if (reason === "too_many_strikes") return "strikes";
  if (["reply_cut_off", "bad_json", "not_an_object", "empty_reply"].includes(reason))
    return "aiReply";
  if (["provider_error", "not_configured", "model_not_priced", "no_time_left"].includes(reason))
    return "aiDown";
  if (
    ["internal_error", "worker_lost", "not_started"].includes(reason) ||
    reason.startsWith("browser_")
  )
    return "ours";
  if (reason === "cancelled_by_user") return "cancelled";
  if (reason === "start_page_failed") return "startPage";
  if (reason.startsWith("start_url_")) return "startBlocked";
  return "generic";
}

function useAgentError() {
  const t = useTranslations("Teacher.agent.errors");
  const describe = useTeacherError();
  return (error: unknown) => {
    if (error instanceof ApiError) {
      const known = AGENT_ERRORS.find((code) => code === error.code);
      if (known) return t(known);
    }
    return describe(error);
  };
}

/** One step in plain words. Only the action kind, the site and a reason code arrive. */
function StepLine({ step }: { step: AgentStep }) {
  const t = useTranslations("Teacher.agent.steps");
  let text: string;
  if (step.verdict === "blocked") {
    const code = step.note.replace(/^landed_on_/, "");
    const known = BLOCK_REASONS.find((reason) => reason === code);
    text = t("blocked", { reason: t(`reasons.${known ?? "other"}`) });
  } else if (step.verdict === "invalid") {
    text = t("invalid");
  } else {
    const action = STEP_ACTIONS.find((name) => name === step.action);
    text = action ? t(`actions.${action}`, { domain: step.domain || "—" }) : t("actions.other");
    if (step.verdict === "failed") text = t("failed", { action: text });
  }
  return (
    <li className="flex items-start gap-3 py-2">
      <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-navy-soft text-xs font-bold text-navy tabular-nums">
        {step.number}
      </span>
      <span className={cn("text-sm", step.verdict === "ok" ? "text-ink" : "text-red-700")}>
        {text}
      </span>
    </li>
  );
}

function merge(current: AgentTaskDetail | null, update: AgentUpdate): AgentTaskDetail | null {
  if (!current || current.id !== update.task.id) return current;
  const step = update.step;
  const steps =
    step && !current.steps.some((item) => item.number === step.number)
      ? [...current.steps, step]
      : current.steps;
  return {
    ...current,
    status: update.task.status,
    steps_taken: update.task.steps_taken,
    failure_reason: update.task.failure_reason,
    answer: update.task.answer ?? current.answer,
    steps,
  };
}

/**
 * Follows one task: the live socket for each step as it happens, and polling as a
 * fallback (the socket can't pass the Next.js dev server, and networks drop sockets).
 */
function useLiveTask(taskId: number) {
  const [task, setTask] = useState<AgentTaskDetail | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let socket: WebSocket | null = null;
    const controller = new AbortController();

    async function poll() {
      try {
        const data = await getAgentTask(taskId, controller.signal);
        if (stopped) return;
        setTask(data);
        setFailed(false);
        if (isActive(data.status)) timer = setTimeout(poll, POLL_MS);
      } catch {
        if (stopped || controller.signal.aborted) return;
        setFailed(true);
        timer = setTimeout(poll, POLL_MS * 2);
      }
    }
    void poll();

    try {
      socket = new WebSocket(agentSocketUrl(taskId));
      socket.onmessage = (event) => {
        try {
          const update = JSON.parse(String(event.data)) as AgentUpdate;
          if (update.type === "task.update") setTask((current) => merge(current, update));
        } catch {
          // A message we don't understand is ignored; polling keeps the page right.
        }
      };
    } catch {
      // No socket (blocked or not available): polling alone.
    }

    return () => {
      stopped = true;
      controller.abort();
      clearTimeout(timer);
      socket?.close();
    };
  }, [taskId]);

  return { task, setTask, failed };
}

function LiveTask({
  taskId,
  onFinished,
  onNewTask,
}: {
  taskId: number;
  onFinished: () => void;
  onNewTask: () => void;
}) {
  const t = useTranslations("Teacher.agent");
  const tCommon = useTranslations("Teacher.common");
  const describe = useAgentError();
  const { task, setTask, failed } = useLiveTask(taskId);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reported = useRef(false);

  // Once the task ends, the allowance and the list of tasks change.
  useEffect(() => {
    if (task && !isActive(task.status) && !reported.current) {
      reported.current = true;
      onFinished();
    }
  }, [task, onFinished]);

  async function cancel() {
    setCancelling(true);
    setError(null);
    try {
      const updated = await cancelAgentTask(taskId);
      setTask((current) => (current ? { ...current, ...updated } : current));
    } catch (err) {
      setError(describe(err));
    } finally {
      setCancelling(false);
    }
  }

  if (!task) {
    return (
      <Panel title={t("task.title")}>
        <p role="status" className="text-sm text-ink-soft">
          {failed ? tCommon("loadFailed") : tCommon("loading")}
        </p>
      </Panel>
    );
  }

  const active = isActive(task.status);
  return (
    <Panel
      title={t("task.title")}
      action={<Badge tone={STATUS_TONES[task.status]}>{t(`status.${task.status}`)}</Badge>}
    >
      <div className="flex flex-col gap-4">
        <div>
          <p className="text-xs font-semibold text-ink-soft">{t("task.goal")}</p>
          <p className="mt-1 whitespace-pre-wrap text-ink" dir="auto">
            {task.goal}
          </p>
          {task.start_url && (
            <p className="mt-1 truncate text-xs text-ink-soft" dir="ltr">
              {task.start_url}
            </p>
          )}
        </div>

        <div>
          <p className="text-xs font-semibold text-ink-soft">{t("task.steps")}</p>
          {task.steps.length === 0 ? (
            <p role="status" className="mt-2 text-sm text-ink-soft">
              {active ? t("task.waiting") : t("task.noSteps")}
            </p>
          ) : (
            <ol aria-live="polite" className="mt-1 flex flex-col divide-y divide-line">
              {task.steps.map((step) => (
                <StepLine key={step.number} step={step} />
              ))}
            </ol>
          )}
        </div>

        {task.status !== "done" && !active && task.failure_reason && (
          <p role="alert" className="rounded-control bg-amber-50 p-3 text-sm text-amber-800">
            {t(`failure.${failureKey(task.failure_reason)}`)}
          </p>
        )}

        {task.answer && (
          <div className="rounded-control border border-line bg-bg-tint p-4">
            <p className="text-xs font-semibold text-ink-soft">
              {task.status === "done" ? t("task.answer") : t("task.foundSoFar")}
            </p>
            <p className="mt-1 whitespace-pre-wrap text-ink" dir="auto">
              {task.answer}
            </p>
            <p className="mt-3 text-xs text-ink-soft">{t("task.aiNote")}</p>
          </div>
        )}

        <ErrorNote message={error} />

        <div className="flex flex-wrap justify-end gap-2">
          {active ? (
            <Button variant="outline" size="sm" loading={cancelling} onClick={cancel}>
              <Square aria-hidden="true" className="size-4" />
              {t("task.cancel")}
            </Button>
          ) : (
            <Button variant="orange" size="sm" onClick={onNewTask}>
              {t("task.newTask")}
            </Button>
          )}
        </div>
      </div>
    </Panel>
  );
}

function ConsentPanel({ version, onAccepted }: { version: string; onAccepted: () => void }) {
  const t = useTranslations("Teacher.agent.consent");
  const describe = useAgentError();
  const form = useValidatedForm({
    initial: { accept: "" },
    validators: { accept: (value) => (value ? null : "acceptPrivacy") },
    idPrefix: "agent-consent-",
    submit: () => acceptAgentConsent(version),
    onSuccess: onAccepted,
    describeError: describe,
  });
  const acceptError = form.errorFor("accept");
  const points = ["where", "ai", "data", "blocked", "responsibility", "check"] as const;

  return (
    <Panel title={t("title")}>
      <form noValidate onSubmit={form.handleSubmit} className="flex flex-col gap-4">
        <p className="text-sm text-ink">{t("intro")}</p>
        <ul className="flex list-disc flex-col gap-2 ps-5 text-sm text-ink">
          {points.map((point) => (
            <li key={point}>{t(`points.${point}`)}</li>
          ))}
        </ul>
        <div>
          <label className="flex items-start gap-2 text-sm text-ink">
            <input
              id="agent-consent-accept"
              name="accept"
              type="checkbox"
              checked={Boolean(form.values.accept)}
              onChange={(event) => form.setValue("accept", event.target.checked ? "yes" : "")}
              aria-invalid={Boolean(acceptError)}
              aria-describedby={acceptError ? "agent-consent-accept-error" : undefined}
              className="mt-0.5 size-4 shrink-0 accent-orange"
            />
            <span>
              {t("accept")}
              <span aria-hidden="true" className="ms-0.5 text-red-700">
                *
              </span>
            </span>
          </label>
          {acceptError && (
            <p id="agent-consent-accept-error" role="alert" className="mt-1 text-sm text-red-700">
              {acceptError}
            </p>
          )}
        </div>
        <ErrorNote message={form.formError} />
        <div className="flex justify-end">
          <Button type="submit" variant="orange" loading={form.saving}>
            <ShieldCheck aria-hidden="true" className="size-4" />
            {t("submit")}
          </Button>
        </div>
      </form>
    </Panel>
  );
}

function StartForm({ onStarted }: { onStarted: (task: AgentTask) => void }) {
  const t = useTranslations("Teacher.agent");
  const describe = useAgentError();
  const form = useValidatedForm({
    initial: { goal: "", start_url: "" },
    validators: {
      goal: required(GOAL_MAX),
      start_url: (value) => {
        const trimmed = value.trim();
        if (!trimmed) return null;
        if (trimmed.length > 2000) return "tooLong";
        return URL_PATTERN.test(trimmed) ? null : "invalid";
      },
    },
    idPrefix: "agent-",
    submit: async (values) => {
      const startUrl = values.start_url.trim();
      const task = await startAgentTask({
        goal: values.goal.trim(),
        ...(startUrl ? { start_url: startUrl } : {}),
      });
      onStarted(task);
    },
    onSuccess: () => form.reset(),
    describeError: describe,
  });

  return (
    <Panel>
      <form noValidate onSubmit={form.handleSubmit} className="flex flex-col gap-4">
        <Field
          id="agent-goal"
          label={t("goal")}
          required
          error={form.errorFor("goal")}
          hint={t("goalHint")}
        >
          <Textarea {...form.bind("goal")} rows={4} maxLength={GOAL_MAX} dir="auto" />
        </Field>
        <Field
          id="agent-start_url"
          label={t("startUrl")}
          error={form.errorFor("start_url")}
          hint={t("startUrlHint")}
        >
          <Input
            {...form.bind("start_url")}
            type="url"
            inputMode="url"
            dir="ltr"
            placeholder="https://"
            autoComplete="off"
          />
        </Field>
        <p className="flex items-start gap-2 rounded-control bg-navy-soft p-3 text-xs text-navy">
          <ShieldCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {t("safety")}
        </p>
        <ErrorNote message={form.formError} />
        <div className="flex justify-end">
          <Button type="submit" variant="orange" loading={form.saving}>
            <Bot aria-hidden="true" className="size-4" />
            {form.saving ? t("starting") : t("start")}
          </Button>
        </div>
      </form>
    </Panel>
  );
}

function History({
  page,
  onPage,
  onOpen,
  refresh,
}: {
  page: number;
  onPage: (page: number) => void;
  onOpen: (task: AgentTask) => void;
  refresh: number;
}) {
  const t = useTranslations("Teacher.agent");
  const formatDate = useFormatDate();
  const { state, reload } = useLoad(
    (signal) => listAgentTasks(page, signal),
    `agent-tasks:${page}:${refresh}`,
  );

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg text-navy-deep">{t("history.title")}</h2>
      <LoadFeedback state={state} onRetry={reload} />
      {state.name === "ready" && state.data.count === 0 && (
        <EmptyState title={t("history.empty")} description={t("history.emptyHint")} />
      )}
      {state.name === "ready" && state.data.count > 0 && (
        <>
          <ul className="flex flex-col gap-2">
            {state.data.results.map((task) => (
              <li key={task.id}>
                <button
                  type="button"
                  onClick={() => onOpen(task)}
                  className="flex w-full cursor-pointer flex-col gap-1 rounded-card border border-line bg-bg p-4 text-start transition-colors hover:border-navy-line sm:flex-row sm:items-center sm:justify-between"
                >
                  <span className="min-w-0">
                    <span className="line-clamp-2 font-semibold text-navy-deep" dir="auto">
                      {task.goal}
                    </span>
                    <span className="mt-1 block text-xs text-ink-soft">
                      {formatDate(task.created_at)} ·{" "}
                      {t("history.steps", { count: task.steps_taken })}
                    </span>
                  </span>
                  <Badge
                    tone={STATUS_TONES[task.status]}
                    className="shrink-0 self-start sm:self-center"
                  >
                    {t(`status.${task.status}`)}
                  </Badge>
                </button>
              </li>
            ))}
          </ul>
          <Pagination page={page} count={state.data.count} onPage={onPage} />
        </>
      )}
    </section>
  );
}

function Allowance({ status }: { status: AgentStatus }) {
  const t = useTranslations("Teacher.agent");
  const { left, limit, period } = status.allowance;
  return (
    <p className={cn("text-sm font-semibold", left === 0 ? "text-red-700" : "text-ink-soft")}>
      {left === 0 ? t("noneLeft", { period }) : t("left", { left, limit, period })}
    </p>
  );
}

/** Lesson Lab Agent: the teacher describes a task, the agent does it on the web (ADR-0028). */
export function AgentPanel() {
  const t = useTranslations("Teacher.agent");
  const { workspace } = useWorkspace();
  const status = useLoad((signal) => getAgentStatus(signal), "agent-status");
  const [opened, setOpened] = useState<number | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const reloadStatus = status.reload;

  if (!workspace.features.agent) {
    return (
      <>
        <PageHeader title={t("title")} subtitle={t("subtitle")} />
        <EmptyState title={t("notAvailable.title")} description={t("notAvailable.body")} />
      </>
    );
  }

  const ready = status.state.name === "ready" ? status.state.data : null;
  // The task on screen: one the teacher opened, or the one still running.
  const shown = opened ?? (dismissed ? null : (ready?.active_task?.id ?? null));
  const readOnly = workspace.access.read_only;

  return (
    <>
      <PageHeader title={t("title")} subtitle={t("subtitle")} />
      <LoadFeedback state={status.state} onRetry={reloadStatus} />

      {ready && (
        <>
          <Allowance status={ready} />

          {shown !== null ? (
            <LiveTask
              key={shown}
              taskId={shown}
              onFinished={() => {
                // Keep the finished task on screen after the status no longer lists it.
                setOpened((current) => current ?? shown);
                reloadStatus();
                setRefresh((value) => value + 1);
              }}
              onNewTask={() => {
                setOpened(null);
                setDismissed(true);
              }}
            />
          ) : readOnly ? (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-line bg-bg p-5">
              <p className="text-sm text-ink">{t("readOnly")}</p>
              <UpgradeLink />
            </div>
          ) : !ready.consent_given ? (
            <ConsentPanel version={ready.consent_version} onAccepted={reloadStatus} />
          ) : ready.allowance.left === 0 ? (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-line bg-bg p-5">
              <p className="text-sm text-ink">
                {t("noneLeft", { period: ready.allowance.period })}
              </p>
              <UpgradeLink />
            </div>
          ) : (
            <StartForm
              onStarted={(task) => {
                setOpened(task.id);
                setRefresh((value) => value + 1);
                reloadStatus();
              }}
            />
          )}

          <History
            page={page}
            onPage={setPage}
            refresh={refresh}
            onOpen={(task) => {
              setOpened(task.id);
              const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
              window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" });
            }}
          />
        </>
      )}
    </>
  );
}
