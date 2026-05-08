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
    path: 'settings',
    loadComponent: () =>
      import('./pages/settings/settings.component').then((m) => m.SettingsPageComponent),
  },
  { path: '**', redirectTo: '' },
];
