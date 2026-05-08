import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';
import { WebsocketService } from '../../services/websocket.service';
import type { TodaySummary } from '../../models';

@Component({
  selector: 'app-live',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h1>Today</h1>

    <div class="grid">
      <div class="card">
        <div class="muted">Total tracked</div>
        <div class="big">{{ formatHMS(summary()?.total_seconds) }}</div>
        <div class="muted">{{ summary()?.session_count || 0 }} sessions</div>
      </div>
      <div class="card">
        <div class="muted">Billable</div>
        <div class="big">{{ formatHMS(summary()?.billable_seconds) }}</div>
      </div>
      <div class="card">
        <div class="muted">Unclassified</div>
        <div class="big">{{ summary()?.unclassified_count || 0 }}</div>
        <div class="muted" *ngIf="summary()?.unclassified_count">
          Review on the Timeline page.
        </div>
      </div>
      <div class="card">
        <div class="muted">WebSocket</div>
        <div class="big">{{ ws.connected() ? 'Connected' : 'Idle' }}</div>
      </div>
    </div>

    <h2>By project</h2>
    <div class="card stack">
      <div *ngFor="let row of summary()?.by_project || []" class="row">
        <span class="badge" [style.background]="row.color">&nbsp;</span>
        <span>{{ row.name }}</span>
        <span class="muted" style="margin-left:auto">{{ formatHMS(row.seconds) }}</span>
      </div>
      <div *ngIf="!summary()?.by_project?.length" class="muted">No sessions yet today.</div>
    </div>
  `,
  styles: [
    `
      .grid {
        display: grid;
        gap: 0.75rem;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        margin-bottom: 1.25rem;
      }
      .big {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0.25rem 0;
      }
    `,
  ],
})
export class LivePageComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  ws = inject(WebsocketService);
  summary = signal<TodaySummary | null>(null);
  private timer?: ReturnType<typeof setInterval>;

  ngOnInit(): void {
    this.refresh();
    this.timer = setInterval(() => this.refresh(), 4000);
    this.ws.connect();
  }

  ngOnDestroy(): void {
    if (this.timer) clearInterval(this.timer);
  }

  refresh(): void {
    this.api.todaySummary().subscribe({
      next: (s) => this.summary.set(s),
      error: () => this.summary.set(null),
    });
  }

  formatHMS(seconds: number | null | undefined): string {
    const s = seconds ?? 0;
    if (s < 60) return `${s}s`;
    if (s < 3600) return `${Math.floor(s / 60)}m`;
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h ${String(m).padStart(2, '0')}m`;
  }
}
