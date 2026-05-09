import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Chart, registerables } from 'chart.js';
import { ApiService } from '../../services/api.service';
import type { Project } from '../../models';

Chart.register(...registerables);

type ReportType = 'summary' | 'billing' | 'activity' | 'detailed' | 'productivity';
type ExportFormat = 'json' | 'csv' | 'ics';

interface SummaryRow { project: string; seconds: number }
interface SummarySeries { bucket: string; project: string; seconds: number }
interface SummaryReport {
  type: 'summary';
  from: string;
  to: string;
  group_by: 'day' | 'week' | 'month';
  by_project: SummaryRow[];
  series: SummarySeries[];
  total_seconds: number;
}
interface BillingRow {
  project: string;
  currency: string;
  billable_seconds: number;
  non_billable_seconds: number;
  amount: number;
  rate: number;
}
interface BillingReport {
  type: 'billing';
  from: string;
  to: string;
  by_project: BillingRow[];
  grand_total_amount: number;
  non_billable_seconds: number;
}
interface ActivityRow { category: string; project: string; seconds: number; sessions: number }
interface ActivityReport { type: 'activity'; from: string; to: string; rows: ActivityRow[] }
interface DetailedSession {
  id: number;
  started_at: string;
  ended_at: string | null;
  duration_secs: number;
  project: string | null;
  description: string | null;
  is_billed: boolean;
}
interface DetailedReport { type: 'detailed'; from: string; to: string; sessions: DetailedSession[] }
interface ProductivityReport {
  type: 'productivity';
  from: string;
  to: string;
  active_seconds: number;
  classified_seconds: number;
  active_by_hour: { hour: number; seconds: number }[];
  pomodoro: { type: string; total: number; completed: number }[];
}
type ReportData =
  | SummaryReport
  | BillingReport
  | ActivityReport
  | DetailedReport
  | ProductivityReport;

// Code Lodge palette — keep charts on-brand without inline magic numbers.
const PALETTE = [
  '#2dd4bf', '#38bdf8', '#fb923c', '#7c6af7', '#22c55e',
  '#ef4444', '#eab308', '#06b6d4', '#a78bfa', '#f472b6',
];
const PALETTE_TRANSLUCENT = PALETTE.map((c) => c + 'cc');

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="reports-screen">
      <!-- Filter bar — printed out in print mode -->
      <header class="hero no-print">
        <div class="hero-left">
          <div class="eyebrow">REPORTS</div>
          <h1>{{ titleFor(type) }}</h1>
          <p class="hero-sub">
            Generate a beautiful, printable report. Use your browser's
            <strong>Print → Save as PDF</strong> for a high-quality export
            with charts intact.
          </p>
        </div>
      </header>

      <div class="card no-print" style="margin-bottom: 1rem">
        <div class="row" style="flex-wrap: wrap; align-items: end; gap: .75rem">
          <label>
            <span class="muted small">Type</span>
            <select [(ngModel)]="type" (ngModelChange)="run()">
              <option value="summary">Time summary</option>
              <option value="billing">Billing</option>
              <option value="activity">Activity</option>
              <option value="detailed">Detailed log</option>
              <option value="productivity">Productivity</option>
            </select>
          </label>
          <label>
            <span class="muted small">From</span>
            <input type="date" [(ngModel)]="fromDate" (ngModelChange)="run()" />
          </label>
          <label>
            <span class="muted small">To</span>
            <input type="date" [(ngModel)]="toDate" (ngModelChange)="run()" />
          </label>
          <label *ngIf="type === 'summary'">
            <span class="muted small">Group by</span>
            <select [(ngModel)]="groupBy" (ngModelChange)="run()">
              <option value="day">Day</option>
              <option value="week">Week</option>
              <option value="month">Month</option>
            </select>
          </label>
          <span style="flex: 1"></span>
          <button class="primary" (click)="print()" [disabled]="!result()">
            Save as PDF
          </button>
          <button class="ghost" (click)="download('csv')" [disabled]="!result()">CSV</button>
          <button class="ghost" (click)="download('json')" [disabled]="!result()">JSON</button>
          <button class="ghost" *ngIf="type === 'detailed'" (click)="download('ics')" [disabled]="!result()">
            ICS
          </button>
        </div>
        <p *ngIf="error()" class="error" style="margin-top:.75rem">{{ error() }}</p>
      </div>

      <!-- Printed report -->
      <div class="report-sheet" *ngIf="result() as r">
        <div class="report-head">
          <div>
            <div class="brand-mark">TICKWISE</div>
            <h2>{{ titleFor(r.type) }}</h2>
            <p class="muted">{{ formatRange(r.from, r.to) }}</p>
          </div>
          <div class="report-meta">
            <span class="muted small">Generated</span>
            <strong>{{ generatedAt }}</strong>
          </div>
        </div>

        <!-- KPI tiles -->
        <div class="kpi-grid" *ngIf="kpis().length">
          <div class="kpi-tile" *ngFor="let k of kpis()">
            <span class="kpi-label">{{ k.label }}</span>
            <span class="kpi-value">{{ k.value }}</span>
            <span class="kpi-sub muted small" *ngIf="k.sub">{{ k.sub }}</span>
          </div>
        </div>

        <!-- Charts row(s) — variable per report type -->
        <ng-container [ngSwitch]="r.type">
          <ng-container *ngSwitchCase="'summary'">
            <div class="chart-row">
              <div class="chart-card chart-card-tall">
                <h3>Time by project · {{ summary().group_by }}</h3>
                <canvas #chartA></canvas>
              </div>
              <div class="chart-card">
                <h3>Project share</h3>
                <canvas #chartB></canvas>
              </div>
            </div>
          </ng-container>

          <ng-container *ngSwitchCase="'billing'">
            <div class="chart-row">
              <div class="chart-card chart-card-tall">
                <h3>Revenue by project</h3>
                <canvas #chartA></canvas>
              </div>
              <div class="chart-card">
                <h3>Billable vs non-billable</h3>
                <canvas #chartB></canvas>
              </div>
            </div>
          </ng-container>

          <ng-container *ngSwitchCase="'activity'">
            <div class="chart-row">
              <div class="chart-card chart-card-tall">
                <h3>Hours by category</h3>
                <canvas #chartA></canvas>
              </div>
              <div class="chart-card">
                <h3>Top projects</h3>
                <canvas #chartB></canvas>
              </div>
            </div>
          </ng-container>

          <ng-container *ngSwitchCase="'productivity'">
            <div class="chart-row">
              <div class="chart-card chart-card-tall">
                <h3>Active hours by time of day</h3>
                <canvas #chartA></canvas>
              </div>
              <div class="chart-card">
                <h3>Pomodoro completion</h3>
                <canvas #chartB></canvas>
              </div>
            </div>
          </ng-container>

          <ng-container *ngSwitchCase="'detailed'">
            <p class="muted" style="margin: 0.25rem 0 1rem 0">
              {{ detailed().sessions.length }} sessions in range.
            </p>
          </ng-container>
        </ng-container>

        <!-- Detail tables per report type -->
        <ng-container [ngSwitch]="r.type">
          <table *ngSwitchCase="'summary'" class="report-table">
            <thead><tr><th>Project</th><th class="num">Hours</th><th class="num">Share</th></tr></thead>
            <tbody>
              <tr *ngFor="let row of summary().by_project">
                <td>{{ row.project }}</td>
                <td class="num">{{ (row.seconds / 3600) | number: '1.2-2' }}</td>
                <td class="num">{{ pctOfTotal(row.seconds, summary().total_seconds) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr><td>Total</td>
                <td class="num">{{ (summary().total_seconds / 3600) | number: '1.2-2' }}</td>
                <td></td></tr>
            </tfoot>
          </table>

          <table *ngSwitchCase="'billing'" class="report-table">
            <thead>
              <tr>
                <th>Project</th>
                <th class="num">Billable hrs</th>
                <th class="num">Rate</th>
                <th class="num">Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let row of billing().by_project">
                <td>{{ row.project }}</td>
                <td class="num">{{ (row.billable_seconds / 3600) | number: '1.2-2' }}</td>
                <td class="num">{{ row.rate | number: '1.2-2' }} {{ row.currency }}</td>
                <td class="num">{{ row.amount | number: '1.2-2' }} {{ row.currency }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td colspan="3">Total</td>
                <td class="num">{{ billing().grand_total_amount | number: '1.2-2' }}</td>
              </tr>
            </tfoot>
          </table>

          <table *ngSwitchCase="'activity'" class="report-table">
            <thead><tr><th>Category</th><th>Project</th><th class="num">Hours</th><th class="num">Sessions</th></tr></thead>
            <tbody>
              <tr *ngFor="let row of activity().rows">
                <td>{{ row.category }}</td>
                <td>{{ row.project }}</td>
                <td class="num">{{ (row.seconds / 3600) | number: '1.2-2' }}</td>
                <td class="num">{{ row.sessions }}</td>
              </tr>
            </tbody>
          </table>

          <table *ngSwitchCase="'detailed'" class="report-table">
            <thead>
              <tr>
                <th>Started</th><th>Ended</th><th class="num">Hours</th>
                <th>Project</th><th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let s of detailed().sessions">
                <td>{{ formatDate(s.started_at) }}</td>
                <td>{{ s.ended_at ? formatDate(s.ended_at) : '—' }}</td>
                <td class="num">{{ (s.duration_secs / 3600) | number: '1.2-2' }}</td>
                <td>{{ s.project || '—' }}</td>
                <td class="desc">{{ s.description || '' }}</td>
              </tr>
            </tbody>
          </table>

          <table *ngSwitchCase="'productivity'" class="report-table">
            <thead><tr><th>Pomodoro type</th><th class="num">Total</th><th class="num">Completed</th><th class="num">Rate</th></tr></thead>
            <tbody>
              <tr *ngFor="let p of productivity().pomodoro">
                <td>{{ p.type }}</td>
                <td class="num">{{ p.total }}</td>
                <td class="num">{{ p.completed }}</td>
                <td class="num">{{ p.total ? (p.completed / p.total * 100 | number:'1.0-0') + '%' : '—' }}</td>
              </tr>
              <tr *ngIf="!productivity().pomodoro.length">
                <td colspan="4" class="muted">No pomodoro sessions in this range.</td>
              </tr>
            </tbody>
          </table>
        </ng-container>

        <footer class="report-foot muted small">
          Tickwise — privacy-first time tracking · tickwise.app
        </footer>
      </div>

      <div *ngIf="!result() && !error()" class="card empty no-print">
        <p class="muted">Select a type and date range to generate a report.</p>
      </div>
    </div>
  `,
  styles: [`
    .reports-screen { display: block; }

    /* Report sheet — sized to look right on screen and on A4 */
    .report-sheet {
      background: var(--cl-panel, #0c1d2a);
      border: 1px solid var(--cl-stroke, rgba(157,197,220,.18));
      border-radius: var(--cl-radius, 14px);
      padding: 2rem 2.25rem;
      box-shadow: var(--cl-shadow-md);
    }
    .report-head {
      display: flex; justify-content: space-between; align-items: flex-start;
      gap: 2rem; margin-bottom: 1.25rem;
      padding-bottom: 1rem; border-bottom: 1px solid var(--cl-stroke);
    }
    .brand-mark {
      font-family: var(--cl-font-display);
      letter-spacing: .25em; font-size: .7rem;
      color: var(--cl-accent, #2dd4bf); margin-bottom: .25rem;
    }
    .report-head h2 { margin: 0 0 .15rem 0; font-family: var(--cl-font-display); font-size: 1.65rem; }
    .report-meta { text-align: right; display: flex; flex-direction: column; gap: .15rem }
    .report-foot {
      margin-top: 1.5rem; padding-top: .75rem;
      border-top: 1px solid var(--cl-stroke);
      text-align: center;
    }

    /* KPI tiles */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: .75rem; margin-bottom: 1.25rem;
    }
    .kpi-tile {
      background: var(--cl-bg-2, #0c1d2a);
      border: 1px solid var(--cl-stroke); border-radius: var(--cl-radius-sm, 8px);
      padding: .85rem 1rem;
      display: flex; flex-direction: column; gap: .15rem;
    }
    .kpi-label {
      font-size: .65rem; font-weight: 600; letter-spacing: .12em;
      text-transform: uppercase; color: var(--cl-muted);
    }
    .kpi-value {
      font-family: var(--cl-font-display);
      font-size: 1.5rem; font-weight: 600; color: var(--cl-text);
    }

    /* Chart cards */
    .chart-row {
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 1rem;
      margin-bottom: 1.25rem;
    }
    .chart-card {
      background: var(--cl-bg-2, #0c1d2a);
      border: 1px solid var(--cl-stroke);
      border-radius: var(--cl-radius-sm);
      padding: 1rem 1rem .5rem;
      display: flex; flex-direction: column;
    }
    .chart-card h3 {
      margin: 0 0 .5rem 0; font-size: .9rem; font-weight: 600;
      color: var(--cl-text);
    }
    .chart-card canvas { width: 100% !important; height: 240px !important; }
    .chart-card-tall canvas { height: 280px !important; }

    /* Table */
    .report-table {
      width: 100%; border-collapse: collapse;
      font-size: .9rem;
    }
    .report-table th, .report-table td {
      padding: .55rem .75rem;
      border-bottom: 1px solid var(--cl-stroke);
      text-align: left;
    }
    .report-table th {
      font-weight: 600; font-size: .72rem; letter-spacing: .08em;
      text-transform: uppercase; color: var(--cl-muted);
      background: rgba(255,255,255,0.02);
    }
    .report-table td.num, .report-table th.num { text-align: right; font-variant-numeric: tabular-nums; }
    .report-table tfoot td { font-weight: 600; border-top: 2px solid var(--cl-stroke); }
    .report-table td.desc { max-width: 24rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }

    .small { font-size: .75rem }
    .empty { text-align: center; padding: 3rem 1rem }

    /* ── PRINT — turn the dashboard into a clean white sheet ─────────── */
    @media print {
      :host { display: block; }
      .no-print { display: none !important; }

      /* Strip sidebars / nav from the surrounding shell. The dashboard
         shell uses common element selectors so the print rule lives
         here for portability. */
      :global(body), :global(html) {
        background: #fff !important; color: #0f172a !important;
      }

      .report-sheet {
        background: #fff !important;
        color: #0f172a !important;
        border: none !important; box-shadow: none !important;
        padding: 0 !important;
      }
      .report-head { border-bottom: 1px solid #cbd5e1 !important; }
      .brand-mark { color: #0d9488 !important; }
      .kpi-tile, .chart-card {
        background: #f8fafc !important;
        border-color: #e2e8f0 !important;
        color: #0f172a !important;
        break-inside: avoid;
      }
      .kpi-label, .report-table th { color: #64748b !important; }
      .kpi-value, .chart-card h3, .report-table td { color: #0f172a !important; }
      .report-table th { background: #f8fafc !important; }
      .report-table th, .report-table td { border-bottom-color: #e2e8f0 !important; }
      .report-foot { border-top-color: #e2e8f0 !important; color: #64748b !important; }
      .chart-card canvas { height: 220px !important; }
      .chart-row { break-inside: avoid; }

      @page { size: A4; margin: 14mm 12mm; }
    }
  `],
})
export class ReportsPageComponent implements OnInit, AfterViewInit, OnDestroy {
  private http = inject(HttpClient);
  private api = inject(ApiService);

  type: ReportType = 'summary';
  groupBy: 'day' | 'week' | 'month' = 'day';
  fromDate = '';
  toDate = '';
  generatedAt = '';
  projects = signal<Project[]>([]);
  result = signal<ReportData | null>(null);
  error = signal<string | null>(null);

  @ViewChild('chartA') chartARef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartB') chartBRef?: ElementRef<HTMLCanvasElement>;

  private chartA?: Chart;
  private chartB?: Chart;

  // Narrowed accessors keep the template readable without manual casts.
  summary = computed(() => this.result() as SummaryReport);
  billing = computed(() => this.result() as BillingReport);
  activity = computed(() => this.result() as ActivityReport);
  detailed = computed(() => this.result() as DetailedReport);
  productivity = computed(() => this.result() as ProductivityReport);

  kpis = computed(() => {
    const r = this.result();
    if (!r) return [];
    if (r.type === 'summary') {
      const projects = r.by_project.length;
      return [
        { label: 'Total tracked', value: this.fmtHours(r.total_seconds) },
        { label: 'Projects', value: projects.toString() },
        {
          label: 'Top project',
          value: r.by_project[0]?.project ?? '—',
          sub: r.by_project[0] ? this.fmtHours(r.by_project[0].seconds) : '',
        },
      ];
    }
    if (r.type === 'billing') {
      const billable = r.by_project.reduce((a, x) => a + x.billable_seconds, 0);
      const currency = r.by_project[0]?.currency ?? 'USD';
      return [
        { label: 'Revenue', value: `${r.grand_total_amount.toFixed(2)} ${currency}` },
        { label: 'Billable hours', value: this.fmtHours(billable) },
        { label: 'Non-billable', value: this.fmtHours(r.non_billable_seconds) },
      ];
    }
    if (r.type === 'activity') {
      const total = r.rows.reduce((a, x) => a + x.seconds, 0);
      return [
        { label: 'Total tracked', value: this.fmtHours(total) },
        { label: 'Categories', value: new Set(r.rows.map((x) => x.category)).size.toString() },
        { label: 'Sessions', value: r.rows.reduce((a, x) => a + x.sessions, 0).toString() },
      ];
    }
    if (r.type === 'productivity') {
      const pomoTotal = r.pomodoro.reduce((a, p) => a + p.total, 0);
      const pomoCompleted = r.pomodoro.reduce((a, p) => a + p.completed, 0);
      const classifiedPct = r.active_seconds
        ? Math.round((r.classified_seconds / r.active_seconds) * 100)
        : 0;
      return [
        { label: 'Active', value: this.fmtHours(r.active_seconds) },
        { label: 'Classified', value: `${classifiedPct}%` },
        {
          label: 'Pomodoros',
          value: pomoTotal ? `${pomoCompleted} / ${pomoTotal}` : '—',
          sub: pomoTotal ? `${Math.round((pomoCompleted / pomoTotal) * 100)}% completed` : '',
        },
      ];
    }
    if (r.type === 'detailed') {
      const total = r.sessions.reduce((a, x) => a + x.duration_secs, 0);
      return [
        { label: 'Sessions', value: r.sessions.length.toString() },
        { label: 'Tracked', value: this.fmtHours(total) },
      ];
    }
    return [];
  });

  constructor() {
    // Re-render charts whenever the report data changes. afterNextRender
    // would be cleaner but we already have @ViewChild — schedule for after
    // Angular swaps the DOM under *ngSwitchCase.
    effect(() => {
      this.result();
      queueMicrotask(() => this.renderCharts());
    });
  }

  ngOnInit(): void {
    const today = new Date();
    const monthAgo = new Date(today.getTime() - 30 * 24 * 3600 * 1000);
    this.fromDate = monthAgo.toISOString().slice(0, 10);
    this.toDate = today.toISOString().slice(0, 10);
    this.api.projects().subscribe((p) => this.projects.set(p));
    this.run();
  }

  ngAfterViewInit(): void {
    // First paint after data lands during ngOnInit.
    queueMicrotask(() => this.renderCharts());
  }

  ngOnDestroy(): void {
    this.chartA?.destroy();
    this.chartB?.destroy();
  }

  // ─── data load ─────────────────────────────────────────────────────

  run(): void {
    if (!this.fromDate || !this.toDate) return;
    this.http
      .post<ReportData>('/api/reports/generate', {
        type: this.type,
        from: this.fromDate,
        to: this.toDate,
        group_by: this.groupBy,
      })
      .subscribe({
        next: (r) => {
          this.result.set(r);
          this.error.set(null);
          this.generatedAt = new Date().toLocaleString(undefined, {
            year: 'numeric', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit',
          });
        },
        error: (err) => this.error.set(err.error?.detail || err.message),
      });
  }

  print(): void {
    // Native print dialog → "Save as PDF" gives the user the highest-
    // fidelity export possible (the canvases rasterise perfectly). We
    // don't try to ship a custom PDF generator — the browser already has
    // one and it knows about page breaks, fonts and our @media print CSS.
    window.print();
  }

  download(format: ExportFormat): void {
    fetch('/api/reports/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: this.type,
        from: this.fromDate,
        to: this.toDate,
        group_by: this.groupBy,
        format,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `tickwise-${this.type}-${this.fromDate}-${this.toDate}.${format}`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch((err) => this.error.set(`Download failed: ${err.message}`));
  }

  // ─── chart rendering ───────────────────────────────────────────────

  private renderCharts(): void {
    this.chartA?.destroy();
    this.chartB?.destroy();
    this.chartA = undefined;
    this.chartB = undefined;

    const r = this.result();
    if (!r) return;
    const aEl = this.chartARef?.nativeElement;
    const bEl = this.chartBRef?.nativeElement;

    Chart.defaults.color = this.cssVar('--cl-text', '#e9f2f8');
    Chart.defaults.font.family = this.cssVar('--cl-font-body', 'sans-serif');
    Chart.defaults.borderColor = this.cssVar('--cl-stroke', 'rgba(157,197,220,.18)');

    if (r.type === 'summary' && aEl && bEl) {
      this.chartA = this.buildStackedBar(aEl, r);
      this.chartB = this.buildDoughnut(
        bEl,
        r.by_project.map((p) => p.project),
        r.by_project.map((p) => p.seconds / 3600),
      );
    } else if (r.type === 'billing' && aEl && bEl) {
      const labels = r.by_project.map((p) => p.project);
      const data = r.by_project.map((p) => p.amount);
      this.chartA = this.buildHorizontalBar(aEl, labels, data, 'Amount');
      const billable = r.by_project.reduce((a, x) => a + x.billable_seconds, 0) / 3600;
      const nonBillable = r.non_billable_seconds / 3600;
      this.chartB = this.buildDoughnut(bEl, ['Billable', 'Non-billable'], [billable, nonBillable]);
    } else if (r.type === 'activity' && aEl && bEl) {
      const byCategory = new Map<string, number>();
      const byProject = new Map<string, number>();
      for (const row of r.rows) {
        byCategory.set(row.category, (byCategory.get(row.category) ?? 0) + row.seconds);
        byProject.set(row.project, (byProject.get(row.project) ?? 0) + row.seconds);
      }
      this.chartA = this.buildDoughnut(
        aEl,
        [...byCategory.keys()],
        [...byCategory.values()].map((s) => s / 3600),
      );
      const topProjects = [...byProject.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
      this.chartB = this.buildHorizontalBar(
        bEl,
        topProjects.map(([p]) => p),
        topProjects.map(([, s]) => s / 3600),
        'Hours',
      );
    } else if (r.type === 'productivity' && aEl && bEl) {
      const labels = Array.from({ length: 24 }, (_, h) => h.toString().padStart(2, '0') + ':00');
      const data = r.active_by_hour.map((x) => x.seconds / 3600);
      this.chartA = this.buildBar(aEl, labels, data, 'Hours');
      if (r.pomodoro.length) {
        const pomoLabels = r.pomodoro.map((p) => p.type);
        const completed = r.pomodoro.map((p) => p.completed);
        const missed = r.pomodoro.map((p) => p.total - p.completed);
        this.chartB = new Chart(bEl, {
          type: 'bar',
          data: {
            labels: pomoLabels,
            datasets: [
              { label: 'Completed', data: completed, backgroundColor: PALETTE[4], stack: 'p' },
              { label: 'Missed', data: missed, backgroundColor: PALETTE[5], stack: 'p' },
            ],
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } },
            scales: { x: { stacked: true }, y: { stacked: true } },
          },
        });
      } else {
        this.chartB = this.buildDoughnut(bEl, ['No data'], [1]);
      }
    }
  }

  private buildBar(el: HTMLCanvasElement, labels: string[], data: number[], label: string): Chart {
    return new Chart(el, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label, data,
          backgroundColor: PALETTE_TRANSLUCENT[1],
          borderColor: PALETTE[1], borderWidth: 1,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } },
      },
    });
  }

  private buildHorizontalBar(el: HTMLCanvasElement, labels: string[], data: number[], label: string): Chart {
    return new Chart(el, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label, data,
          backgroundColor: labels.map((_, i) => PALETTE_TRANSLUCENT[i % PALETTE.length]),
          borderColor: labels.map((_, i) => PALETTE[i % PALETTE.length]),
          borderWidth: 1,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
      },
    });
  }

  private buildDoughnut(el: HTMLCanvasElement, labels: string[], data: number[]): Chart {
    return new Chart(el, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: labels.map((_, i) => PALETTE[i % PALETTE.length]),
          borderColor: this.cssVar('--cl-bg-2', '#0c1d2a'),
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        cutout: '62%',
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } },
      },
    });
  }

  private buildStackedBar(el: HTMLCanvasElement, r: SummaryReport): Chart {
    const buckets = [...new Set(r.series.map((s) => s.bucket))].sort();
    const projects = [...new Set(r.series.map((s) => s.project))];
    const datasets = projects.map((project, i) => ({
      label: project,
      data: buckets.map((bucket) => {
        const hit = r.series.find((s) => s.bucket === bucket && s.project === project);
        return hit ? hit.seconds / 3600 : 0;
      }),
      backgroundColor: PALETTE_TRANSLUCENT[i % PALETTE.length],
      borderColor: PALETTE[i % PALETTE.length],
      borderWidth: 1,
    }));
    return new Chart(el, {
      type: 'bar',
      data: { labels: buckets, datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } },
        scales: {
          x: { stacked: true },
          y: { stacked: true, beginAtZero: true, title: { display: true, text: 'Hours' } },
        },
      },
    });
  }

  // ─── utilities ─────────────────────────────────────────────────────

  titleFor(t: ReportType): string {
    return ({
      summary: 'Time Summary',
      billing: 'Billing Report',
      activity: 'Activity Breakdown',
      detailed: 'Detailed Log',
      productivity: 'Productivity Report',
    })[t];
  }

  fmtHours(seconds: number): string {
    const h = seconds / 3600;
    if (h >= 10) return `${h.toFixed(0)} h`;
    if (h >= 1) return `${h.toFixed(1)} h`;
    return `${Math.round(seconds / 60)} min`;
  }

  pctOfTotal(secs: number, total: number): string {
    if (!total) return '—';
    return `${((secs / total) * 100).toFixed(1)}%`;
  }

  formatDate(iso: string): string {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  }

  formatRange(from: string, to: string): string {
    return `${from} → ${to}`;
  }

  private cssVar(name: string, fallback: string): string {
    if (typeof document === 'undefined') return fallback;
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }
}
