import { Component, HostListener, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ApiService } from './services/api.service';

interface OnboardingState {
  needs_profile: boolean;
  needs_first_project: boolean;
  needs_privacy_choice: boolean;
  is_first_run: boolean;
  complete: boolean;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div *ngIf="onboarding() && !onboarding()!.complete" class="first-run-banner">
      <span>
        <strong>Finish setting up Tickwise.</strong>
        <span *ngIf="onboarding()!.needs_profile"> fill in your business profile,</span>
        <span *ngIf="onboarding()!.needs_first_project"> create a first project</span>
        — pick up where you left off in
        <a routerLink="/settings">Settings</a>.
      </span>
      <button class="ghost" (click)="dismissBanner()">Dismiss</button>
    </div>

    <header class="topbar">
      <div class="brand">
        <span class="dot" [class.tracking]="status()?.tracking"></span>
        <strong>Tickwise</strong>
        <span class="muted">v{{ status()?.version || '–' }}</span>
      </div>
      <nav class="nav">
        <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">Live</a>
        <a routerLink="/timeline" routerLinkActive="active">Timeline</a>
        <a routerLink="/projects" routerLinkActive="active">Projects</a>
        <a routerLink="/calendar" routerLinkActive="active">Calendar</a>
        <a routerLink="/reports" routerLinkActive="active">Reports</a>
        <a routerLink="/clients" routerLinkActive="active">Clients</a>
        <a routerLink="/invoices" routerLinkActive="active">Invoices</a>
        <a routerLink="/pomodoro" routerLinkActive="active">Pomodoro</a>
        <a routerLink="/mobile" routerLinkActive="active">Mobile</a>
        <a routerLink="/privacy" routerLinkActive="active">Privacy</a>
        <a routerLink="/settings" routerLinkActive="active">Settings</a>
      </nav>
      <button class="ghost" (click)="toggleTheme()" title="Toggle theme">
        {{ theme() === 'dark' ? '☀' : '☾' }}
      </button>
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
      .brand { display: flex; gap: 0.5rem; align-items: center; }
      .dot { width: 0.6rem; height: 0.6rem; border-radius: 50%; background: var(--color-muted); }
      .dot.tracking { background: var(--color-success); }
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
      .page { max-width: 1200px; margin: 1.5rem auto; padding: 0 1.25rem; }
    `,
  ],
})
export class AppComponent {
  private api = inject(ApiService);
  private http = inject(HttpClient);
  private router = inject(Router);

  status = signal<{ tracking: boolean; version: string } | null>(null);
  onboarding = signal<OnboardingState | null>(null);
  theme = signal<'light' | 'dark' | null>(localStorage.getItem('tickwise.theme') as 'light' | 'dark' | null);

  constructor() {
    this.applyTheme();
    this.refreshStatus();
    this.refreshOnboarding();
    setInterval(() => this.refreshStatus(), 5000);
  }

  private refreshStatus(): void {
    this.api.status().subscribe({
      next: (s) => this.status.set({ tracking: s.tracking, version: s.version }),
      error: () => this.status.set(null),
    });
  }

  private refreshOnboarding(): void {
    if (sessionStorage.getItem('tickwise.banner.dismissed') === '1') return;
    this.http.get<OnboardingState>('/api/onboarding/state').subscribe({
      next: (o) => this.onboarding.set(o),
      error: () => this.onboarding.set(null),
    });
  }

  dismissBanner(): void {
    sessionStorage.setItem('tickwise.banner.dismissed', '1');
    this.onboarding.set(null);
  }

  toggleTheme(): void {
    const next = this.theme() === 'dark' ? 'light' : 'dark';
    this.theme.set(next);
    localStorage.setItem('tickwise.theme', next);
    this.applyTheme();
  }

  private applyTheme(): void {
    const t = this.theme();
    if (t) document.body.dataset['theme'] = t;
    else delete document.body.dataset['theme'];
  }

  // Keyboard shortcuts: Ctrl/Cmd+P → pomodoro, Ctrl/Cmd+, → settings.
  @HostListener('window:keydown', ['$event'])
  onKey(event: KeyboardEvent): void {
    if (!(event.ctrlKey || event.metaKey)) return;
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
    if (event.key.toLowerCase() === 'p') {
      event.preventDefault();
      this.router.navigateByUrl('/pomodoro');
    } else if (event.key === ',') {
      event.preventDefault();
      this.router.navigateByUrl('/settings');
    }
  }
}
