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
    <h1>Pomodoro</h1>

    <div class="card timer" *ngIf="status() as s">
      <div class="state-pill" [class]="s.state">{{ stateLabel(s.state) }}</div>
      <div class="clock">{{ format(s.remaining_secs) }}</div>
      <progress
        *ngIf="s.duration_secs > 0"
        max="{{ s.duration_secs }}"
        value="{{ s.duration_secs - s.remaining_secs }}"
        style="width: 100%"
      ></progress>
      <p class="muted">
        {{ s.completed_focus_count }} focus periods completed today.
      </p>
      <div class="row">
        <button (click)="start('focus')" *ngIf="s.state === 'idle'">Start focus</button>
        <button (click)="start('short_break')" *ngIf="s.state === 'idle'" class="ghost">
          Short break
        </button>
        <button (click)="start('long_break')" *ngIf="s.state === 'idle'" class="ghost">
          Long break
        </button>
        <button (click)="stop()" *ngIf="s.state !== 'idle'">Stop</button>
      </div>
    </div>

    <details class="card" style="margin-top: 1rem">
      <summary><strong>Settings</strong></summary>
      <div *ngIf="settings() as cfg" class="stack" style="margin-top: 0.75rem">
        <div class="row" style="flex-wrap: wrap">
          <label>Work min <input type="number" [(ngModel)]="cfg.work_minutes" min="1" max="180" /></label>
          <label>Short break <input type="number" [(ngModel)]="cfg.short_break_minutes" min="1" max="60" /></label>
          <label>Long break <input type="number" [(ngModel)]="cfg.long_break_minutes" min="1" max="120" /></label>
          <label>Cycles before long
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

    <div class="card" style="margin-top: 1rem">
      <h2>Recent</h2>
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr><th>Type</th><th>Started</th><th>Ended</th><th>Completed</th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let h of history()" style="border-top: 1px solid var(--color-border)">
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
      .timer { text-align: center; }
      .clock { font-size: 4.5rem; font-variant-numeric: tabular-nums; margin: 0.5rem 0; }
      .state-pill { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.85rem; }
      .state-pill.idle { background: #e2e8f0; color: #475569; }
      .state-pill.focus, .state-pill.work { background: #fee2e2; color: #991b1b; }
      .state-pill.short_break { background: #cffafe; color: #155e75; }
      .state-pill.long_break { background: #dbeafe; color: #1e3a8a; }
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
}
