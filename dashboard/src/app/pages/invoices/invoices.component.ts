import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ApiService } from '../../services/api.service';
import type { Client, FreelancerProfile, Invoice, Project } from '../../models';

interface DraftLineItem {
  description: string;
  hours: number;
  rate: number;
  session_ids?: number[];
  session_id?: number | null;
}

interface DraftPayload {
  project_id: number;
  client_id: number | null;
  from_date: string;
  to_date: string;
  currency: string;
  tax_rate: number;
  subtotal: number;
  tax_amount: number;
  total: number;
  line_items: DraftLineItem[];
}

@Component({
  selector: 'app-invoices',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h1>Invoices</h1>

    <details class="card" [open]="!profile()?.name">
      <summary><strong>Business profile</strong></summary>
      <div class="stack" style="margin-top: 0.75rem">
        <div class="row" style="flex-wrap: wrap">
          <label>Name <input [(ngModel)]="profileDraft.name" /></label>
          <label>Company <input [(ngModel)]="profileDraft.company" /></label>
          <label>Email <input type="email" [(ngModel)]="profileDraft.email" /></label>
          <label>Tax ID <input [(ngModel)]="profileDraft.tax_id" /></label>
        </div>
        <label>Address
          <textarea rows="2" [(ngModel)]="profileDraft.address" style="width: 100%"></textarea>
        </label>
        <div class="row" style="flex-wrap: wrap">
          <label>IBAN <input [(ngModel)]="profileDraft.iban" /></label>
          <label>Bank <input [(ngModel)]="profileDraft.bank_name" /></label>
          <label>Currency <input [(ngModel)]="profileDraft.default_currency" maxlength="3" /></label>
          <label>Default rate <input type="number" [(ngModel)]="profileDraft.default_hourly_rate" /></label>
        </div>
        <div class="row" style="flex-wrap: wrap">
          <label>Invoice prefix <input [(ngModel)]="profileDraft.invoice_prefix" /></label>
          <label>Next number <input type="number" [(ngModel)]="profileDraft.invoice_next_number" /></label>
          <label>Default tax % <input type="number" [(ngModel)]="profileDraft.invoice_default_tax_rate" /></label>
          <label>Due days <input type="number" [(ngModel)]="profileDraft.invoice_default_due_days" /></label>
        </div>
        <label>Payment terms
          <textarea rows="2" [(ngModel)]="profileDraft.payment_terms" style="width: 100%"></textarea>
        </label>
        <div class="row">
          <button (click)="saveProfile()">Save profile</button>
          <input #logo type="file" accept="image/*" (change)="uploadLogo(logo)" />
        </div>
        <p *ngIf="profile()?.logo_path" class="muted">Logo on file: {{ profile()!.logo_path }}</p>
      </div>
    </details>

    <div class="card" style="margin-top: 1rem">
      <h2>New invoice from sessions</h2>
      <div class="row" style="flex-wrap: wrap">
        <label>Project
          <select [(ngModel)]="wizardProjectId">
            <option [ngValue]="null">— select —</option>
            <option *ngFor="let p of projects()" [ngValue]="p.id">{{ p.name }}</option>
          </select>
        </label>
        <label>From <input type="date" [(ngModel)]="wizardFrom" /></label>
        <label>To <input type="date" [(ngModel)]="wizardTo" /></label>
        <label>Override rate <input type="number" [(ngModel)]="wizardRate" placeholder="optional" /></label>
        <button (click)="generateDraft()">Generate</button>
      </div>

      <div *ngIf="draft()" class="stack" style="margin-top: 1rem">
        <p class="muted">{{ draft()!.line_items.length }} line items · subtotal {{ draft()!.subtotal | number:'1.2-2' }} {{ draft()!.currency }}</p>
        <table style="width: 100%; border-collapse: collapse">
          <thead><tr><th>Description</th><th>Hours</th><th>Rate</th><th>Amount</th></tr></thead>
          <tbody>
            <tr *ngFor="let li of draft()!.line_items; let i = index" style="border-top: 1px solid var(--color-border)">
              <td><input [(ngModel)]="li.description" style="width: 100%" /></td>
              <td><input type="number" step="0.25" [(ngModel)]="li.hours" /></td>
              <td><input type="number" step="0.5" [(ngModel)]="li.rate" /></td>
              <td>{{ (li.hours * li.rate) | number:'1.2-2' }}</td>
            </tr>
          </tbody>
        </table>
        <div class="row">
          <button (click)="saveDraft()">Save as draft</button>
          <button class="ghost" (click)="draft.set(null)">Cancel</button>
        </div>
      </div>
      <p *ngIf="error()" class="error">{{ error() }}</p>
    </div>

    <div class="card" style="margin-top: 1rem">
      <h2>All invoices</h2>
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr>
            <th>Number</th><th>Issued</th><th>Due</th><th>Client</th>
            <th>Total</th><th>Status</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let inv of invoices()" style="border-top: 1px solid var(--color-border)">
            <td>{{ inv.invoice_number }}</td>
            <td>{{ inv.issued_date }}</td>
            <td>{{ inv.due_date }}</td>
            <td>{{ clientNameById(inv.client_id) }}</td>
            <td>{{ inv.total | number:'1.2-2' }} {{ inv.currency }}</td>
            <td><span class="badge" [class]="inv.status">{{ inv.status }}</span></td>
            <td style="text-align: right; white-space: nowrap">
              <button class="ghost" (click)="downloadPdf(inv)">PDF</button>
              <button class="ghost" *ngIf="inv.status === 'draft'" (click)="markSent(inv)">Mark sent</button>
              <button class="ghost" *ngIf="inv.status === 'sent' || inv.status === 'overdue'" (click)="markPaid(inv)">Mark paid</button>
              <button class="ghost" *ngIf="inv.status !== 'paid'" (click)="remove(inv)">Delete</button>
            </td>
          </tr>
          <tr *ngIf="!invoices().length"><td colspan="7" class="muted">No invoices yet.</td></tr>
        </tbody>
      </table>
    </div>
  `,
  styles: [
    `
      .badge { padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.75rem; background: #e2e8f0; }
      .badge.draft { background: #e2e8f0; color: #475569; }
      .badge.sent { background: #dbeafe; color: #1e3a8a; }
      .badge.paid { background: #dcfce7; color: #166534; }
      .badge.overdue { background: #fee2e2; color: #991b1b; }
      .badge.cancelled { background: #f1f5f9; color: #64748b; text-decoration: line-through; }
    `,
  ],
})
export class InvoicesPageComponent implements OnInit {
  private api = inject(ApiService);
  private http = inject(HttpClient);

  profile = signal<FreelancerProfile | null>(null);
  profileDraft: Partial<FreelancerProfile> = {};
  invoices = signal<Invoice[]>([]);
  projects = signal<Project[]>([]);
  clients = signal<Client[]>([]);

  wizardProjectId: number | null = null;
  wizardFrom = '';
  wizardTo = '';
  wizardRate: number | null = null;
  draft = signal<DraftPayload | null>(null);
  error = signal<string | null>(null);

  ngOnInit(): void {
    const today = new Date();
    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
    this.wizardFrom = monthStart.toISOString().slice(0, 10);
    this.wizardTo = today.toISOString().slice(0, 10);

    this.api.profile().subscribe((p) => {
      this.profile.set(p);
      this.profileDraft = { ...p };
    });
    this.api.projects(true).subscribe((p) => this.projects.set(p));
    this.api.clients().subscribe((c) => this.clients.set(c));
    this.refreshInvoices();
  }

  refreshInvoices(): void {
    this.api.invoices().subscribe((rows) => this.invoices.set(rows));
  }

  clientNameById(id: number | null): string {
    if (id === null) return '';
    const c = this.clients().find((x) => x.id === id);
    return c?.name || `#${id}`;
  }

  saveProfile(): void {
    this.api.updateProfile(this.profileDraft).subscribe({
      next: (p) => {
        this.profile.set(p);
        this.profileDraft = { ...p };
      },
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }

  uploadLogo(input: HTMLInputElement): void {
    const file = input.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    this.http.post<{ logo_path: string }>('/api/profile/logo', fd).subscribe({
      next: () => this.api.profile().subscribe((p) => this.profile.set(p)),
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }

  generateDraft(): void {
    if (!this.wizardProjectId) {
      this.error.set('Pick a project first');
      return;
    }
    this.api
      .draftInvoice({
        project_id: this.wizardProjectId,
        from_date: this.wizardFrom,
        to_date: this.wizardTo,
        rate_override: this.wizardRate ?? undefined,
      })
      .subscribe({
        next: (d) => {
          this.draft.set(d as DraftPayload);
          this.error.set(null);
        },
        error: (err) => this.error.set(err.error?.detail || err.message),
      });
  }

  saveDraft(): void {
    const d = this.draft();
    if (!d) return;
    const payload: Partial<Invoice> = {
      project_id: d.project_id,
      client_id: d.client_id,
      issued_date: new Date().toISOString().slice(0, 10),
      tax_rate: d.tax_rate,
      currency: d.currency,
      line_items: d.line_items.map((li) => ({
        id: 0,
        description: li.description,
        hours: Number(li.hours) || 0,
        rate: Number(li.rate) || 0,
        amount: 0,
        session_id: li.session_ids?.[0] ?? null,
      })),
    };
    this.api.createInvoice(payload).subscribe({
      next: () => {
        this.draft.set(null);
        this.refreshInvoices();
      },
      error: (err) => this.error.set(err.error?.detail || err.message),
    });
  }

  markSent(inv: Invoice): void {
    this.api.markInvoiceSent(inv.id).subscribe(() => this.refreshInvoices());
  }
  markPaid(inv: Invoice): void {
    this.api.markInvoicePaid(inv.id).subscribe(() => this.refreshInvoices());
  }
  remove(inv: Invoice): void {
    if (!confirm(`Delete invoice ${inv.invoice_number}?`)) return;
    this.api.deleteInvoice(inv.id).subscribe(() => this.refreshInvoices());
  }
  downloadPdf(inv: Invoice): void {
    fetch(`/api/invoices/${inv.id}/pdf`)
      .then((res) => res.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${inv.invoice_number}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      });
  }
}
