export interface Watch {
  id: number;
  subject: string;
  catalog: string;
  component: string | null;
  term_code: string;
  active: boolean;
  created_at: string;
}

export interface WatchInput {
  subject: string;
  catalog: string;
  component: string | null;
  term_code: string | null;
}

export interface Section {
  section: string;
  component: string;
  enrolled_total: number;
  capacity: number;
  status: 'OPEN' | 'FULL';
}

export interface WatchStatus {
  watch_id: number;
  term_code: string;
  checked_at: string;
  sections: Section[];
}
