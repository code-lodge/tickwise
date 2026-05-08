import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  Category,
  Client,
  CustomRule,
  LLMConfig,
  LLMUsage,
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
  deleteProject(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/projects/${id}`);
  }

  // Clients
  clients(): Observable<Client[]> {
    return this.http.get<Client[]>(`${this.base}/clients`);
  }
  createClient(c: Partial<Client>): Observable<Client> {
    return this.http.post<Client>(`${this.base}/clients`, c);
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

  // LLM
  llmConfig(): Observable<LLMConfig> {
    return this.http.get<LLMConfig>(`${this.base}/llm/config`);
  }
  updateLLMConfig(cfg: Partial<LLMConfig>): Observable<LLMConfig> {
    return this.http.put<LLMConfig>(`${this.base}/llm/config`, cfg);
  }
  llmUsage(limit = 25): Observable<LLMUsage> {
    return this.http.get<LLMUsage>(`${this.base}/llm/usage`, { params: { limit } });
  }
  testClassify(payload: {
    process_name?: string;
    window_title?: string;
    ocr_text?: string;
  }): Observable<unknown> {
    return this.http.post<unknown>(`${this.base}/llm/test`, payload);
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
