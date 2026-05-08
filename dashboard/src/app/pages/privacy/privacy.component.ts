import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import type {
  CustomRule,
  LLMConfig,
  LLMUsage,
  PreviewResult,
  RedactionLevel,
} from '../../models';

@Component({
  selector: 'app-privacy',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h1>Privacy &amp; LLM</h1>

    <div class="grid">
      <section class="card stack">
        <h3>Privacy level</h3>
        <p class="muted">{{ levelInfo()?.description }}</p>
        <div class="row">
          <label *ngFor="let n of [1, 2, 3, 4]">
            <input
              type="radio"
              name="level"
              [value]="n"
              [checked]="levelInfo()?.level === n"
              (change)="setLevel(n)"
            />
            Level {{ n }}
          </label>
        </div>
        <details>
          <summary>Active categories ({{ levelInfo()?.categories?.length || 0 }})</summary>
          <code style="font-size:0.75rem; line-height:1.6">
            {{ levelInfo()?.categories?.join(', ') }}
          </code>
        </details>
      </section>

      <section class="card stack">
        <h3>Preview</h3>
        <textarea
          rows="4"
          [(ngModel)]="previewText"
          placeholder="Paste text to redact…"
        ></textarea>
        <button (click)="runPreview()">Run preview</button>
        <div *ngIf="previewResult() as r" class="stack">
          <pre style="white-space: pre-wrap; background: #f1f5f9; padding: 0.5rem; border-radius: 0.375rem">{{ r.redacted_text }}</pre>
          <div class="muted">
            {{ r.original_length }} → {{ r.redacted_length }} chars,
            {{ r.redaction_count }} redactions ({{ r.categories_hit.join(', ') || 'none' }})
          </div>
        </div>
      </section>
    </div>

    <section class="card stack" style="margin-top:1rem">
      <h3>Custom rules</h3>
      <div class="row">
        <input [(ngModel)]="ruleDraft.pattern" placeholder="Pattern" />
        <select [(ngModel)]="ruleDraft.match_mode">
          <option value="contains">contains</option>
          <option value="exact">exact</option>
          <option value="regex">regex</option>
        </select>
        <input [(ngModel)]="ruleDraft.replacement" placeholder="[REDACTED]" />
        <button (click)="createRule()" [disabled]="!ruleDraft.pattern">Add</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Pattern</th>
            <th>Mode</th>
            <th>Replacement</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let r of rules()">
            <td>{{ r.pattern }}</td>
            <td>{{ r.match_mode }}</td>
            <td>{{ r.replacement }}</td>
            <td><button class="danger" (click)="deleteRule(r.id)">Delete</button></td>
          </tr>
          <tr *ngIf="!rules().length">
            <td colspan="4" class="muted">No custom rules yet.</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="card stack" style="margin-top:1rem">
      <h3>LLM configuration</h3>
      <div class="row">
        <label>
          Provider
          <select [(ngModel)]="llmDraft.provider">
            <option value="anthropic">Anthropic</option>
            <option value="openai">OpenAI</option>
          </select>
        </label>
        <label>
          Model
          <input [(ngModel)]="llmDraft.model" />
        </label>
        <label>
          Monthly budget (¢)
          <input type="number" [(ngModel)]="llmDraft.monthly_budget_cents" min="0" />
        </label>
      </div>
      <div class="row">
        <label style="flex:1">
          API key
          <input
            type="password"
            [(ngModel)]="apiKeyInput"
            [placeholder]="llmDraft.has_api_key ? '•••••• (stored)' : 'sk-…'"
          />
        </label>
        <label class="row">
          <input type="checkbox" [(ngModel)]="llmDraft.is_active" /> Active
        </label>
      </div>
      <div class="row">
        <button (click)="saveLLM()">Save</button>
        <button class="ghost" (click)="testLLM()">Run test</button>
      </div>
      <pre *ngIf="testResult()" style="background:#f1f5f9; padding:0.5rem; border-radius:0.375rem">{{ testResult() | json }}</pre>
    </section>

    <section class="card stack" style="margin-top:1rem">
      <h3>Usage</h3>
      <div *ngIf="usage() as u" class="row" style="flex-wrap: wrap; gap: 1.5rem">
        <div>
          <div class="muted">Calls</div>
          <div class="big">{{ u.summary.calls }}</div>
        </div>
        <div>
          <div class="muted">Cache hits</div>
          <div class="big">{{ u.summary.cache_hits }}</div>
        </div>
        <div>
          <div class="muted">Tokens (in/out)</div>
          <div>
            {{ u.summary.prompt_tokens }} / {{ u.summary.completion_tokens }}
          </div>
        </div>
        <div>
          <div class="muted">Spent</div>
          <div class="big">{{ (u.summary.cost_cents / 100) | number: '1.2-2' }} USD</div>
        </div>
        <div>
          <div class="muted">Budget</div>
          <div class="big" [class.error]="u.budget.over_budget">
            {{ u.budget.budget_cents === 0 ? 'unlimited' : (u.budget.spent_cents / 100 | number: '1.2-2') + ' / ' + (u.budget.budget_cents / 100 | number: '1.2-2') }}
          </div>
        </div>
      </div>
    </section>

    <p *ngIf="error()" class="error">{{ error() }}</p>
  `,
  styles: [
    `
      .grid {
        display: grid;
        gap: 1rem;
        grid-template-columns: 1fr 1fr;
      }
      .big {
        font-size: 1.25rem;
        font-weight: 600;
      }
      @media (max-width: 720px) {
        .grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class PrivacyPageComponent implements OnInit {
  private api = inject(ApiService);

  levelInfo = signal<RedactionLevel | null>(null);
  previewText = 'Email me at alice@example.com — token sk-test12345678901234567890abcd';
  previewResult = signal<PreviewResult | null>(null);
  rules = signal<CustomRule[]>([]);
  ruleDraft: Partial<CustomRule> = {
    match_mode: 'contains',
    replacement: '[REDACTED]',
    is_active: true,
  };

  llmDraft: LLMConfig = {
    provider: 'anthropic',
    model: 'claude-haiku-4-5-20251001',
    max_tokens: 256,
    temperature: 0,
    monthly_budget_cents: 0,
    is_active: true,
    has_api_key: false,
  };
  apiKeyInput = '';
  testResult = signal<unknown>(null);
  usage = signal<LLMUsage | null>(null);
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.reloadLevel();
    this.reloadRules();
    this.api.llmConfig().subscribe((c) => (this.llmDraft = c));
    this.reloadUsage();
  }

  setLevel(level: number): void {
    this.api.setRedactionLevel(level).subscribe((info) => this.levelInfo.set(info));
  }
  reloadLevel(): void {
    this.api.redactionLevel().subscribe((l) => this.levelInfo.set(l));
  }
  reloadRules(): void {
    this.api.rules().subscribe((r) => this.rules.set(r));
  }
  reloadUsage(): void {
    this.api.llmUsage().subscribe((u) => this.usage.set(u));
  }

  runPreview(): void {
    const level = this.levelInfo()?.level ?? 2;
    this.api.preview(this.previewText, level).subscribe({
      next: (r) => this.previewResult.set(r),
      error: (err) => this.error.set(err.message),
    });
  }

  createRule(): void {
    if (!this.ruleDraft.pattern) return;
    this.api.createRule(this.ruleDraft).subscribe(() => {
      this.ruleDraft = { match_mode: 'contains', replacement: '[REDACTED]', is_active: true };
      this.reloadRules();
    });
  }

  deleteRule(id: number): void {
    this.api.deleteRule(id).subscribe(() => this.reloadRules());
  }

  saveLLM(): void {
    const payload: Partial<LLMConfig> = { ...this.llmDraft };
    if (this.apiKeyInput) {
      payload.api_key = this.apiKeyInput;
    }
    this.api.updateLLMConfig(payload).subscribe({
      next: (c) => {
        this.llmDraft = c;
        this.apiKeyInput = '';
        this.reloadUsage();
      },
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }

  testLLM(): void {
    this.api.testClassify({}).subscribe({
      next: (r) => this.testResult.set(r),
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }
}
