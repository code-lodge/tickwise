// Shared TypeScript types mirroring the FastAPI response shapes.

export interface Status {
  status: string;
  version: string;
  uptime_secs: number;
  tracking: boolean;
}

export interface Session {
  id: number;
  started_at: string;
  ended_at: string | null;
  duration_secs: number | null;
  project_id: number | null;
  category_id: number | null;
  description: string | null;
  tags: string | null;
  is_manual: number;
  is_billed: number;
  invoice_id: number | null;
  llm_classified: number;
  confidence: number | null;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: number;
  name: string;
  color: string;
  client_id: number | null;
  hourly_rate: number | null;
  currency: string;
  is_active: boolean;
  total_seconds: number;
}

export interface Client {
  id: number;
  name: string;
  email: string | null;
  timezone: string;
  address?: string | null;
  tax_id?: string | null;
}

export interface FreelancerProfile {
  name: string;
  email: string;
  company: string | null;
  address: string | null;
  tax_id: string | null;
  iban: string | null;
  bank_name: string | null;
  payment_terms: string | null;
  default_currency: string;
  default_hourly_rate: number | null;
  timezone: string;
  invoice_prefix: string;
  invoice_next_number: number;
  invoice_default_due_days: number;
  invoice_default_tax_rate: number;
  logo_path: string | null;
}

export interface InvoiceLineItem {
  id: number;
  description: string;
  hours: number;
  rate: number;
  amount: number;
  session_id: number | null;
}

export interface Invoice {
  id: number;
  client_id: number | null;
  project_id: number | null;
  invoice_number: string;
  issued_date: string;
  due_date: string | null;
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  total: number;
  currency: string;
  notes: string | null;
  sent_at: string | null;
  paid_at: string | null;
  line_items: InvoiceLineItem[];
}

export interface Category {
  id: number;
  name: string;
  color: string;
  project_id: number | null;
}

export interface RedactionLevel {
  level: number;
  description: string;
  categories: string[];
}

export interface CustomRule {
  id: number;
  pattern: string;
  match_mode: 'contains' | 'regex' | 'exact';
  replacement: string;
  description: string | null;
  is_active: boolean;
}

export interface PreviewResult {
  redacted_text: string;
  original_length: number;
  redacted_length: number;
  redaction_count: number;
  categories_hit: string[];
}

export interface LLMConfig {
  provider: 'anthropic' | 'openai';
  model: string;
  max_tokens: number;
  temperature: number;
  monthly_budget_cents: number;
  is_active: boolean;
  api_key?: string | null;
  has_api_key: boolean;
}

export interface LLMUsage {
  summary: {
    calls: number;
    cache_hits: number;
    prompt_tokens: number;
    completion_tokens: number;
    cost_cents: number;
  };
  budget: {
    spent_cents: number;
    budget_cents: number;
    over_budget: boolean;
  };
  recent: Array<Record<string, unknown>>;
}

export interface TodaySummary {
  total_seconds: number;
  billable_seconds: number;
  session_count: number;
  unclassified_count: number;
  by_project: Array<{ name: string; color: string; seconds: number }>;
}

export interface SettingsMap {
  [key: string]: string;
}

export type PomodoroState = 'idle' | 'focus' | 'short_break' | 'long_break';

export interface PomodoroStatus {
  state: PomodoroState;
  remaining_secs: number;
  duration_secs: number;
  completed_focus_count: number;
  current_session_id: number | null;
  started_at: string | null;
}

export interface PomodoroSettings {
  work_minutes: number;
  short_break_minutes: number;
  long_break_minutes: number;
  cycles_before_long: number;
  auto_start: boolean;
}

export interface PomodoroHistoryEntry {
  id: number;
  type: 'work' | 'short_break' | 'long_break';
  started_at: string;
  ended_at: string | null;
  completed: boolean;
}
