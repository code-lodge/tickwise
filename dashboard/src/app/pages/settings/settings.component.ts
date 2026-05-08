import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import type { SettingsMap } from '../../models';

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
  `,
})
export class SettingsPageComponent implements OnInit {
  private api = inject(ApiService);
  editable = signal<{ key: string; value: string }[]>([]);
  error = signal<string | null>(null);
  saved = signal<boolean>(false);

  ngOnInit(): void {
    this.api.settings().subscribe((s) => this.populate(s));
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
