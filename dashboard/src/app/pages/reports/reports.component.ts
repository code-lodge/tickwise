import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ApiService } from '../../services/api.service';
import type { Project } from '../../models';

type ReportType = 'summary' | 'billing' | 'activity' | 'detailed' | 'productivity';
type ExportFormat = 'json' | 'csv' | 'pdf' | 'ics';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h1>Reports</h1>

    <div class="card stack">
      <div class="row" style="flex-wrap: wrap">
        <label>
          Type
          <select [(ngModel)]="type">
            <option value="summary">Time summary</option>
            <option value="billing">Billing</option>
            <option value="activity">Activity</option>
            <option value="detailed">Detailed log</option>
            <option value="productivity">Productivity</option>
          </select>
        </label>
        <label>
          From <input type="date" [(ngModel)]="fromDate" />
        </label>
        <label>
          To <input type="date" [(ngModel)]="toDate" />
        </label>
        <label *ngIf="type === 'summary'">
          Group by
          <select [(ngModel)]="groupBy">
            <option value="day">Day</option>
            <option value="week">Week</option>
            <option value="month">Month</option>
          </select>
        </label>
      </div>

      <div class="row">
        <button (click)="run()">Generate</button>
        <button class="ghost" (click)="download('csv')">CSV</button>
        <button class="ghost" (click)="download('pdf')">PDF</button>
        <button class="ghost" (click)="download('json')">JSON</button>
        <button class="ghost" *ngIf="type === 'detailed'" (click)="download('ics')">ICS</button>
      </div>

      <p *ngIf="error()" class="error">{{ error() }}</p>
    </div>

    <pre
      *ngIf="result()"
      style="background:#f1f5f9; padding:1rem; border-radius:0.5rem; margin-top:1rem; max-height: 60vh; overflow:auto"
    >{{ result() | json }}</pre>
  `,
})
export class ReportsPageComponent implements OnInit {
  private http = inject(HttpClient);
  private api = inject(ApiService);

  type: ReportType = 'summary';
  groupBy: 'day' | 'week' | 'month' = 'day';
  fromDate = '';
  toDate = '';
  projects = signal<Project[]>([]);
  result = signal<unknown>(null);
  error = signal<string | null>(null);

  ngOnInit(): void {
    const today = new Date();
    const monthAgo = new Date(today.getTime() - 30 * 24 * 3600 * 1000);
    this.fromDate = monthAgo.toISOString().slice(0, 10);
    this.toDate = today.toISOString().slice(0, 10);
    this.api.projects().subscribe((p) => this.projects.set(p));
  }

  run(): void {
    this.http
      .post('/api/reports/generate', {
        type: this.type,
        from: this.fromDate,
        to: this.toDate,
        group_by: this.groupBy,
      })
      .subscribe({
        next: (r) => {
          this.result.set(r);
          this.error.set(null);
        },
        error: (err) => this.error.set(err.error?.detail || err.message),
      });
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
        a.download = `chronolens-${this.type}-${this.fromDate}-${this.toDate}.${format}`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch((err) => this.error.set(`Download failed: ${err.message}`));
  }
}
