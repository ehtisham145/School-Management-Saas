import { apiFetch } from "@/lib/api";
import type {
  LoginRequest,
  LoginResponse,
  SwitchSchoolRequest,
  SwitchSchoolResponse,
} from "./schemas";

export function login(body: LoginRequest) {
  return apiFetch<LoginResponse>("/auth/login/", { method: "POST", body });
}

export function switchSchool(body: SwitchSchoolRequest) {
  return apiFetch<SwitchSchoolResponse>("/auth/switch-school/", { method: "POST", body });
}

export function logout() {
  return apiFetch<void>("/auth/logout/", { method: "POST" });
}
