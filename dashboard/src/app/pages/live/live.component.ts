import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { WebsocketService } from '../../services/websocket.service';
import type { TodaySummary } from '../../models';

@Component({
  selector: 'app-live',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <header class="hero">
      <div>
        <div class="eyebrow">{{ todayLabel() }}</div>
        <h1>Tickwise <span class="cl-accent-text">Live</span></h1>
        <p class="sub">
          Capture loop running locally — every screen change feeds the keyword matcher.
          {{ summary()?.session_count || 0 }} sessions today, {{ summary()?.unclassified_count || 0 }} still need a project.
        </p>
        <div class="cta-row">
          <span class="cl-pill" [class.cl-pill-good]="ws.connected()" [class.cl-pill-warn]="!ws.connected()">
            <span class="cl-pill-dot"></span>
            {{ ws.connected() ? 'TRACKING' : 'WAITING' }}
          </span>
          <a class="btn-grad" routerLink="/timeline">View Timeline →</a>
          <a class="btn-outline" routerLink="/projects">Manage projects</a>
        </div>
      </div>
    </header>

    <section class="stats">
      <article class="stat">
        <div class="eyebrow">TOTAL TRACKED</div>
        <div class="num">{{ formatHM(summary()?.total_seconds) }}</div>
        <div class="foot">{{ summary()?.session_count || 0 }} sessions</div>
      </article>
      <article class="stat">
        <div class="eyebrow">BILLABLE</div>
        <div class="num cl-accent-text">{{ formatHM(summary()?.billable_seconds) }}</div>
        <div class="foot">{{ billablePct() }}% of tracked</div>
      </article>
      <article class="stat">
        <div class="eyebrow">UNCLASSIFIED</div>
        <div class="num" [class.warn]="(summary()?.unclassified_count || 0) > 0">
          {{ summary()?.unclassified_count || 0 }}
        </div>
        <div class="foot">
          <a *ngIf="(summary()?.unclassified_count || 0) > 0" routerLink="/timeline">Review on Timeline →</a>
          <span *ngIf="!(summary()?.unclassified_count || 0)">Everything's tagged</span>
        </div>
      </article>
      <article class="stat">
        <div class="eyebrow">BROWSER BRIDGE</div>
        <div class="num" [class.good]="ws.connected()">{{ ws.connected() ? 'Connected' : 'Idle' }}</div>
        <div class="foot">{{ ws.connected() ? 'Extension live' : 'Install the extension' }}</div>
      </article>
    </section>

    <h3 class="section-h">By project</h3>
    <div class="rows">
      <div *ngFor="let row of summary()?.by_project || []" class="row-card">
        <span class="dot" [style.background]="row.color"></span>
        <span class="name">{{ row.name }}</span>
        <span class="bar"><span [style.width.%]="pct(row.seconds)"></span></span>
        <span class="time">{{ formatHM(row.seconds) }}</span>
      </div>
      <div *ngIf="!summary()?.by_project?.length" class="muted">No sessions yet today.</div>
    </div>
  `,
  styles: [
    `
      :host { display: block; }

      .hero {
        background:
          linear-gradient(120deg, rgba(45, 212, 191, 0.10), rgba(56, 189, 248, 0.06));
        border: 1px solid var(--cl-stroke);
        border-radius: var(--cl-radius);
        padding: 2rem 2.2rem;
        margin-bottom: 1.25rem;
        box-shadow: var(--cl-shadow-sm);
      }
      .eyebrow {
        font-family: var(--cl-font-display);
        font-size: 0.72rem; font-weight: 700;
        letter-spacing: 0.18em; text-transform: uppercase;
        color: var(--cl-muted); margin-bottom: 0.5rem;
      }
      .hero h1 {
        font-size: clamp(2rem, 4.5vw, 2.8rem);
        margin: 0 0 0.5rem;
        font-family: var(--cl-font-display);
        font-weight: 700; letter-spacing: -0.03em;
      }
      .hero .sub {
        color: var(--cl-muted);
        margin: 0 0 1.2rem;
        font-size: 1rem;
        max-width: 720px;
      }
      .cta-row { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center; }

      /* Buttons that override the global gradient default */
      .btn-grad {
        display: inline-flex; align-items: center; gap: 0.45rem;
        padding: 0.65rem 1.2rem;
        background: linear-gradient(120deg, var(--cl-accent), var(--cl-accent-2));
        color: #02151b !important;
        border-radius: var(--cl-radius-sm);
        font-weight: 700; font-size: 0.9rem;
        text-decoration: none;
        transition: transform 0.12s var(--cl-ease), opacity 0.12s var(--cl-ease);
      }
      .btn-grad:hover { transform: translateY(-1px); opacity: 0.92; text-decoration: none; }
      .btn-outline {
        display: inline-flex; align-items: center; gap: 0.45rem;
        padding: 0.65rem 1.2rem;
        background: transparent;
        border: 1px solid var(--cl-stroke-strong);
        color: var(--cl-text) !important;
        border-radius: var(--cl-radius-sm);
        font-weight: 600; font-size: 0.9rem;
        text-decoration: none;
        transition: background 0.12s var(--cl-ease);
      }
      .btn-outline:hover { background: rgba(157, 197, 220, 0.06); text-decoration: none; }

      .stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
        gap: 0.85rem;
        margin-bottom: 1.6rem;
      }
      .stat {
        background: var(--cl-bg-2);
        border: 1px solid var(--cl-stroke);
        border-radius: var(--cl-radius);
        padding: 1.2rem 1.3rem;
        display: flex; flex-direction: column; gap: 0.4rem;
      }
      .stat .num {
        font-family: var(--cl-font-display);
        font-size: 2rem; font-weight: 700;
        letter-spacing: -0.02em; line-height: 1;
        color: var(--cl-text);
      }
      .stat .num.warn { color: var(--cl-accent-warm); }
      .stat .num.good { color: var(--cl-good); }
      .stat .foot { color: var(--cl-muted); font-size: 0.78rem; }
      .stat .foot a { color: var(--cl-accent); }

      .section-h {
        font-family: var(--cl-font-display);
        font-size: 0.74rem; letter-spacing: 0.18em;
        text-transform: uppercase; color: var(--cl-muted);
        margin: 0.5rem 0 0.85rem;
      }
      .rows { display: flex; flex-direction: column; gap: 0.5rem; }
      .row-card {
        display: flex; align-items: center; gap: 0.85rem;
        padding: 0.75rem 1rem;
        background: var(--cl-bg-2);
        border: 1px solid var(--cl-stroke);
        border-radius: var(--cl-radius-sm);
        font-size: 0.92rem;
      }
      .dot { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
      .name { flex: 1; }
      .bar {
        width: 220px; height: 6px;
        background: rgba(157, 197, 220, 0.10);
        border-radius: 3px; overflow: hidden; flex-shrink: 0;
      }
      .bar > span {
        display: block; height: 100%;
        background: linear-gradient(90deg, var(--cl-accent), var(--cl-accent-2));
        transition: width 0.4s var(--cl-ease);
      }
      .time {
        font-family: var(--cl-font-mono); font-size: 0.84rem;
        color: var(--cl-muted); width: 60px; text-align: right;
      }

      @media (max-width: 720px) {
        .hero { padding: 1.4rem 1.4rem; }
        .bar { display: none; }
      }
    `,
  ],
})
export class LivePageComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  ws = inject(WebsocketService);
  summary = signal<TodaySummary | null>(null);
  private timer?: ReturnType<typeof setInterval>;

  todayLabel = computed(() => {
    const d = new Date();
    return d.toLocaleDateString(undefined, { weekday: 'long', day: '2-digit', month: 'short' }).toUpperCase();
  });

  billablePct = computed(() => {
    const s = this.summary();
    if (!s || !s.total_seconds) return 0;
    return Math.round((s.billable_seconds / s.total_seconds) * 100);
  });

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

  pct(seconds: number): number {
    const s = this.summary();
    if (!s || !s.total_seconds) return 0;
    return Math.round((seconds / s.total_seconds) * 100);
  }

  formatHM(seconds: number | null | undefined): string {
    const s = seconds ?? 0;
    if (s < 60) return `${s}s`;
    if (s < 3600) return `${Math.floor(s / 60)}m`;
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h ${String(m).padStart(2, '0')}m`;
  }
}
