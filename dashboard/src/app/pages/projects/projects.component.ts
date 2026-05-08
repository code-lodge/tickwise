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
    <header class="hero">
      <div class="hero-left">
        <div class="eyebrow">PROJECTS</div>
        <h1>{{ projects().length }} {{ projects().length === 1 ? 'project' : 'projects' }}</h1>
        <p class="hero-sub">
          Each project's keywords are matched against window titles, browser
          URLs and on-screen text. Edit a row's keywords to tag everything
          related to that project automatically.
        </p>
      </div>
      <div class="hero-right">
        <button class="outline" (click)="reclassify()" [disabled]="reclassifying()">
          {{ reclassifying() ? 'Re-classifying…' : 'Re-classify history' }}
        </button>
        <p *ngIf="reclassifyResult() as r" class="muted reclassify-summary">
          Activities: {{ r.matched }} matched · Sessions: {{ (r.sessions_matched ?? 0) }} matched
        </p>
      </div>
    </header>

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
      <p class="muted" style="margin:.5rem 0 .25rem 0">
        Match keywords (one per line). Spacing, punctuation and case are
        ignored — "Sceneryenzo" matches "scenery en zo" and
        "scenery-enzo.com". Whichever project has the strongest match wins.
      </p>
      <textarea
        [(ngModel)]="draft.match_keywords"
        rows="3"
        placeholder="Defaults to the project name if left blank"
        style="width:100%; font-family: var(--mono, monospace)"
      ></textarea>
      <p *ngIf="error()" class="error">{{ error() }}</p>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Client</th>
            <th>Rate</th>
            <th>Match keywords</th>
            <th>Tracked</th>
            <th>Active</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <ng-container *ngFor="let p of projects()">
          <tr [class.archived]="!p.is_active">
            <td>
              <span class="badge" [style.background]="p.color">&nbsp;</span>
              <input [(ngModel)]="p.name" (change)="save(p)" />
              <span *ngIf="!p.is_active" class="muted" style="margin-left:.4rem">(archived)</span>
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
            <td>
              <textarea
                [(ngModel)]="p.match_keywords"
                (change)="save(p)"
                rows="2"
                placeholder="one keyword per line"
                style="width: 14rem; font-family: var(--mono, monospace)"
              ></textarea>
            </td>
            <td>{{ formatHours(p.total_seconds) }}</td>
            <td>
              <input type="checkbox" [(ngModel)]="p.is_active" (change)="save(p)" />
            </td>
            <td style="white-space:nowrap">
              <button *ngIf="p.is_active" (click)="archive(p)" title="Hide from active list, keep history">
                Archive
              </button>
              <button class="danger" (click)="remove(p)" title="Permanently delete — cannot be undone">
                Delete
              </button>
            </td>
          </tr>
          </ng-container>
          <tr *ngIf="!projects().length">
            <td colspan="7" class="muted">No projects yet — create one above.</td>
          </tr>
        </tbody>
      </table>
    </div>
  `,
  styles: [
    `
      :host { display: block; }
      .hero {
        display: flex; gap: 1.5rem; align-items: flex-start;
        justify-content: space-between; flex-wrap: wrap;
        background: linear-gradient(120deg, rgba(45, 212, 191, 0.10), rgba(56, 189, 248, 0.06));
        border: 1px solid var(--cl-stroke);
        border-radius: var(--cl-radius);
        padding: 1.6rem 1.8rem;
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
        font-family: var(--cl-font-display);
        font-size: clamp(1.7rem, 3.5vw, 2.2rem);
        margin: 0 0 0.5rem; letter-spacing: -0.02em;
      }
      .hero-sub {
        color: var(--cl-muted); margin: 0;
        font-size: 0.95rem; max-width: 540px;
      }
      .hero-right { display: flex; flex-direction: column; align-items: flex-end; gap: 0.5rem; }
      button.outline {
        background: transparent;
        border: 1px solid var(--cl-stroke-strong);
        color: var(--cl-text);
      }
      button.outline:hover { background: rgba(157, 197, 220, 0.06); }
      .reclassify-summary { font-size: 0.78rem; margin: 0; }
      tr.archived td { opacity: 0.55; }
    `,
  ],
})
export class ProjectsPageComponent implements OnInit {
  private api = inject(ApiService);
  projects = signal<Project[]>([]);
  clients = signal<Client[]>([]);
  draft: Partial<Project> = { color: '#3B82F6', currency: 'USD', is_active: true, match_keywords: '' };
  error = signal<string | null>(null);
  reclassifying = signal(false);
  reclassifyResult = signal<{ scanned: number; matched: number; unchanged: number; sessions_scanned?: number; sessions_matched?: number } | null>(null);

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
        this.draft = { color: '#3B82F6', currency: 'USD', is_active: true, match_keywords: '' };
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
    if (!confirm(`Archive ${p.name}? It will be hidden from the active list but its time history is kept.`)) return;
    this.api.deleteProject(p.id).subscribe(() => this.reload());
  }

  remove(p: Project): void {
    const msg = `Permanently delete ${p.name}?\n\n` +
      `This cannot be undone. Past sessions and activities will be detached and shown as "Unassigned".\n\n` +
      `Type the project name to confirm:`;
    const answer = prompt(msg);
    if (answer !== p.name) {
      if (answer !== null) alert('Name did not match — project not deleted.');
      return;
    }
    this.api.deleteProject(p.id, true).subscribe(() => this.reload());
  }

  formatHours(secs: number): string {
    const h = secs / 3600;
    return `${h.toFixed(1)} h`;
  }

  reclassify(): void {
    this.reclassifying.set(true);
    this.reclassifyResult.set(null);
    this.api.reclassifyAll().subscribe({
      next: (r) => {
        this.reclassifyResult.set(r);
        this.reclassifying.set(false);
        this.reload();
      },
      error: (err) => {
        this.error.set(err.error?.detail || err.message);
        this.reclassifying.set(false);
      },
    });
  }
}
