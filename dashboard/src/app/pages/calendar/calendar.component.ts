import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

interface FeedConfig {
  id: number;
  token: string;
  name: string;
  include_descriptions: boolean;
  project_filter: string | null;
  is_active: boolean;
}

interface Provider {
  id: number;
  name: string;
  type: 'caldav' | 'google' | 'ical';
  url: string | null;
  username: string | null;
  is_active: boolean;
  last_synced_at: string | null;
}

interface CloudflareState {
  has_token: boolean;
  tunnel_id: string | null;
  tunnel_name: string | null;
  hostname: string | null;
  is_active: boolean;
  binary_installed: boolean;
  binary_available: boolean;
  tunnel_running: boolean;
  last_log_line: string | null;
  last_error: string | null;
}

@Component({
  selector: 'app-calendar',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h1>Calendar &amp; tunnel</h1>

    <section class="card stack">
      <h3>ICS feeds</h3>
      <p class="muted">
        Each feed exposes a public URL that calendar clients (Tuta, Google,
        Apple) can subscribe to. Combine with the Cloudflare tunnel below to
        publish over a stable domain.
      </p>
      <div class="row">
        <input [(ngModel)]="newFeed.name" placeholder="Feed name" />
        <label class="row">
          <input type="checkbox" [(ngModel)]="newFeed.include_descriptions" />
          Include descriptions
        </label>
        <input
          [(ngModel)]="newFeed.project_filter"
          placeholder="Project IDs (e.g. 1,2)"
        />
        <button (click)="createFeed()" [disabled]="!newFeed.name">Create feed</button>
      </div>
      <table>
        <thead>
          <tr><th>Name</th><th>URL</th><th></th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let f of feeds()">
            <td>{{ f.name }}</td>
            <td><code style="font-size:0.75rem">/api/calendar/feed/{{ f.token }}.ics</code></td>
            <td><button class="danger" (click)="deleteFeed(f.id)">Delete</button></td>
          </tr>
          <tr *ngIf="!feeds().length"><td colspan="3" class="muted">No feeds yet.</td></tr>
        </tbody>
      </table>
      <a class="ghost" [href]="'/api/calendar/export.ics'">Download one-shot ICS</a>
    </section>

    <section class="card stack" style="margin-top:1rem">
      <h3>Calendar providers (push sync)</h3>
      <div class="row">
        <input [(ngModel)]="newProv.name" placeholder="Display name" />
        <select [(ngModel)]="newProv.type">
          <option value="caldav">CalDAV</option>
          <option value="google">Google</option>
        </select>
        <input [(ngModel)]="newProv.url" placeholder="URL" />
        <input [(ngModel)]="newProv.username" placeholder="Username (optional)" />
        <button (click)="createProvider()" [disabled]="!newProv.name">Add</button>
      </div>
      <table>
        <thead>
          <tr><th>Name</th><th>Type</th><th>URL</th><th>Last synced</th><th></th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let p of providers()">
            <td>{{ p.name }}</td>
            <td>{{ p.type }}</td>
            <td>{{ p.url }}</td>
            <td>{{ p.last_synced_at || '—' }}</td>
            <td><button class="danger" (click)="deleteProvider(p.id)">Delete</button></td>
          </tr>
          <tr *ngIf="!providers().length"><td colspan="5" class="muted">No providers yet.</td></tr>
        </tbody>
      </table>
      <button (click)="syncNow()">Sync now</button>
      <pre *ngIf="syncReport()" style="background:#f1f5f9; padding:0.5rem; border-radius:0.375rem">{{ syncReport() | json }}</pre>
    </section>

    <section class="card stack" style="margin-top:1rem">
      <h3>Cloudflare tunnel</h3>
      <p *ngIf="cf() as s" class="muted">
        Status:
        <strong [class.error]="s.last_error">
          {{ s.is_active ? 'configured' : 'not configured' }}
          · binary {{ s.binary_installed ? 'installed' : 'missing' }}
          · process {{ s.tunnel_running ? 'running' : 'stopped' }}
        </strong>
        <span *ngIf="s.hostname">— hostname: {{ s.hostname }}</span>
        <span *ngIf="s.last_error" class="error"> — {{ s.last_error }}</span>
      </p>

      <div class="row" *ngIf="!cf()?.has_token">
        <input [(ngModel)]="apiToken" placeholder="Cloudflare API token" />
        <button (click)="saveToken()">Save token</button>
      </div>

      <div *ngIf="cf()?.has_token && !cf()?.is_active" class="stack">
        <div class="row">
          <input [(ngModel)]="activate.account_id" placeholder="Account ID" />
          <input [(ngModel)]="activate.zone_id" placeholder="Zone ID" />
          <input [(ngModel)]="activate.hostname" placeholder="time.example.com" />
          <button (click)="activateTunnel()">Activate</button>
        </div>
      </div>

      <div *ngIf="cf()?.is_active" class="row">
        <button *ngIf="!cf()?.binary_installed" (click)="downloadBinary()">Download cloudflared</button>
        <button *ngIf="!cf()?.tunnel_running" (click)="startTunnel()">Start tunnel</button>
        <button *ngIf="cf()?.tunnel_running" class="ghost" (click)="stopTunnel()">Stop tunnel</button>
        <button class="danger" (click)="deactivateTunnel()">Deactivate</button>
      </div>
    </section>

    <p *ngIf="error()" class="error">{{ error() }}</p>
  `,
})
export class CalendarPageComponent implements OnInit {
  private http = inject(HttpClient);
  feeds = signal<FeedConfig[]>([]);
  providers = signal<Provider[]>([]);
  cf = signal<CloudflareState | null>(null);
  syncReport = signal<unknown>(null);
  error = signal<string | null>(null);

  newFeed = { name: '', include_descriptions: false, project_filter: null as string | null };
  newProv = { name: '', type: 'caldav', url: '', username: '' };
  apiToken = '';
  activate = { account_id: '', zone_id: '', hostname: '' };

  ngOnInit(): void {
    this.reloadAll();
  }

  reloadAll(): void {
    this.http.get<FeedConfig[]>('/api/calendar/feeds').subscribe((f) => this.feeds.set(f));
    this.http
      .get<Provider[]>('/api/calendar/providers')
      .subscribe((p) => this.providers.set(p));
    this.http.get<CloudflareState>('/api/cloudflare/state').subscribe((s) => this.cf.set(s));
  }

  createFeed(): void {
    this.http.post('/api/calendar/feeds', this.newFeed).subscribe({
      next: () => {
        this.newFeed = { name: '', include_descriptions: false, project_filter: null };
        this.reloadAll();
      },
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }
  deleteFeed(id: number): void {
    this.http.delete(`/api/calendar/feeds/${id}`).subscribe(() => this.reloadAll());
  }

  createProvider(): void {
    this.http.post('/api/calendar/providers', this.newProv).subscribe({
      next: () => {
        this.newProv = { name: '', type: 'caldav', url: '', username: '' };
        this.reloadAll();
      },
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }
  deleteProvider(id: number): void {
    this.http
      .delete(`/api/calendar/providers/${id}`)
      .subscribe(() => this.reloadAll());
  }
  syncNow(): void {
    this.http.post('/api/calendar/sync', {}).subscribe({
      next: (r) => this.syncReport.set(r),
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }

  saveToken(): void {
    this.http.post('/api/cloudflare/token', { api_token: this.apiToken }).subscribe({
      next: () => {
        this.apiToken = '';
        this.reloadAll();
      },
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }
  activateTunnel(): void {
    this.http.post('/api/cloudflare/activate', this.activate).subscribe({
      next: () => this.reloadAll(),
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }
  deactivateTunnel(): void {
    this.http
      .post('/api/cloudflare/deactivate', {})
      .subscribe(() => this.reloadAll());
  }
  downloadBinary(): void {
    this.http
      .post('/api/cloudflare/binary/download', {})
      .subscribe(() => this.reloadAll());
  }
  startTunnel(): void {
    this.http.post('/api/cloudflare/start', {}).subscribe({
      next: () => this.reloadAll(),
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }
  stopTunnel(): void {
    this.http.post('/api/cloudflare/stop', {}).subscribe(() => this.reloadAll());
  }
}
