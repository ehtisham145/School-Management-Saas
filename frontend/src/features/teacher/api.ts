import { apiDownload, apiFetch, apiUpload, saveFile } from "@/lib/api";
import type {
  AgentStatus,
  AgentTask,
  AgentTaskDetail,
  Assessment,
  AssessmentInput,
  AttendanceRoster,
  AttendanceStatus,
  Classroom,
  ClassroomInput,
  Difficulty,
  Exam,
  ExamDetail,
  ExamDraft,
  ExamDraftInput,
  ExamInput,
  ExamOptions,
  ExamPattern,
  ExamSection,
  ExamTheme,
  Gradebook,
  LessonDraft,
  LessonGenerateInput,
  LessonPlan,
  LessonPlanInput,
  MarkSheet,
  Paginated,
  ParentMessage,
  ProfilePeriod,
  QuestionKind,
  RegeneratedQuestion,
  SourceDocument,
  Student,
  StudentInput,
  StudentProfile,
  TeacherPlanCode,
  Workspace,
} from "./schemas";

const BASE = "/classroom";

export const getWorkspace = (signal?: AbortSignal) =>
  apiFetch<Workspace>(`${BASE}/workspace/`, { signal });

export const saveSetup = (body: { subject: string; grade_levels: string }) =>
  apiFetch<void>(`${BASE}/setup/`, { method: "POST", body });

export const requestUpgrade = (plan: TeacherPlanCode) =>
  apiFetch<void>(`${BASE}/upgrade-request/`, { method: "POST", body: { plan } });

export const listClasses = (signal?: AbortSignal) =>
  apiFetch<Classroom[]>(`${BASE}/classes/`, { signal });
export const getClass = (id: number, signal?: AbortSignal) =>
  apiFetch<Classroom>(`${BASE}/classes/${id}/`, { signal });
export const createClass = (body: ClassroomInput) =>
  apiFetch<Classroom>(`${BASE}/classes/`, { method: "POST", body });
export const updateClass = (id: number, body: ClassroomInput) =>
  apiFetch<Classroom>(`${BASE}/classes/${id}/`, { method: "PATCH", body });
export const deleteClass = (id: number) =>
  apiFetch<void>(`${BASE}/classes/${id}/`, { method: "DELETE" });

export const listStudents = (classId: number, signal?: AbortSignal) =>
  apiFetch<Student[]>(`${BASE}/classes/${classId}/students/`, { signal });
export const addStudents = (classId: number, students: StudentInput[]) =>
  apiFetch<Student[]>(`${BASE}/classes/${classId}/students/`, {
    method: "POST",
    body: { students },
  });
export const updateStudent = (id: number, body: StudentInput) =>
  apiFetch<Student>(`${BASE}/students/${id}/`, { method: "PATCH", body });
export const getStudentProfile = (id: number, period: ProfilePeriod, signal?: AbortSignal) =>
  apiFetch<StudentProfile>(`${BASE}/students/${id}/profile/?period=${period}`, { signal });
export const deleteStudent = (id: number) =>
  apiFetch<void>(`${BASE}/students/${id}/`, { method: "DELETE" });

export async function downloadReportCard(student: Pick<Student, "id">, language: string) {
  const { blob, filename } = await apiDownload(
    `${BASE}/students/${student.id}/report-card/?language=${language}`,
  );
  saveFile(blob, filename ?? "report-card.pdf");
}

export const getAttendance = (classId: number, date: string, signal?: AbortSignal) =>
  apiFetch<AttendanceRoster>(`${BASE}/classes/${classId}/attendance/?date=${date}`, { signal });
export const saveAttendance = (
  classId: number,
  date: string,
  records: { student: number; status: AttendanceStatus }[],
) =>
  apiFetch<void>(`${BASE}/classes/${classId}/attendance/`, {
    method: "PUT",
    body: { date, records },
  });

export const listLessonPlans = (search: string, page: number, signal?: AbortSignal) => {
  const query = new URLSearchParams({ page: String(page) });
  if (search) query.set("search", search);
  return apiFetch<Paginated<LessonPlan>>(`${BASE}/lesson-plans/?${query}`, { signal });
};
export const createLessonPlan = (body: LessonPlanInput) =>
  apiFetch<LessonPlan>(`${BASE}/lesson-plans/`, { method: "POST", body });
export const updateLessonPlan = (id: number, body: LessonPlanInput) =>
  apiFetch<LessonPlan>(`${BASE}/lesson-plans/${id}/`, { method: "PATCH", body });
export const deleteLessonPlan = (id: number) =>
  apiFetch<void>(`${BASE}/lesson-plans/${id}/`, { method: "DELETE" });
export const generateLessonPlan = (body: LessonGenerateInput) =>
  apiFetch<LessonDraft>(`${BASE}/lesson-plans/generate/`, { method: "POST", body });

export async function downloadPresentation(plan: LessonPlan) {
  const { blob, filename } = await apiDownload(`${BASE}/lesson-plans/${plan.id}/presentation/`);
  saveFile(blob, filename ?? "lesson.pptx");
}

export async function downloadWordDocument(plan: LessonPlan) {
  const { blob, filename } = await apiDownload(`${BASE}/lesson-plans/${plan.id}/document/`);
  saveFile(blob, filename ?? "lesson.docx");
}

export const listAssessments = (classId: number, signal?: AbortSignal) =>
  apiFetch<Assessment[]>(`${BASE}/assessments/?classroom=${classId}`, { signal });
export const createAssessment = (body: AssessmentInput) =>
  apiFetch<Assessment>(`${BASE}/assessments/`, { method: "POST", body });
export const deleteAssessment = (id: number) =>
  apiFetch<void>(`${BASE}/assessments/${id}/`, { method: "DELETE" });
export const getMarkSheet = (id: number, signal?: AbortSignal) =>
  apiFetch<MarkSheet>(`${BASE}/assessments/${id}/marks/`, { signal });
export const saveMarks = (id: number, marks: { student: number; value: string | null }[]) =>
  apiFetch<void>(`${BASE}/assessments/${id}/marks/`, { method: "PUT", body: { marks } });
export const getGradebook = (classId: number, signal?: AbortSignal) =>
  apiFetch<Gradebook>(`${BASE}/classes/${classId}/gradebook/`, { signal });

export const listMessages = (signal?: AbortSignal) =>
  apiFetch<Paginated<ParentMessage>>(`${BASE}/messages/`, { signal });
export const sendMessage = (body: { classroom: number; subject: string; body: string }) =>
  apiFetch<ParentMessage>(`${BASE}/messages/`, { method: "POST", body });

// --- Tests made from a PDF

export const getExamOptions = (signal?: AbortSignal) =>
  apiFetch<ExamOptions>(`${BASE}/exam-options/`, { signal });

export function uploadExamSource(file: File) {
  const body = new FormData();
  body.append("file", file);
  return apiUpload<SourceDocument>(`${BASE}/exam-sources/`, body);
}

export const listExamPatterns = (signal?: AbortSignal) =>
  apiFetch<ExamPattern[]>(`${BASE}/exam-patterns/`, { signal });
export const createExamPattern = (body: { name: string; sections: ExamSection[] }) =>
  apiFetch<ExamPattern>(`${BASE}/exam-patterns/`, { method: "POST", body });
export const deleteExamPattern = (id: number) =>
  apiFetch<void>(`${BASE}/exam-patterns/${id}/`, { method: "DELETE" });

export const createExamDraft = (body: ExamDraftInput) =>
  apiFetch<ExamDraft>(`${BASE}/exam-drafts/`, { method: "POST", body });
export const getExamDraft = (id: number, signal?: AbortSignal) =>
  apiFetch<ExamDraft>(`${BASE}/exam-drafts/${id}/`, { signal });
export const regenerateExamQuestion = (
  id: number,
  body: { kind: QuestionKind; difficulty: Difficulty; source_page: number | null; avoid: string[] },
) =>
  apiFetch<RegeneratedQuestion>(`${BASE}/exam-drafts/${id}/regenerate/`, {
    method: "POST",
    body,
  });

export const listExams = (search: string, page: number, signal?: AbortSignal) => {
  const query = new URLSearchParams({ page: String(page) });
  if (search) query.set("search", search);
  return apiFetch<Paginated<Exam>>(`${BASE}/exams/?${query}`, { signal });
};
export const getExam = (id: number, signal?: AbortSignal) =>
  apiFetch<ExamDetail>(`${BASE}/exams/${id}/`, { signal });
export const createExam = (body: ExamInput) =>
  apiFetch<ExamDetail>(`${BASE}/exams/`, { method: "POST", body });
export const updateExam = (id: number, body: ExamInput) =>
  apiFetch<ExamDetail>(`${BASE}/exams/${id}/`, { method: "PATCH", body });
export const deleteExam = (id: number) =>
  apiFetch<void>(`${BASE}/exams/${id}/`, { method: "DELETE" });
export const duplicateExam = (id: number) =>
  apiFetch<ExamDetail>(`${BASE}/exams/${id}/duplicate/`, { method: "POST" });

export async function downloadExam(exam: Pick<Exam, "id">, type: "pdf" | "docx", answers: boolean) {
  const query = new URLSearchParams({ type });
  if (answers) query.set("answers", "true");
  const { blob, filename } = await apiDownload(`${BASE}/exams/${exam.id}/download/?${query}`);
  saveFile(blob, filename ?? `test.${type}`);
}

/** The look of every test paper and answer key the teacher downloads. */
export const getPaperDesign = (signal?: AbortSignal) =>
  apiFetch<ExamTheme>(`${BASE}/paper-design/`, { signal });
export const savePaperDesign = (body: ExamTheme) =>
  apiFetch<ExamTheme>(`${BASE}/paper-design/`, { method: "PUT", body });

/* ------------------------------------------------------------ Lesson Lab Agent */

const AGENT = "/browser-agent";

export const getAgentStatus = (signal?: AbortSignal) =>
  apiFetch<AgentStatus>(`${AGENT}/status/`, { signal });
export const acceptAgentConsent = (version: string) =>
  apiFetch<void>(`${AGENT}/consent/`, { method: "POST", body: { version } });
export const listAgentTasks = (page: number, signal?: AbortSignal) =>
  apiFetch<Paginated<AgentTask>>(`${AGENT}/tasks/?page=${page}`, { signal });
export const getAgentTask = (id: number, signal?: AbortSignal) =>
  apiFetch<AgentTaskDetail>(`${AGENT}/tasks/${id}/`, { signal });
export const startAgentTask = (body: { goal: string; start_url?: string }) =>
  apiFetch<AgentTask>(`${AGENT}/tasks/`, { method: "POST", body });
export const cancelAgentTask = (id: number) =>
  apiFetch<AgentTask>(`${AGENT}/tasks/${id}/cancel/`, { method: "POST" });

/**
 * The live socket for one task. Same origin on servers (Caddy sends /ws/ to Django). The
 * Next.js dev server can't pass sockets on, so locally NEXT_PUBLIC_WS_ORIGIN points at
 * Django (e.g. ws://localhost:8000); without it the page just polls.
 */
export function agentSocketUrl(taskId: number) {
  const origin =
    process.env.NEXT_PUBLIC_WS_ORIGIN ??
    `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
  return `${origin}/ws/browser-agent/${taskId}/`;
}
