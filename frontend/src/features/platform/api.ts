import { apiFetch } from "@/lib/api";
import type {
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
