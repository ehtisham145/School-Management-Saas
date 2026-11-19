import { apiDownload, apiFetch, saveFile } from "@/lib/api";
import type {
  Assessment,
  AssessmentInput,
  AttendanceRoster,
  AttendanceStatus,
  Classroom,
  ClassroomInput,
  Gradebook,
  LessonDraft,
  LessonGenerateInput,
  LessonPlan,
  LessonPlanInput,
  MarkSheet,
  Paginated,
  ParentMessage,
  ProfilePeriod,
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
