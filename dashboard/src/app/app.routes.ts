import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/live/live.component').then((m) => m.LivePageComponent),
  },
  {
    path: 'timeline',
    loadComponent: () =>
      import('./pages/timeline/timeline.component').then((m) => m.TimelinePageComponent),
  },
  {
    path: 'projects',
    loadComponent: () =>
      import('./pages/projects/projects.component').then((m) => m.ProjectsPageComponent),
  },
  {
    path: 'privacy',
    loadComponent: () =>
      import('./pages/privacy/privacy.component').then((m) => m.PrivacyPageComponent),
  },
  {
    path: 'calendar',
    loadComponent: () =>
      import('./pages/calendar/calendar.component').then((m) => m.CalendarPageComponent),
  },
  {
    path: 'reports',
    loadComponent: () =>
      import('./pages/reports/reports.component').then((m) => m.ReportsPageComponent),
  },
  {
    path: 'clients',
    loadComponent: () =>
      import('./pages/clients/clients.component').then((m) => m.ClientsPageComponent),
  },
  {
    path: 'invoices',
    loadComponent: () =>
      import('./pages/invoices/invoices.component').then((m) => m.InvoicesPageComponent),
  },
  {
    path: 'settings',
    loadComponent: () =>
      import('./pages/settings/settings.component').then((m) => m.SettingsPageComponent),
  },
  { path: '**', redirectTo: '' },
];
