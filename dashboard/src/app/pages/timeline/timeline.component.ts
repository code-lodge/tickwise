import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import type { Project, Session } from '../../models';

@Component({
  selector: 'app-timeline',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h1>Timeline</h1>

    <div class="row" style="margin-bottom: 1rem">
      <label>From <input type="date" [(ngModel)]="fromDate" (change)="reload()" /></label>
      <label>To <input type="date" [(ngModel)]="toDate" (change)="reload()" /></label>
      <button class="ghost" (click)="reload()">Refresh</button>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Started</th>
            <th>Duration</th>
            <th>Project</th>
            <th>Description</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let s of sessions()">
            <td>{{ s.started_at | date: 'short' }}</td>
            <td>{{ formatDuration(s.duration_secs) }}</td>
            <td>
              <select [(ngModel)]="s.project_id" (change)="updateProject(s)">
                <option [ngValue]="null">— Unclassified —</option>
                <option *ngFor="let p of projects()" [ngValue]="p.id">{{ p.name }}</option>
              </select>
            </td>
            <td>
              <input
                style="width:100%"
                [(ngModel)]="s.description"
                (change)="updateDescription(s)"
                placeholder="Add notes…"
              />
            </td>
            <td class="row">
              <button class="ghost" (click)="prepareSplit(s)">Split</button>
              <button class="danger" (click)="delete(s.id)">Delete</button>
            </td>
          </tr>
          <tr *ngIf="!sessions().length">
            <td colspan="5" class="muted">No sessions in this range.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div *ngIf="splitTarget()" class="card" style="margin-top:1rem">
      <h3>Split session #{{ splitTarget()!.id }}</h3>
      <div class="row">
        <label>
          At
          <input type="datetime-local" [(ngModel)]="splitAt" />
        </label>
        <button (click)="performSplit()">Confirm split</button>
        <button class="ghost" (click)="splitTarget.set(null)">Cancel</button>
      </div>
    </div>

    <p *ngIf="error()" class="error">{{ error() }}</p>
  `,
})
export class TimelinePageComponent implements OnInit {
  private api = inject(ApiService);
  sessions = signal<Session[]>([]);
  projects = signal<Project[]>([]);
  splitTarget = signal<Session | null>(null);
  splitAt = '';
  fromDate = '';
  toDate = '';
  error = signal<string | null>(null);

  ngOnInit(): void {
    const today = new Date();
    const weekAgo = new Date(today.getTime() - 7 * 24 * 3600 * 1000);
    this.fromDate = weekAgo.toISOString().slice(0, 10);
    this.toDate = today.toISOString().slice(0, 10);
    this.reload();
    this.api.projects().subscribe((p) => this.projects.set(p));
  }

  reload(): void {
    this.api
      .sessions({
        from: this.fromDate ? `${this.fromDate}T00:00:00` : undefined,
        to: this.toDate ? `${this.toDate}T23:59:59` : undefined,
      })
      .subscribe({
        next: (s) => {
          this.sessions.set(s);
          this.error.set(null);
        },
        error: (err) => this.error.set(`Failed to load sessions: ${err.message}`),
      });
  }

  updateProject(s: Session): void {
    this.api.updateSession(s.id, { project_id: s.project_id }).subscribe();
  }

  updateDescription(s: Session): void {
    this.api.updateSession(s.id, { description: s.description }).subscribe();
  }

  delete(id: number): void {
    if (!confirm('Delete this session?')) return;
    this.api.deleteSession(id).subscribe(() => this.reload());
  }

  prepareSplit(s: Session): void {
    this.splitTarget.set(s);
    this.splitAt = s.started_at.slice(0, 16);
  }

  performSplit(): void {
    const target = this.splitTarget();
    if (!target) return;
    this.api.splitSession(target.id, new Date(this.splitAt).toISOString()).subscribe({
      next: () => {
        this.splitTarget.set(null);
        this.reload();
      },
      error: (err) => this.error.set(`Split failed: ${err.error?.detail || err.message}`),
    });
  }

  formatDuration(secs: number | null): string {
    if (!secs) return '—';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  }
}
