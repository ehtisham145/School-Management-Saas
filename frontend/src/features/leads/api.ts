import { apiFetch } from "@/lib/api";

export const PLANS = ["basic", "premium", "custom", "teacher", "teacher_pro"] as const;
export type Plan = (typeof PLANS)[number];

export type DemoRequestBody = {
  name: string;
  school_name: string;
  email: string;
  phone: string;
  plan: Plan | "";
  message: string;
  website: string;
};

export type ContactMessageBody = {
  name: string;
  school_name: string;
  email: string;
  message: string;
  website: string;
};

export function createDemoRequest(body: DemoRequestBody) {
  return apiFetch<void>("/platform/demo-requests/", { method: "POST", body });
}

export function createContactMessage(body: ContactMessageBody) {
  return apiFetch<void>("/platform/contact-messages/", { method: "POST", body });
}
