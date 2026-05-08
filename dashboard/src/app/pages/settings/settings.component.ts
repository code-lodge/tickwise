import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ApiService } from '../../services/api.service';
import type { SettingsMap } from '../../models';

interface MonitorEntry {
  index: number;
  left: number;
  top: number;
  width: number;
  height: number;
  label: string | null;
  enabled: boolean;
  is_primary: boolean;
}

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h1>Settings</h1>
    <p class="muted">
      Tracking, OCR, and Pomodoro defaults. Changes persist immediately.
    </p>

    <div class="card stack">
      <table>
        <thead>
          <tr>
            <th>Key</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let entry of editable()">
            <td>{{ entry.key }}</td>
            <td>
              <input
                [(ngModel)]="entry.value"
                (change)="save(entry.key, entry.value)"
                style="width:100%"
              />
            </td>
          </tr>
        </tbody>
      </table>
      <p *ngIf="error()" class="error">{{ error() }}</p>
      <p *ngIf="saved()" class="muted">Saved.</p>
    </div>

    <h2 style="margin-top: 2rem">Monitors</h2>
    <p class="muted">Detected displays. Disable a monitor to skip capturing it; the primary
      preference influences fallback when the focused-window position can't be determined.</p>
    <div class="card">
      <table style="width:100%; border-collapse: collapse">
        <thead>
          <tr>
            <th>#</th><th>Resolution</th><th>Position</th><th>Label</th>
            <th>Enabled</th><th>Primary</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let m of monitors()" style="border-top: 1px solid var(--color-border)">
            <td>{{ m.index }}</td>
            <td>{{ m.width }}×{{ m.height }}</td>
            <td>{{ m.left }}, {{ m.top }}</td>
            <td><input [(ngModel)]="m.label" (change)="saveMonitor(m)" style="width: 12em" /></td>
            <td><input type="checkbox" [(ngModel)]="m.enabled" (change)="saveMonitor(m)" /></td>
            <td><input type="radio" name="primary" [checked]="m.is_primary" (change)="setPrimary(m)" /></td>
          </tr>
          <tr *ngIf="!monitors().length">
            <td colspan="6" class="muted">No monitors detected.</td>
          </tr>
        </tbody>
      </table>
    </div>
  `,
})
export class SettingsPageComponent implements OnInit {
  private api = inject(ApiService);
  private http = inject(HttpClient);
  editable = signal<{ key: string; value: string }[]>([]);
  error = signal<string | null>(null);
  saved = signal<boolean>(false);
  monitors = signal<MonitorEntry[]>([]);

  ngOnInit(): void {
    this.api.settings().subscribe((s) => this.populate(s));
    this.refreshMonitors();
  }

  refreshMonitors(): void {
    this.http.get<MonitorEntry[]>('/api/monitors').subscribe((rows) => this.monitors.set(rows));
  }

  saveMonitor(m: MonitorEntry): void {
    this.http
      .put<MonitorEntry>(`/api/monitors/${m.index}`, {
        label: m.label,
        enabled: m.enabled,
        is_primary: m.is_primary,
      })
      .subscribe({
        next: () => {
          this.saved.set(true);
          setTimeout(() => this.saved.set(false), 1500);
        },
        error: (err) => this.error.set(err.error?.detail || err.message),
      });
  }

  setPrimary(m: MonitorEntry): void {
    this.monitors.update((rows) => rows.map((r) => ({ ...r, is_primary: r.index === m.index })));
    const target = this.monitors().find((r) => r.index === m.index);
    if (target) this.saveMonitor(target);
  }

  private populate(map: SettingsMap): void {
    const sorted = Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
    this.editable.set(sorted.map(([key, value]) => ({ key, value })));
  }

  save(key: string, value: string): void {
    this.api.updateSettings({ [key]: value }).subscribe({
      next: (s) => {
        this.populate(s);
        this.error.set(null);
        this.saved.set(true);
        setTimeout(() => this.saved.set(false), 1500);
      },
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }
}
