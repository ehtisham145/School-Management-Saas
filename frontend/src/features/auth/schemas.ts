export type Role = "SCHOOL_ADMIN" | "PRINCIPAL" | "TEACHER" | "STUDENT" | "PARENT";

export type School = {
  id: number;
  code: string;
  name_en: string;
  name_ar: string;
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
  memberships: Membership[];
};

export type Requires2faResponse = {
  requires_2fa: true;
};

export type LoginResponse = AuthenticatedResponse | Requires2faResponse;

export type SwitchSchoolRequest = {
  membership_id: number;
};

export type SwitchSchoolResponse = {
  membership_id: number;
  role: Role;
  school: School;
};

export type MeResponse = {
  username: string;
  active_membership_id: number | null;
  memberships: Membership[];
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
