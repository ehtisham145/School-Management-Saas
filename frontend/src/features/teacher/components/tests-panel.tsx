"use client";

import { useState } from "react";
import { Copy, Download, Plus, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import {
  LoadFeedback,
  PageHeader,
  Pagination,
  SearchBox,
} from "@/features/platform/components/panel-ui";
import { useLoad } from "@/features/platform/use-load";
import {
  deleteExam,
  downloadExam,
  duplicateExam,
  getExam,
  getExamOptions,
  listExams,
} from "../api";
import type { Exam, ExamDetail, ExamDraft } from "../schemas";
import {
  ConfirmDelete,
  ErrorNote,
  useFormatDate,
  useTeacherError,
  useWorkspace,
} from "./teacher-ui";
import { TestEditor } from "./test-editor";
import { TestMaker, useAiTestAllowance } from "./test-maker";

type View =
  | { name: "list" }
  | { name: "make" }
  | { name: "review"; draft: ExamDraft }
  | { name: "edit"; exam?: ExamDetail };

type FileChoice = "pdf" | "key" | "docx";

function TestList({
  onMake,
  onNew,
  onEdit,
}: {
  onMake: () => void;
  onNew: () => void;
  onEdit: (exam: ExamDetail) => void;
}) {
  const t = useTranslations("Teacher.tests");
  const tCommon = useTranslations("Teacher.common");
  const describe = useTeacherError();
  const formatDate = useFormatDate();
  const { workspace, reload: reloadWorkspace } = useWorkspace();
  const allowance = useAiTestAllowance();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { state, reload } = useLoad(
    (signal) => listExams(search, page, signal),
    `${search}:${page}`,
  );
  const [removing, setRemoving] = useState<Exam | null>(null);
  // "12:key" while test 12's answer key downloads.
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const readOnly = workspace.access.read_only;

  async function run(exam: Exam, action: string, work: () => Promise<void>) {
    setBusy(`${exam.id}:${action}`);
    setError(null);
    try {
      await work();
    } catch (err) {
      setError(describe(err));
    } finally {
      setBusy(null);
    }
  }

  const download = (exam: Exam, choice: FileChoice) =>
    run(exam, choice, () =>
      downloadExam(exam, choice === "docx" ? "docx" : "pdf", choice === "key"),
    );

  return (
    <>
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        action={
          !readOnly && (
            <div className="flex flex-wrap gap-2">
              <Button variant="orange" size="sm" disabled={allowance.left === 0} onClick={onMake}>
                <Sparkles aria-hidden="true" className="size-4" />
                {t("ai")}
                <span className="rounded-full bg-on-orange/20 px-1.5 text-[11px] tabular-nums">
                  {t("aiLeftShort", { left: allowance.left })}
                </span>
              </Button>
              <Button size="sm" onClick={onNew}>
                <Plus aria-hidden="true" className="size-4" />
                {t("new")}
              </Button>
            </div>
          )
        }
      />

      <SearchBox
        label={t("search")}
        onSearch={(term) => {
          setSearch(term);
          setPage(1);
        }}
      />
      <ErrorNote message={error} />
      <LoadFeedback state={state} onRetry={reload} />

      {state.name === "ready" && state.data.count === 0 && (
        <EmptyState title={t("emptyTitle")} description={t("emptyHint")} />
      )}

      {state.name === "ready" && state.data.count > 0 && (
        <>
          <ul className="flex flex-col gap-3">
            {state.data.results.map((exam) => (
              <li key={exam.id} className="rounded-card border border-line bg-bg p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p
                      className="flex flex-wrap items-center gap-2 text-[16px] font-semibold text-navy-deep"
                      dir="auto"
                    >
                      {exam.title}
                      {exam.source === "ai" && <Badge tone="info">{t("aiBadge")}</Badge>}
                    </p>
                    <p className="mt-1 text-sm text-ink-soft">
                      {[
                        exam.classroom_name,
                        exam.subject,
                        t("questionCount", { count: exam.question_count }),
                        t("marksTotal", { marks: Number(exam.total_marks) }),
                        exam.exam_date && formatDate(exam.exam_date),
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      loading={busy === `${exam.id}:pdf`}
                      onClick={() => download(exam, "pdf")}
                    >
                      <Download aria-hidden="true" className="size-4" />
                      {t("downloadPaper")}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      loading={busy === `${exam.id}:key`}
                      onClick={() => download(exam, "key")}
                    >
                      {t("downloadKey")}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      loading={busy === `${exam.id}:docx`}
                      onClick={() => download(exam, "docx")}
                    >
                      {t("downloadWord")}
                    </Button>
                    {!readOnly && (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          loading={busy === `${exam.id}:edit`}
                          onClick={() =>
                            run(exam, "edit", async () => onEdit(await getExam(exam.id)))
                          }
                        >
                          {tCommon("edit")}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          loading={busy === `${exam.id}:copy`}
                          aria-label={t("copyLabel", { name: exam.title })}
                          onClick={() =>
                            run(exam, "copy", async () => {
                              await duplicateExam(exam.id);
                              reload();
                              reloadWorkspace();
                            })
                          }
                        >
                          <Copy aria-hidden="true" className="size-4" />
                          {t("copy")}
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setRemoving(exam)}>
                          {tCommon("delete")}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
          <Pagination page={page} count={state.data.count} onPage={setPage} />
        </>
      )}

      {removing && (
        <ConfirmDelete
          title={t("deleteTitle", { name: removing.title })}
          body={t("deleteBody")}
          onConfirm={async () => {
            await deleteExam(removing.id);
            reload();
            reloadWorkspace();
          }}
          onClose={() => setRemoving(null)}
        />
      )}
    </>
  );
}

/** The teacher's tests: made with AI from a PDF, or written by hand. */
export function TestsPanel() {
  const options = useLoad(getExamOptions, "exam-options");
  const { reload: reloadWorkspace } = useWorkspace();
  const [view, setView] = useState<View>({ name: "list" });

  if (options.state.name !== "ready") {
    return <LoadFeedback state={options.state} onRetry={options.reload} />;
  }
  const loaded = options.state.data;
  const backToList = () => setView({ name: "list" });
  const saved = () => {
    reloadWorkspace();
    backToList();
  };

  if (view.name === "make") {
    return (
      <TestMaker
        options={loaded}
        onCancel={backToList}
        onDraft={(draft) => setView({ name: "review", draft })}
      />
    );
  }
  if (view.name === "review") {
    return <TestEditor options={loaded} draft={view.draft} onClose={backToList} onSaved={saved} />;
  }
  if (view.name === "edit") {
    return <TestEditor options={loaded} exam={view.exam} onClose={backToList} onSaved={saved} />;
  }
  return (
    <TestList
      onMake={() => setView({ name: "make" })}
      onNew={() => setView({ name: "edit" })}
      onEdit={(exam) => setView({ name: "edit", exam })}
    />
  );
}
