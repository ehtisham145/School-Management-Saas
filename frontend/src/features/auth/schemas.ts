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

export type LoginResponse = {
  memberships: Membership[];
};

export type SwitchSchoolRequest = {
  membership_id: number;
};

export type SwitchSchoolResponse = {
  membership_id: number;
  role: Role;
  school: School;
};

export type ActiveSession = {
  membershipId: number;
  role: Role;
  school: School;
};
