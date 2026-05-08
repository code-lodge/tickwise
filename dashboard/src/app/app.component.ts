import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ApiService } from './services/api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header class="topbar">
      <div class="brand">
        <span class="dot" [class.tracking]="status()?.tracking"></span>
        <strong>ChronoLens</strong>
        <span class="muted">v{{ status()?.version || '–' }}</span>
      </div>
      <nav class="nav">
        <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">Live</a>
        <a routerLink="/timeline" routerLinkActive="active">Timeline</a>
        <a routerLink="/projects" routerLinkActive="active">Projects</a>
        <a routerLink="/privacy" routerLinkActive="active">Privacy &amp; LLM</a>
        <a routerLink="/settings" routerLinkActive="active">Settings</a>
      </nav>
    </header>

    <main class="page">
      <router-outlet />
    </main>
  `,
  styles: [
    `
      .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1.25rem;
        border-bottom: 1px solid var(--color-border);
        background: var(--color-surface);
        position: sticky;
        top: 0;
        z-index: 10;
      }
      .brand {
        display: flex;
        gap: 0.5rem;
        align-items: center;
      }
      .dot {
        width: 0.6rem;
        height: 0.6rem;
        border-radius: 50%;
        background: var(--color-muted);
      }
      .dot.tracking {
        background: var(--color-success);
      }
      .nav a {
        margin: 0 0.5rem;
        padding: 0.4rem 0.6rem;
        border-radius: 0.375rem;
        color: var(--color-muted);
      }
      .nav a.active {
        color: var(--color-text);
        background: rgba(59, 130, 246, 0.08);
      }
      .page {
        max-width: 1200px;
        margin: 1.5rem auto;
        padding: 0 1.25rem;
      }
    `,
  ],
})
export class AppComponent {
  private api = inject(ApiService);
  status = signal<{ tracking: boolean; version: string } | null>(null);

  constructor() {
    this.api.status().subscribe({
      next: (s) => this.status.set({ tracking: s.tracking, version: s.version }),
      error: () => this.status.set(null),
    });
    setInterval(() => {
      this.api.status().subscribe((s) =>
        this.status.set({ tracking: s.tracking, version: s.version })
      );
    }, 5000);
  }
}
