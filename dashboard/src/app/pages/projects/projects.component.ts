import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import type { Client, Project } from '../../models';

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h1>Projects</h1>

    <div class="card" style="margin-bottom:1rem">
      <h3>New project</h3>
      <div class="row">
        <input [(ngModel)]="draft.name" placeholder="Project name" />
        <input [(ngModel)]="draft.color" type="color" style="width: 3rem" />
        <select [(ngModel)]="draft.client_id">
          <option [ngValue]="null">— No client —</option>
          <option *ngFor="let c of clients()" [ngValue]="c.id">{{ c.name }}</option>
        </select>
        <input
          [(ngModel)]="draft.hourly_rate"
          type="number"
          min="0"
          step="0.5"
          placeholder="Rate"
          style="width: 6rem"
        />
        <input [(ngModel)]="draft.currency" placeholder="USD" style="width: 4rem" />
        <button (click)="create()" [disabled]="!draft.name">Create</button>
      </div>
      <p *ngIf="error()" class="error">{{ error() }}</p>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Client</th>
            <th>Rate</th>
            <th>Tracked</th>
            <th>Active</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let p of projects()">
            <td>
              <span class="badge" [style.background]="p.color">&nbsp;</span>
              <input [(ngModel)]="p.name" (change)="save(p)" />
            </td>
            <td>
              <select [(ngModel)]="p.client_id" (change)="save(p)">
                <option [ngValue]="null">—</option>
                <option *ngFor="let c of clients()" [ngValue]="c.id">{{ c.name }}</option>
              </select>
            </td>
            <td>
              <input
                type="number"
                [(ngModel)]="p.hourly_rate"
                (change)="save(p)"
                style="width: 6rem"
              />
              <span class="muted">{{ p.currency }}</span>
            </td>
            <td>{{ formatHours(p.total_seconds) }}</td>
            <td>
              <input type="checkbox" [(ngModel)]="p.is_active" (change)="save(p)" />
            </td>
            <td>
              <button class="danger" (click)="archive(p)">Archive</button>
            </td>
          </tr>
          <tr *ngIf="!projects().length">
            <td colspan="6" class="muted">No projects yet — create one above.</td>
          </tr>
        </tbody>
      </table>
    </div>
  `,
})
export class ProjectsPageComponent implements OnInit {
  private api = inject(ApiService);
  projects = signal<Project[]>([]);
  clients = signal<Client[]>([]);
  draft: Partial<Project> = { color: '#3B82F6', currency: 'USD', is_active: true };
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.reload();
    this.api.clients().subscribe((c) => this.clients.set(c));
  }

  reload(): void {
    this.api.projects().subscribe((p) => this.projects.set(p));
  }

  create(): void {
    this.api.createProject(this.draft).subscribe({
      next: () => {
        this.draft = { color: '#3B82F6', currency: 'USD', is_active: true };
        this.error.set(null);
        this.reload();
      },
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }

  save(p: Project): void {
    this.api.updateProject(p.id, p).subscribe();
  }

  archive(p: Project): void {
    if (!confirm(`Archive ${p.name}? It will be marked inactive.`)) return;
    this.api.deleteProject(p.id).subscribe(() => this.reload());
  }

  formatHours(secs: number): string {
    const h = secs / 3600;
    return `${h.toFixed(1)} h`;
  }
}
