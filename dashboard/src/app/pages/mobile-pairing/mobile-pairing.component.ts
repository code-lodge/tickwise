import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

interface PairResponse {
  token_id: number;
  token: string;
  pairing_url: string;
  qr_svg: string;
}

interface PairedDevice {
  id: number;
  device_name: string | null;
  created_at: string;
  last_used: string | null;
  expires_at: string | null;
}

@Component({
  selector: 'app-mobile-pairing',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h1>Pair Mobile Device</h1>

    <div class="card stack">
      <div class="row" style="flex-wrap: wrap">
        <label>
          Device name (optional)
          <input [(ngModel)]="deviceName" placeholder="My iPhone" />
        </label>
        <label>
          Token expires after (days)
          <input type="number" [(ngModel)]="ttlDays" min="1" max="3650" placeholder="never" />
        </label>
      </div>
      <div class="row">
        <button (click)="generate()">Generate pairing QR</button>
        <span class="muted" *ngIf="!cloudflareReady()">
          Cloudflare Tunnel not active — QR will use local IP and only works on the same network.
        </span>
      </div>
      <p *ngIf="error()" class="error">{{ error() }}</p>
    </div>

    <div class="card" *ngIf="pair() as p" style="margin-top: 1rem">
      <h2>Scan this QR on your phone</h2>
      <div class="qr-host" [innerHTML]="qrHtml()"></div>
      <p class="muted" style="word-break: break-all">{{ p.pairing_url }}</p>
      <p class="muted">
        Or open
        <code>{{ pwaPath(p.pairing_url) }}</code>
        and paste the token manually:
      </p>
      <pre style="background:#f1f5f9; padding: 0.6rem; border-radius: 0.4rem; overflow:auto">{{ p.token }}</pre>
      <p class="muted">
        The token is shown once — copy it now. Revoke it anytime from the list below.
      </p>
    </div>

    <div class="card" style="margin-top: 1rem">
      <h2>Paired devices</h2>
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr>
            <th>Name</th><th>Created</th><th>Last used</th><th>Expires</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let d of devices()" style="border-top: 1px solid var(--color-border)">
            <td>{{ d.device_name || '—' }}</td>
            <td>{{ d.created_at }}</td>
            <td>{{ d.last_used || 'never' }}</td>
            <td>{{ d.expires_at || 'never' }}</td>
            <td style="text-align: right">
              <button class="ghost" (click)="revoke(d)">Revoke</button>
            </td>
          </tr>
          <tr *ngIf="!devices().length">
            <td colspan="5" class="muted">No paired devices yet.</td>
          </tr>
        </tbody>
      </table>
    </div>
  `,
  styles: [
    `
      .qr-host {
        max-width: 320px;
        margin: 1rem auto;
        background: white;
        padding: 0.75rem;
        border-radius: 0.4rem;
      }
      .qr-host ::ng-deep svg { width: 100%; height: auto; display: block; }
    `,
  ],
})
export class MobilePairingPageComponent implements OnInit {
  private http = inject(HttpClient);
  private sanitizer = inject(DomSanitizer);

  deviceName = '';
  ttlDays: number | null = null;

  pair = signal<PairResponse | null>(null);
  devices = signal<PairedDevice[]>([]);
  error = signal<string | null>(null);
  cloudflareReady = signal<boolean>(false);

  ngOnInit(): void {
    this.refreshDevices();
    this.http
      .get<{ is_active: boolean }>('/api/cloudflare/state')
      .subscribe({
        next: (s) => this.cloudflareReady.set(!!s.is_active),
        error: () => this.cloudflareReady.set(false),
      });
  }

  refreshDevices(): void {
    this.http
      .get<PairedDevice[]>('/api/pairing/tokens')
      .subscribe((rows) => this.devices.set(rows));
  }

  qrHtml(): SafeHtml | null {
    const p = this.pair();
    if (!p) return null;
    return this.sanitizer.bypassSecurityTrustHtml(p.qr_svg);
  }

  pwaPath(pairingUrl: string): string {
    try {
      const u = new URL(pairingUrl);
      return `${u.origin}/m/`;
    } catch {
      return '/m/';
    }
  }

  generate(): void {
    const payload: Record<string, unknown> = {};
    if (this.deviceName) payload['device_name'] = this.deviceName;
    if (this.ttlDays) payload['ttl_days'] = this.ttlDays;
    this.http.post<PairResponse>('/api/pairing/start', payload).subscribe({
      next: (r) => {
        this.pair.set(r);
        this.error.set(null);
        this.refreshDevices();
      },
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }

  revoke(d: PairedDevice): void {
    if (!confirm(`Revoke device "${d.device_name || d.id}"?`)) return;
    this.http.delete(`/api/pairing/tokens/${d.id}`).subscribe(() => this.refreshDevices());
  }
}
