import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import type {
  PomodoroHistoryEntry,
  PomodoroSettings,
  PomodoroStatus,
} from '../../models';

@Component({
  selector: 'app-pomodoro',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <header class="hero" *ngIf="status() as s" [attr.data-state]="s.state">
      <div class="eyebrow">POMODORO</div>
      <span class="cl-pill" [class.cl-pill-good]="s.state === 'idle'"
                            [class.cl-pill-warn]="s.state === 'focus'"
                            [class.state-break]="s.state !== 'idle' && s.state !== 'focus'">
        <span class="cl-pill-dot"></span>
        {{ stateLabel(s.state).toUpperCase() }}
      </span>
      <div class="clock">{{ format(s.remaining_secs) }}</div>
      <div class="progress-track" *ngIf="s.duration_secs > 0">
        <div class="progress-fill" [style.width.%]="progressPct(s)"></div>
      </div>
      <p class="hero-sub">
        {{ s.completed_focus_count }} focus periods completed today.
      </p>
      <div class="cta-row">
        <button class="primary" (click)="start('focus')" *ngIf="s.state === 'idle'">Start focus</button>
        <button class="outline" (click)="start('short_break')" *ngIf="s.state === 'idle'">Short break</button>
        <button class="outline" (click)="start('long_break')" *ngIf="s.state === 'idle'">Long break</button>
        <button class="danger" (click)="stop()" *ngIf="s.state !== 'idle'">Stop</button>
      </div>
    </header>

    <details class="card" style="margin-top: 1.25rem">
      <summary>Settings</summary>
      <div *ngIf="settings() as cfg" class="stack" style="margin-top: 0.85rem">
        <div class="row" style="flex-wrap: wrap; gap: 1rem">
          <label class="setting">Work min<input type="number" [(ngModel)]="cfg.work_minutes" min="1" max="180" /></label>
          <label class="setting">Short break<input type="number" [(ngModel)]="cfg.short_break_minutes" min="1" max="60" /></label>
          <label class="setting">Long break<input type="number" [(ngModel)]="cfg.long_break_minutes" min="1" max="120" /></label>
          <label class="setting">Cycles before long
            <input type="number" [(ngModel)]="cfg.cycles_before_long" min="1" max="12" />
          </label>
          <label class="row" style="align-items: center; gap: 0.4rem">
            <input type="checkbox" [(ngModel)]="cfg.auto_start" /> Auto-start next period
          </label>
        </div>
        <div class="row">
          <button (click)="saveSettings()">Save</button>
        </div>
      </div>
    </details>

    <h3 class="section-h">Recent</h3>
    <div class="card">
      <table>
        <thead>
          <tr><th>Type</th><th>Started</th><th>Ended</th><th>Completed</th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let h of history()">
            <td>{{ stateLabel(h.type) }}</td>
            <td>{{ h.started_at }}</td>
            <td>{{ h.ended_at }}</td>
            <td>{{ h.completed ? 'Yes' : 'No' }}</td>
          </tr>
          <tr *ngIf="!history().length"><td colspan="4" class="muted">No sessions yet.</td></tr>
        </tbody>
      </table>
    </div>
  `,
  styles: [
    `
      :host { display: block; }
      .hero {
        text-align: center;
        padding: 2.5rem 2rem 2.2rem;
        border: 1px solid var(--cl-stroke);
        border-radius: var(--cl-radius);
        background: linear-gradient(120deg, rgba(45, 212, 191, 0.10), rgba(56, 189, 248, 0.06));
        box-shadow: var(--cl-shadow-sm);
      }
      .hero[data-state="focus"] {
        background: linear-gradient(120deg, rgba(251, 146, 60, 0.12), rgba(239, 68, 68, 0.05));
      }
      .hero[data-state="short_break"], .hero[data-state="long_break"] {
        background: linear-gradient(120deg, rgba(56, 189, 248, 0.14), rgba(45, 212, 191, 0.06));
      }
      .eyebrow {
        font-family: var(--cl-font-display);
        font-size: 0.72rem; font-weight: 700;
        letter-spacing: 0.18em; text-transform: uppercase;
        color: var(--cl-muted); margin-bottom: 0.6rem;
      }
      .clock {
        font-family: var(--cl-font-display);
        font-size: clamp(4rem, 12vw, 6.5rem);
        font-weight: 700; font-variant-numeric: tabular-nums;
        letter-spacing: -0.04em; line-height: 1;
        margin: 1rem 0 1rem;
        color: var(--cl-text);
      }
      .progress-track {
        max-width: 420px; margin: 0 auto 1rem;
        height: 6px; border-radius: 999px;
        background: rgba(157, 197, 220, 0.12);
        overflow: hidden;
      }
      .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--cl-accent), var(--cl-accent-2));
        transition: width 1s linear;
      }
      .hero-sub { color: var(--cl-muted); margin: 0 0 1rem; font-size: 0.95rem; }
      .cta-row { display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: center; }
      .cta-row .primary {
        background: linear-gradient(120deg, var(--cl-accent), var(--cl-accent-2));
        color: #02151b;
      }
      .cta-row .outline {
        background: transparent;
        border: 1px solid var(--cl-stroke-strong);
        color: var(--cl-text);
      }
      .cta-row .danger { background: var(--cl-critical); color: #fff; }
      .state-break {
        background: rgba(56, 189, 248, 0.12) !important;
        border-color: rgba(56, 189, 248, 0.32) !important;
        color: var(--cl-accent-2) !important;
      }
      details.card summary {
        list-style: none; cursor: pointer; user-select: none;
        font-family: var(--cl-font-display);
        font-size: 0.74rem; letter-spacing: 0.18em;
        text-transform: uppercase; color: var(--cl-muted);
      }
      details.card summary::-webkit-details-marker { display: none; }
      details.card[open] summary { color: var(--cl-text); margin-bottom: 0.5rem; }
      .setting { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: var(--cl-muted); }
      .setting input { font: inherit; font-size: 0.95rem; }
      .section-h {
        font-family: var(--cl-font-display);
        font-size: 0.74rem; letter-spacing: 0.18em;
        text-transform: uppercase; color: var(--cl-muted);
        margin: 1.5rem 0 0.75rem;
      }
    `,
  ],
})
export class PomodoroPageComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);

  status = signal<PomodoroStatus | null>(null);
  settings = signal<PomodoroSettings | null>(null);
  history = signal<PomodoroHistoryEntry[]>([]);
  private interval: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.refreshAll();
    this.interval = setInterval(() => this.refreshStatus(), 1000);
  }

  ngOnDestroy(): void {
    if (this.interval) clearInterval(this.interval);
  }

  refreshAll(): void {
    this.refreshStatus();
    this.api.pomodoroSettings().subscribe((s) => this.settings.set({ ...s }));
    this.refreshHistory();
  }

  refreshStatus(): void {
    this.api.pomodoroStatus().subscribe((s) => this.status.set(s));
  }

  refreshHistory(): void {
    this.api.pomodoroHistory().subscribe((h) => this.history.set(h));
  }

  start(target: 'focus' | 'short_break' | 'long_break'): void {
    this.api.startPomodoro(target).subscribe((s) => {
      this.status.set(s);
      this.refreshHistory();
    });
  }

  stop(): void {
    this.api.stopPomodoro().subscribe((s) => {
      this.status.set(s);
      this.refreshHistory();
    });
  }

  saveSettings(): void {
    const cfg = this.settings();
    if (!cfg) return;
    this.api.updatePomodoroSettings(cfg).subscribe((s) => this.settings.set({ ...s }));
  }

  stateLabel(state: string): string {
    return {
      idle: 'Idle',
      focus: 'Focus',
      work: 'Focus',
      short_break: 'Short break',
      long_break: 'Long break',
    }[state] || state;
  }

  format(secs: number): string {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  progressPct(s: PomodoroStatus): number {
    if (!s.duration_secs) return 0;
    return Math.round(((s.duration_secs - s.remaining_secs) / s.duration_secs) * 100);
  }
}
