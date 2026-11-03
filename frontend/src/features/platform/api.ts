import { apiFetch } from "@/lib/api";
import type { CreateSchoolRequest, PlatformSchool, SchoolsPage } from "./schemas";

export function listSchools(page: number, signal?: AbortSignal) {
  return apiFetch<SchoolsPage>(`/platform/schools/?page=${page}`, { signal });
}

export function createSchool(body: CreateSchoolRequest) {
  return apiFetch<PlatformSchool>("/platform/schools/", { method: "POST", body });
}
