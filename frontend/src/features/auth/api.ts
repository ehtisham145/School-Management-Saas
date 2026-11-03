import { apiFetch } from "@/lib/api";
import type {
  AuthenticatedResponse,
  LoginRequest,
  LoginResponse,
  MeResponse,
  SwitchSchoolRequest,
  SwitchSchoolResponse,
} from "./schemas";

export function login(body: LoginRequest) {
  return apiFetch<LoginResponse>("/auth/login/", { method: "POST", body });
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

export function verifyTotp(token: string) {
  return apiFetch<AuthenticatedResponse>("/auth/2fa/verify/", {
    method: "POST",
    body: { token },
  });
}

export function requestTotpReset() {
  return apiFetch<void>("/auth/2fa/reset/request/", { method: "POST" });
}

export function confirmTotpReset(code: string) {
  return apiFetch<AuthenticatedResponse>("/auth/2fa/reset/confirm/", {
    method: "POST",
    body: { code },
  });
}

export function requestEmailOtp(email: string) {
  return apiFetch<void>("/auth/email-otp/request/", { method: "POST", body: { email } });
}

export function verifyEmailOtp(email: string, code: string) {
  return apiFetch<LoginResponse>("/auth/email-otp/verify/", {
    method: "POST",
    body: { email, code },
  });
}
