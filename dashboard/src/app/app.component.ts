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
        padding: 0.85rem 1.5rem;
        border-bottom: 1px solid var(--cl-stroke);
        background: rgba(8, 19, 29, 0.82);
        backdrop-filter: saturate(140%) blur(14px);
        position: sticky;
        top: 0;
        z-index: 10;
      }
      .brand {
        display: flex; gap: 0.6rem; align-items: center;
        font-family: var(--cl-font-display);
        font-weight: 700; letter-spacing: -0.01em;
      }
      .brand strong { font-size: 1.05rem; color: var(--cl-text); }
      .brand .muted { font-size: 0.78rem; }
      .dot {
        width: 0.7rem; height: 0.7rem; border-radius: 50%;
        background: var(--cl-muted);
        transition: background 0.2s var(--cl-ease), box-shadow 0.2s var(--cl-ease);
      }
      .dot.tracking {
        background: var(--cl-good);
        box-shadow: 0 0 12px var(--cl-good);
      }
      .nav { display: flex; flex-wrap: wrap; gap: 0.15rem; }
      .nav a {
        padding: 0.4rem 0.75rem;
        border-radius: 6px;
        color: var(--cl-muted);
        font-size: 0.88rem;
        text-decoration: none;
        transition: color 0.12s var(--cl-ease), background 0.12s var(--cl-ease);
      }
      .nav a:hover { color: var(--cl-text); background: rgba(157, 197, 220, 0.06); }
      .nav a.active {
        color: var(--cl-accent);
        background: rgba(45, 212, 191, 0.12);
      }
      .page { max-width: 1200px; margin: 1.75rem auto 3rem; padding: 0 1.5rem; }
    `,
  ],
})
export class AppComponent {
  private api = inject(ApiService);
  private http = inject(HttpClient);
  private router = inject(Router);

  status = signal<{ tracking: boolean; version: string } | null>(null);
  onboarding = signal<OnboardingState | null>(null);

  constructor() {
    // Clean up the legacy theme attribute / preference for users who
    // toggled "light" before the toggle was removed — otherwise their
    // body still carries data-theme="light" forever.
    delete document.body.dataset['theme'];
    localStorage.removeItem('tickwise.theme');

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
