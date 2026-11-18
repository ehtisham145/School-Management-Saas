export type Role = "SCHOOL_ADMIN" | "PRINCIPAL" | "TEACHER" | "STUDENT" | "PARENT";

export type School = {
  id: number;
  code: string;
  name_en: string;
  name_ar: string;
  kind?: "school" | "individual";
};

export type Membership = {
  membership_id: number;
  role: Role;
  school: School;
};

export type LoginRequest = {
  username: string;
  password: string;
};

export type AuthenticatedResponse = {
  username: string;
  is_platform_admin: boolean;
  /** The user belongs to schools, but all of them are deactivated. */
  school_inactive: boolean;
  memberships: Membership[];
  /** Only for an individual teacher whose free trial is running. */
  trial: { ends_on: string; days_left: number } | null;
};

export type TeacherSignupDetails = {
  full_name: string;
  email: string;
  password: string;
  accept_privacy: true;
};

export type SwitchSchoolRequest = {
  membership_id: number;
};

export type SwitchSchoolResponse = {
  membership_id: number;
  role: Role;
  school: School;
};

export type MeResponse = AuthenticatedResponse & {
  email: string | null;
  full_name: string;
  active_membership_id: number | null;
};

export type ActiveSession = {
  membershipId: number;
  role: Role;
  school: School;
};

export function toActiveSession(membership: Membership): ActiveSession {
  return {
    membershipId: membership.membership_id,
    role: membership.role,
    school: membership.school,
  };
}
