import { apiFetch } from "@/lib/api";
import type {
  AuthenticatedResponse,
  LoginRequest,
  MeResponse,
  SwitchSchoolRequest,
  SwitchSchoolResponse,
  TeacherSignupDetails,
} from "./schemas";

export function login(body: LoginRequest) {
  return apiFetch<AuthenticatedResponse>("/auth/login/", { method: "POST", body });
}

export function me() {
  return apiFetch<MeResponse>("/auth/me/");
}

export function switchSchool(body: SwitchSchoolRequest) {
  return apiFetch<SwitchSchoolResponse>("/auth/switch-school/", { method: "POST", body });
}

export function logout() {
  return apiFetch<void>("/auth/logout/", { method: "POST" });
}

export function requestTeacherSignup(body: TeacherSignupDetails & { website?: string }) {
  return apiFetch<void>("/auth/teacher-signup/request/", { method: "POST", body });
}

export function verifyTeacherSignup(body: TeacherSignupDetails & { code: string }) {
  return apiFetch<AuthenticatedResponse>("/auth/teacher-signup/verify/", {
    method: "POST",
    body,
  });
}

export function requestPasswordReset(email: string) {
  return apiFetch<void>("/auth/password/reset/request/", { method: "POST", body: { email } });
}

export function confirmPasswordReset(body: { email: string; code: string; password: string }) {
  return apiFetch<AuthenticatedResponse>("/auth/password/reset/confirm/", {
    method: "POST",
    body,
  });
}
