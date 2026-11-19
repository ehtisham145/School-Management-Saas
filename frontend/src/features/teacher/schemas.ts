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
    ai_lessons: number;
    ai_period: "trial" | "month";
    pro_features: boolean;
  };
  usage: {
    classes: number;
    students: number;
    lesson_plans: number;
    presentation_exports: number;
    assessments: number;
    attendance_records: number;
    ai_used: number;
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
  assessment_count: number;
  attendance_taken_today: boolean;
};
export type ClassroomInput = Pick<Classroom, "name" | "subject" | "grade">;

export type Student = {
  id: number;
  classroom: number;
  first_name: string;
  last_name: string;
  father_name: string;
  student_number: string;
  full_name: string;
  parent_email: string;
};
export type StudentInput = Pick<
  Student,
  "first_name" | "last_name" | "father_name" | "student_number" | "parent_email"
>;

export const PROFILE_PERIODS = ["month", "90days", "all"] as const;
export type ProfilePeriod = (typeof PROFILE_PERIODS)[number];
export type StudentProfile = {
  student: Student & { classroom_name: string };
  period: ProfilePeriod;
  start: string | null;
  end: string;
  attendance: Record<AttendanceStatus, number> & {
    total: number;
    rate: string | null;
    days: { date: string; status: AttendanceStatus }[];
  };
  marks: {
    id: number;
    title: string;
    date: string;
    max_marks: string;
    value: string | null;
    percent: string | null;
    class_average_percent: string | null;
  }[];
  average_percent: string | null;
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
export type LessonPlanInput = Omit<
  LessonPlan,
  "id" | "classroom_name" | "source" | "updated_at"
> & {
  source?: LessonPlan["source"];
};
export type LessonDraft = Pick<
  LessonPlan,
  | "title"
  | "subject"
  | "grade"
  | "objectives"
  | "materials"
  | "activities"
  | "assessment"
  | "homework"
  | "classroom"
>;
export type LessonGenerateInput = {
  topic: string;
  subject: string;
  grade: string;
  language: "en" | "ar";
  classroom: number | null;
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
