import { apiFetch } from "@/lib/api";
import type {
  AuthenticatedResponse,
  LoginRequest,
  MeResponse,
  SwitchSchoolRequest,
  SwitchSchoolResponse,
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

export function requestEmailOtp(email: string) {
  return apiFetch<void>("/auth/email-otp/request/", { method: "POST", body: { email } });
}

export function verifyEmailOtp(email: string, code: string) {
  return apiFetch<AuthenticatedResponse>("/auth/email-otp/verify/", {
    method: "POST",
    body: { email, code },
  });
}
