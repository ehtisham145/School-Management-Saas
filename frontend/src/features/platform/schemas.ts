export const SCHOOL_TYPES = ["boys", "girls", "mixed"] as const;
export type SchoolType = (typeof SCHOOL_TYPES)[number];

export const EDUCATION_STAGES = ["kindergarten", "primary", "intermediate", "secondary"] as const;
export type EducationStage = (typeof EDUCATION_STAGES)[number];

export const SAUDI_REGIONS = [
  "riyadh",
  "makkah",
  "madinah",
  "eastern",
  "qassim",
  "asir",
  "tabuk",
  "hail",
  "northern_borders",
  "jazan",
  "najran",
  "al_bahah",
  "al_jawf",
] as const;
export type SaudiRegion = (typeof SAUDI_REGIONS)[number];

export const SCHOOL_STATUS_FILTERS = ["active", "inactive"] as const;
export type SchoolStatusFilter = (typeof SCHOOL_STATUS_FILTERS)[number];

export const DEMO_STATUSES = [
  "new",
  "contacted",
  "demo_scheduled",
  "converted",
  "rejected",
] as const;
export type DemoStatus = (typeof DEMO_STATUSES)[number];

export const LIST_PAGE_SIZE = 25;

export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

/** Schools created before these details existed have them blank. */
export type PlatformSchool = {
  id: number;
  name_en: string;
  name_ar: string;
  code: string;
  is_active: boolean;
  created_at: string;
  member_count: number;
  school_admin_email: string | null;
  school_type: SchoolType | "";
  education_stages: EducationStage[];
  email: string;
  phone: string;
  region: SaudiRegion | "";
  city: string;
  address: string;
  cr_number: string;
  moe_license_number: string;
  estimated_students: number | null;
  admin_name: string;
  admin_phone: string;
};

export type SchoolsPage = Page<PlatformSchool>;

export type SchoolCounts = {
  total: number;
  active: number;
  inactive: number;
};

export type CreateSchoolRequest = {
  name_en: string;
  name_ar: string;
  code: string;
  school_type: string;
  education_stages: string[];
  email: string;
  phone: string;
  region: string;
  city: string;
  address: string;
  cr_number: string;
  moe_license_number: string;
  estimated_students: number;
  admin_name: string;
  admin_email: string;
  admin_phone: string;
  demo_request?: number;
};

export type DemoRequest = {
  id: number;
  name: string;
  school_name: string;
  email: string;
  phone: string;
  plan: "basic" | "premium" | "advanced" | "";
  message: string;
  status: DemoStatus;
  admin_notes: string;
  converted_school_code: string | null;
  created_at: string;
};

export type DemoRequestsPage = Page<DemoRequest>;

export type DemoRequestCounts = {
  total: number;
  by_status: Record<DemoStatus, number>;
};

export type UpdateDemoRequest = {
  status?: DemoStatus;
  admin_notes?: string;
};

export type DashboardOverview = {
  schools: SchoolCounts;
  demo_requests: DemoRequestCounts;
  recent_schools: PlatformSchool[];
  recent_demo_requests: DemoRequest[];
};
