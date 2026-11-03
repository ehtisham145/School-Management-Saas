export type PlatformSchool = {
  id: number;
  name_en: string;
  name_ar: string;
  code: string;
  is_active: boolean;
  created_at: string;
  member_count: number;
};

export type SchoolsPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: PlatformSchool[];
};

export type CreateSchoolRequest = {
  name_en: string;
  name_ar: string;
  code: string;
  admin_email: string;
};

export const SCHOOLS_PAGE_SIZE = 25;
