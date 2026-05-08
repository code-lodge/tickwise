import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  Category,
  Client,
  CustomRule,
  FreelancerProfile,
  Invoice,
  PomodoroHistoryEntry,
  PomodoroSettings,
  PomodoroStatus,
  PreviewResult,
  Project,
  RedactionLevel,
  Session,
  SettingsMap,
  Status,
  TodaySummary,
} from '../models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = '/api';

  // Status
  status(): Observable<Status> {
    return this.http.get<Status>(`${this.base}/status`);
  }

  // Settings
  settings(): Observable<SettingsMap> {
    return this.http.get<SettingsMap>(`${this.base}/settings`);
  }
  updateSettings(payload: Partial<SettingsMap>): Observable<SettingsMap> {
    return this.http.put<SettingsMap>(`${this.base}/settings`, payload);
  }

  // Sessions
  sessions(params: {
    from?: string;
    to?: string;
    project_id?: number;
    limit?: number;
  } = {}): Observable<Session[]> {
    return this.http.get<Session[]>(`${this.base}/sessions`, {
      params: this.cleanParams(params),
    });
  }
  session(id: number): Observable<Session> {
    return this.http.get<Session>(`${this.base}/sessions/${id}`);
  }
  updateSession(id: number, patch: Partial<Session>): Observable<Session> {
    return this.http.put<Session>(`${this.base}/sessions/${id}`, patch);
  }
  splitSession(id: number, splitAt: string): Observable<Session[]> {
    return this.http.post<Session[]>(`${this.base}/sessions/${id}/split`, {
      split_at: splitAt,
    });
  }
  mergeSessions(id: number, otherId: number): Observable<Session> {
    return this.http.post<Session>(`${this.base}/sessions/${id}/merge`, {
      other_id: otherId,
    });
  }
  deleteSession(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/sessions/${id}`);
  }
  todaySummary(): Observable<TodaySummary> {
    return this.http.get<TodaySummary>(`${this.base}/sessions/summary/today`);
  }

  // Projects
  projects(activeOnly = false): Observable<Project[]> {
    return this.http.get<Project[]>(`${this.base}/projects`, {
      params: activeOnly ? { active_only: 'true' } : {},
    });
  }
  createProject(p: Partial<Project>): Observable<Project> {
    return this.http.post<Project>(`${this.base}/projects`, p);
  }
  updateProject(id: number, p: Partial<Project>): Observable<Project> {
    return this.http.put<Project>(`${this.base}/projects/${id}`, p);
  }
  deleteProject(id: number, hard = false): Observable<void> {
    return this.http.delete<void>(`${this.base}/projects/${id}`, {
      params: hard ? { hard: 'true' } : {},
    });
  }
  reclassifyAll(overwrite = false): Observable<{ scanned: number; matched: number; unchanged: number }> {
    return this.http.post<{ scanned: number; matched: number; unchanged: number }>(
      `${this.base}/projects/reclassify`,
      null,
      { params: overwrite ? { overwrite: 'true' } : {} },
    );
  }

  // Clients
  clients(): Observable<Client[]> {
    return this.http.get<Client[]>(`${this.base}/clients`);
  }
  createClient(c: Partial<Client>): Observable<Client> {
    return this.http.post<Client>(`${this.base}/clients`, c);
  }
  updateClient(id: number, c: Partial<Client>): Observable<Client> {
    return this.http.put<Client>(`${this.base}/clients/${id}`, c);
  }
  deleteClient(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/clients/${id}`);
  }

  // Freelancer profile
  profile(): Observable<FreelancerProfile> {
    return this.http.get<FreelancerProfile>(`${this.base}/profile`);
  }
  updateProfile(p: Partial<FreelancerProfile>): Observable<FreelancerProfile> {
    return this.http.put<FreelancerProfile>(`${this.base}/profile`, p);
  }

  // Invoices
  invoices(status?: string): Observable<Invoice[]> {
    return this.http.get<Invoice[]>(`${this.base}/invoices`, {
      params: status ? { status } : {},
    });
  }
  invoice(id: number): Observable<Invoice> {
    return this.http.get<Invoice>(`${this.base}/invoices/${id}`);
  }
  draftInvoice(payload: {
    project_id: number;
    from_date: string;
    to_date: string;
    rate_override?: number;
    tax_rate_override?: number;
  }): Observable<unknown> {
    return this.http.post<unknown>(`${this.base}/invoices/draft`, payload);
  }
  createInvoice(payload: Partial<Invoice>): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.base}/invoices`, payload);
  }
  updateInvoice(id: number, payload: Partial<Invoice>): Observable<Invoice> {
    return this.http.put<Invoice>(`${this.base}/invoices/${id}`, payload);
  }
  deleteInvoice(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/invoices/${id}`);
  }
  markInvoiceSent(id: number): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.base}/invoices/${id}/mark-sent`, {});
  }
  markInvoicePaid(id: number): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.base}/invoices/${id}/mark-paid`, {});
  }

  // Pomodoro
  pomodoroStatus(): Observable<PomodoroStatus> {
    return this.http.get<PomodoroStatus>(`${this.base}/pomodoro/status`);
  }
  pomodoroSettings(): Observable<PomodoroSettings> {
    return this.http.get<PomodoroSettings>(`${this.base}/pomodoro/settings`);
  }
  updatePomodoroSettings(s: PomodoroSettings): Observable<PomodoroSettings> {
    return this.http.put<PomodoroSettings>(`${this.base}/pomodoro/settings`, s);
  }
  startPomodoro(target: 'focus' | 'short_break' | 'long_break' = 'focus'): Observable<PomodoroStatus> {
    return this.http.post<PomodoroStatus>(`${this.base}/pomodoro/start`, null, {
      params: { target },
    });
  }
  stopPomodoro(): Observable<PomodoroStatus> {
    return this.http.post<PomodoroStatus>(`${this.base}/pomodoro/stop`, {});
  }
  pomodoroHistory(limit = 20): Observable<PomodoroHistoryEntry[]> {
    return this.http.get<PomodoroHistoryEntry[]>(`${this.base}/pomodoro/history`, {
      params: { limit },
    });
  }

  // Categories
  categories(): Observable<Category[]> {
    return this.http.get<Category[]>(`${this.base}/categories`);
  }
  createCategory(c: Partial<Category>): Observable<Category> {
    return this.http.post<Category>(`${this.base}/categories`, c);
  }

  // Redaction
  redactionLevel(): Observable<RedactionLevel> {
    return this.http.get<RedactionLevel>(`${this.base}/redaction/level`);
  }
  setRedactionLevel(level: number): Observable<RedactionLevel> {
    return this.http.put<RedactionLevel>(`${this.base}/redaction/level`, { level });
  }
  rules(): Observable<CustomRule[]> {
    return this.http.get<CustomRule[]>(`${this.base}/redaction/rules`);
  }
  createRule(r: Partial<CustomRule>): Observable<CustomRule> {
    return this.http.post<CustomRule>(`${this.base}/redaction/rules`, r);
  }
  deleteRule(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/redaction/rules/${id}`);
  }
  preview(text: string, level: number): Observable<PreviewResult> {
    return this.http.post<PreviewResult>(`${this.base}/redaction/preview`, { text, level });
  }

  // Helpers
  private cleanParams(p: Record<string, unknown>): Record<string, string> {
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(p)) {
      if (v !== undefined && v !== null && v !== '') out[k] = String(v);
    }
    return out;
  }
}
