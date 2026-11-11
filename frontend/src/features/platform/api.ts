import { apiDownload, apiFetch } from "@/lib/api";
import type {
  ActivateSubscriptionRequest,
  AuditEventsPage,
  FormChoices,
  Plan,
  PlanInput,
  Quotation,
  QuotationCounts,
  QuotationInput,
  QuotationsPage,
  Subscription,
  SubscriptionCounts,
  SubscriptionsPage,
  UsagePage,
  UsageTotals,
  CreateSchoolRequest,
  DashboardOverview,
  DemoRequest,
  DemoRequestCounts,
  DemoRequestsPage,
  DemoStatus,
  PlatformSchool,
  SchoolCounts,
  SchoolsPage,
  SchoolStatusFilter,
  UpdateDemoRequest,
} from "./schemas";

type ListQuery<Status> = {
  page: number;
  status?: Status;
  search?: string;
};

function toQueryString<Status extends string>({ page, status, search }: ListQuery<Status>) {
  const params = new URLSearchParams({ page: String(page) });
  if (status) params.set("status", status);
  if (search) params.set("search", search);
  return params.toString();
}

export function getDashboard(signal?: AbortSignal) {
  return apiFetch<DashboardOverview>("/platform/dashboard/", { signal });
}

export function listSchools(query: ListQuery<SchoolStatusFilter>, signal?: AbortSignal) {
  return apiFetch<SchoolsPage>(`/platform/schools/?${toQueryString(query)}`, { signal });
}

export function getSchoolCounts(signal?: AbortSignal) {
  return apiFetch<SchoolCounts>("/platform/schools/summary/", { signal });
}

export function createSchool(body: CreateSchoolRequest) {
  return apiFetch<PlatformSchool>("/platform/schools/", { method: "POST", body });
}

export function setSchoolActive(id: number, isActive: boolean) {
  const action = isActive ? "activate" : "deactivate";
  return apiFetch<PlatformSchool>(`/platform/schools/${id}/${action}/`, { method: "POST" });
}

export function listDemoRequests(query: ListQuery<DemoStatus>, signal?: AbortSignal) {
  return apiFetch<DemoRequestsPage>(`/platform/manage/demo-requests/?${toQueryString(query)}`, {
    signal,
  });
}

export function getDemoRequestCounts(signal?: AbortSignal) {
  return apiFetch<DemoRequestCounts>("/platform/manage/demo-requests/summary/", { signal });
}

export function getDemoRequest(id: number, signal?: AbortSignal) {
  return apiFetch<DemoRequest>(`/platform/manage/demo-requests/${id}/`, { signal });
}

export function updateDemoRequest(id: number, body: UpdateDemoRequest) {
  return apiFetch<DemoRequest>(`/platform/manage/demo-requests/${id}/`, { method: "PATCH", body });
}

// --- Billing, usage and the audit log

type Query = Record<string, string | number | undefined>;

function withQuery(path: string, query: Query) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const text = params.toString();
  return text ? `${path}?${text}` : path;
}

export function getFormChoices(signal?: AbortSignal) {
  return apiFetch<FormChoices>("/platform/choices/", { signal });
}

export function listPlans(signal?: AbortSignal) {
  return apiFetch<Plan[]>("/platform/plans/", { signal });
}

export function createPlan(body: PlanInput) {
  return apiFetch<Plan>("/platform/plans/", { method: "POST", body });
}

export function updatePlan(id: number, body: Partial<PlanInput>) {
  return apiFetch<Plan>(`/platform/plans/${id}/`, { method: "PATCH", body });
}

export function listSubscriptions(query: Query, signal?: AbortSignal) {
  return apiFetch<SubscriptionsPage>(withQuery("/platform/subscriptions/", query), { signal });
}

export function getSubscriptionCounts(signal?: AbortSignal) {
  return apiFetch<SubscriptionCounts>("/platform/subscriptions/summary/", { signal });
}

export function activateSubscription(body: ActivateSubscriptionRequest) {
  return apiFetch<Subscription>("/platform/subscriptions/", { method: "POST", body });
}

export function expireSubscription(id: number) {
  return apiFetch<Subscription>(`/platform/subscriptions/${id}/expire/`, { method: "POST" });
}

export function listQuotations(query: Query, signal?: AbortSignal) {
  return apiFetch<QuotationsPage>(withQuery("/platform/quotations/", query), { signal });
}

export function getQuotationCounts(signal?: AbortSignal) {
  return apiFetch<QuotationCounts>("/platform/quotations/summary/", { signal });
}

export function getQuotation(id: number, signal?: AbortSignal) {
  return apiFetch<Quotation>(`/platform/quotations/${id}/`, { signal });
}

export function createQuotation(body: QuotationInput) {
  return apiFetch<Quotation>("/platform/quotations/", { method: "POST", body });
}

export function updateQuotation(id: number, body: Partial<QuotationInput>) {
  return apiFetch<Quotation>(`/platform/quotations/${id}/`, { method: "PATCH", body });
}

export function quotationAction(id: number, action: "send" | "accept" | "reject") {
  return apiFetch<Quotation>(`/platform/quotations/${id}/${action}/`, { method: "POST" });
}

export function downloadQuotationPdf(id: number) {
  return apiDownload(`/platform/quotations/${id}/pdf/`);
}

export function listUsage(query: Query, signal?: AbortSignal) {
  return apiFetch<UsagePage>(withQuery("/platform/usage/", query), { signal });
}

export function getUsageTotals(signal?: AbortSignal) {
  return apiFetch<UsageTotals>("/platform/usage/summary/", { signal });
}

export function listAuditEvents(query: Query, signal?: AbortSignal) {
  return apiFetch<AuditEventsPage>(withQuery("/platform/audit-log/", query), { signal });
}
