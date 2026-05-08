import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import type { CustomRule, PreviewResult, RedactionLevel } from '../../models';

@Component({
  selector: 'app-privacy',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h1>Privacy</h1>
    <p class="muted">
      Tickwise runs entirely on this machine — no cloud, no API keys, no
      subscriptions. Activity is classified by matching keywords from your
      projects against the window title, browser URL, and on-screen text.
      Redaction is applied before any text is stored.
    </p>

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

    <p *ngIf="error()" class="error">{{ error() }}</p>
  `,
  styles: [
    `
      .grid {
        display: grid;
        gap: 1rem;
        grid-template-columns: 1fr 1fr;
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
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.reloadLevel();
    this.reloadRules();
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
}
