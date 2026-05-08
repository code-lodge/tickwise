import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import type { Client } from '../../models';

@Component({
  selector: 'app-clients',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h1>Clients</h1>

    <div class="card stack">
      <h2>{{ editing()?.id ? 'Edit client' : 'New client' }}</h2>
      <div class="row" style="flex-wrap: wrap; gap: 0.75rem">
        <label>Name <input [(ngModel)]="draft.name" placeholder="Acme Corp" /></label>
        <label>Email <input type="email" [(ngModel)]="draft.email" /></label>
        <label>Tax ID <input [(ngModel)]="draft.tax_id" /></label>
        <label>Timezone <input [(ngModel)]="draft.timezone" /></label>
      </div>
      <label>
        Address
        <textarea rows="3" [(ngModel)]="draft.address" style="width: 100%"></textarea>
      </label>
      <div class="row">
        <button (click)="save()">{{ editing()?.id ? 'Save changes' : 'Create' }}</button>
        <button class="ghost" *ngIf="editing()?.id" (click)="reset()">Cancel</button>
      </div>
      <p *ngIf="error()" class="error">{{ error() }}</p>
    </div>

    <div class="card" style="margin-top: 1rem">
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr>
            <th>Name</th><th>Email</th><th>Tax ID</th><th>Timezone</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let c of clients()" style="border-top: 1px solid var(--color-border)">
            <td>{{ c.name }}</td>
            <td>{{ c.email }}</td>
            <td>{{ c.tax_id }}</td>
            <td>{{ c.timezone }}</td>
            <td style="text-align: right">
              <button class="ghost" (click)="edit(c)">Edit</button>
              <button class="ghost" (click)="remove(c)">Delete</button>
            </td>
          </tr>
          <tr *ngIf="!clients().length"><td colspan="5" class="muted">No clients yet.</td></tr>
        </tbody>
      </table>
    </div>
  `,
})
export class ClientsPageComponent implements OnInit {
  private api = inject(ApiService);

  clients = signal<Client[]>([]);
  editing = signal<Partial<Client> | null>(null);
  draft: Partial<Client> = this.empty();
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.refresh();
  }

  empty(): Partial<Client> {
    return { name: '', email: '', timezone: 'UTC', address: '', tax_id: '' };
  }

  refresh(): void {
    this.api.clients().subscribe((rows) => this.clients.set(rows));
  }

  edit(c: Client): void {
    this.editing.set(c);
    this.draft = { ...c };
  }

  reset(): void {
    this.editing.set(null);
    this.draft = this.empty();
    this.error.set(null);
  }

  save(): void {
    if (!this.draft.name) {
      this.error.set('Name is required');
      return;
    }
    const editing = this.editing();
    const op$ = editing?.id
      ? this.api.updateClient(editing.id, this.draft)
      : this.api.createClient(this.draft);
    op$.subscribe({
      next: () => {
        this.reset();
        this.refresh();
      },
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }

  remove(c: Client): void {
    if (!confirm(`Delete client "${c.name}"?`)) return;
    this.api.deleteClient(c.id).subscribe({
      next: () => this.refresh(),
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }
}
