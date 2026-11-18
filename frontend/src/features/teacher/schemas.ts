export type Tier = "trial" | "teacher" | "teacher_pro" | "expired";
export type TeacherPlanCode = "teacher" | "teacher_pro";

export type Workspace = {
  teacher_name: string;
  access: { tier: Tier; read_only: boolean; ends_on: string | null; days_left: number | null };
  limits: {
    classes: number | null;
    students: number | null;
    lesson_plans: number | null;
    presentation_exports: number | null;
    ai_per_month: number;
    pro_features: boolean;
  };
  usage: {
    classes: number;
    students: number;
    lesson_plans: number;
    presentation_exports: number;
    assessments: number;
    attendance_records: number;
    ai_this_month: number;
  };
  profile: { subject: string; grade_levels: string } | null;
  pending_upgrade: { plan: TeacherPlanCode } | null;
};

export type Classroom = {
  id: number;
  name: string;
  subject: string;
  grade: string;
  student_count: number;
};
export type ClassroomInput = Pick<Classroom, "name" | "subject" | "grade">;

export type Student = {
  id: number;
  classroom: number;
  full_name: string;
  parent_email: string;
};

export const ATTENDANCE_STATUSES = ["present", "absent", "late", "excused"] as const;
export type AttendanceStatus = (typeof ATTENDANCE_STATUSES)[number];
export type AttendanceRoster = {
  date: string;
  students: { id: number; full_name: string; status: AttendanceStatus | null }[];
};

export type LessonPlan = {
  id: number;
  classroom: number | null;
  classroom_name: string | null;
  title: string;
  subject: string;
  grade: string;
  lesson_date: string | null;
  objectives: string;
  materials: string;
  activities: string;
  assessment: string;
  homework: string;
  source: "manual" | "ai";
  updated_at: string;
};
export type LessonPlanInput = Omit<LessonPlan, "id" | "classroom_name" | "source" | "updated_at">;
export type LessonGenerateInput = {
  topic: string;
  subject: string;
  grade: string;
  language: "en" | "ar";
};

export type Assessment = {
  id: number;
  classroom: number;
  title: string;
  max_marks: string;
  date: string;
  marked: number;
};
export type AssessmentInput = Pick<Assessment, "classroom" | "title" | "max_marks" | "date">;
export type MarkSheet = {
  assessment: Assessment;
  students: { id: number; full_name: string; value: string | null }[];
};
export type Gradebook = {
  assessments: { id: number; title: string; max_marks: string; date: string }[];
  students: { id: number; full_name: string; marks: Record<string, string> }[];
};

export type ParentMessage = {
  id: number;
  classroom: number;
  classroom_name: string;
  subject: string;
  body: string;
  recipient_count: number;
  created_at: string;
};

export type Paginated<T> = { count: number; results: T[] };
