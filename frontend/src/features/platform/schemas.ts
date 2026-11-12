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
  plan: "basic" | "premium" | "custom" | "teacher" | "teacher_pro" | "";
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

// --- Billing. Money comes from the API as text ("1500.00"). It is parsed into a number
// only for display, never for storing or sending.

export const BILLING_CYCLES = ["monthly", "yearly"] as const;
export type BillingCycle = (typeof BILLING_CYCLES)[number];

export type SchoolRef = { id: number; code: string; name_en: string; name_ar: string };
export type PlanRef = { id: number; code: string; name_en: string; name_ar: string };

export type Plan = PlanRef & {
  monthly_price: string;
  yearly_price: string;
  max_students: number | null;
  is_active: boolean;
  active_subscriptions: number;
  created_at: string;
};

export type PlanInput = {
  code?: string;
  name_en: string;
  name_ar: string;
  monthly_price: string;
  yearly_price: string;
  max_students: number | null;
  is_active: boolean;
};

export const SUBSCRIPTION_STATUSES = ["active", "expired"] as const;
export type SubscriptionStatus = (typeof SUBSCRIPTION_STATUSES)[number];

export type Subscription = {
  id: number;
  school: SchoolRef;
  plan: PlanRef;
  billing_cycle: BillingCycle;
  price: string;
  starts_on: string;
  ends_on: string;
  status: SubscriptionStatus;
  expired_at: string | null;
  notes: string;
  created_at: string;
};

export type SubscriptionsPage = Page<Subscription>;

export type SubscriptionCounts = { total: number; active: number; expired: number };

export type ActivateSubscriptionRequest = {
  school: number;
  plan: number;
  billing_cycle: BillingCycle;
  starts_on: string;
  price: string | null;
  notes: string;
};

export const QUOTATION_STATUSES = ["draft", "sent", "accepted", "rejected"] as const;
export type QuotationStatus = (typeof QUOTATION_STATUSES)[number];
export const QUOTATION_LANGUAGES = ["en", "ar"] as const;
export type QuotationLanguage = (typeof QUOTATION_LANGUAGES)[number];

export type QuotationItem = {
  description: string;
  quantity: number;
  unit_price: string;
  amount: string;
};

export type Quotation = {
  id: number;
  number: string;
  status: QuotationStatus;
  is_expired: boolean;
  school: SchoolRef | null;
  demo_request: number | null;
  recipient_name: string;
  recipient_email: string;
  recipient_organization: string;
  language: QuotationLanguage;
  plan: PlanRef | null;
  billing_cycle: BillingCycle | "";
  valid_until: string;
  vat_rate: string;
  subtotal: string;
  vat_amount: string;
  total: string;
  notes: string;
  items: QuotationItem[];
  sent_at: string | null;
  responded_at: string | null;
  created_at: string;
  updated_at: string;
};

export type QuotationsPage = Page<Quotation>;

export type QuotationCounts = {
  total: number;
  by_status: Record<QuotationStatus, number>;
};

export type QuotationItemInput = { description: string; quantity: number; unit_price: string };

export type QuotationInput = {
  school?: number | null;
  demo_request?: number | null;
  language: QuotationLanguage;
  plan: number | null;
  billing_cycle: BillingCycle | "";
  valid_until: string;
  vat_rate: string;
  notes: string;
  recipient_name: string;
  recipient_email: string;
  recipient_organization: string;
  items: QuotationItemInput[];
};

export type ChoicePlan = PlanRef & {
  monthly_price: string;
  yearly_price: string;
  max_students: number | null;
};

export type FormChoices = {
  schools: (SchoolRef & { email: string })[];
  demo_requests: { id: number; name: string; school_name: string; email: string }[];
  plans: ChoicePlan[];
};

export type SchoolUsage = {
  id: number;
  code: string;
  name_en: string;
  name_ar: string;
  is_active: boolean;
  estimated_students: number | null;
  students: number;
  teachers: number;
  parents: number;
  staff: number;
  active_users: number;
  plan: { code: string; name_en: string; name_ar: string; max_students: number | null } | null;
  subscription_ends_on: string | null;
  over_student_limit: boolean;
};

export type UsagePage = Page<SchoolUsage>;

export type UsageTotals = {
  active_schools: number;
  active_subscriptions: number;
  active_user_days: number;
  students: number;
  teachers: number;
  parents: number;
  staff: number;
  active_users: number;
};

export const AUDIT_ACTIONS = [
  "school.created",
  "school.activated",
  "school.deactivated",
  "demo_request.updated",
  "plan.created",
  "plan.updated",
  "subscription.activated",
  "subscription.expired",
  "quotation.created",
  "quotation.updated",
  "quotation.sent",
  "quotation.accepted",
  "quotation.rejected",
] as const;
export type AuditAction = (typeof AUDIT_ACTIONS)[number];

export type AuditEvent = {
  id: number;
  action: AuditAction;
  actor_label: string;
  target_type: string;
  target_id: number;
  target_label: string;
  school: SchoolRef | null;
  ip_address: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

export type AuditEventsPage = Page<AuditEvent>;
