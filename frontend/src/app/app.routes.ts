import { Routes } from '@angular/router';
import { adminGuard, authGuard, guestGuard } from './core/guards';

export const routes: Routes = [
  { path: 'login', canActivate: [guestGuard], title: 'Sign in · hotstar', loadComponent: () => import('./pages/login.component').then((m) => m.LoginComponent) },
  { path: 'register', canActivate: [guestGuard], title: 'Join · hotstar', loadComponent: () => import('./pages/register.component').then((m) => m.RegisterComponent) },
  { path: '', pathMatch: 'full', canActivate: [authGuard], title: 'hotstar', loadComponent: () => import('./pages/home.component').then((m) => m.HomeComponent) },
  { path: 'browse', canActivate: [authGuard], title: 'Browse · hotstar', loadComponent: () => import('./pages/browse.component').then((m) => m.BrowseComponent) },
  { path: 'title/:id', canActivate: [authGuard], title: 'Details · hotstar', loadComponent: () => import('./pages/detail.component').then((m) => m.DetailComponent) },
  { path: 'watch/:id', canActivate: [authGuard], title: 'Watch · hotstar', loadComponent: () => import('./pages/watch.component').then((m) => m.WatchComponent) },
  { path: 'watchlist', canActivate: [authGuard], title: 'Watchlist · hotstar', loadComponent: () => import('./pages/watchlist.component').then((m) => m.WatchlistComponent) },
  { path: 'history', canActivate: [authGuard], title: 'Watch history · hotstar', loadComponent: () => import('./pages/history.component').then((m) => m.HistoryComponent) },
  { path: 'profile', canActivate: [authGuard], title: 'Profile · hotstar', loadComponent: () => import('./pages/profile.component').then((m) => m.ProfileComponent) },
  {
    path: 'admin', canActivate: [adminGuard], loadComponent: () => import('./pages/admin/admin-layout.component').then((m) => m.AdminLayoutComponent),
    children: [
      { path: '', pathMatch: 'full', title: 'Dashboard · hotstar admin', loadComponent: () => import('./pages/admin/admin-dashboard.component').then((m) => m.AdminDashboardComponent) },
      { path: 'content', title: 'Content · hotstar admin', loadComponent: () => import('./pages/admin/admin-content.component').then((m) => m.AdminContentComponent) },
      { path: 'content/new', title: 'Add content · hotstar admin', loadComponent: () => import('./pages/admin/admin-content-form.component').then((m) => m.AdminContentFormComponent) },
      { path: 'content/:id', title: 'Edit content · hotstar admin', loadComponent: () => import('./pages/admin/admin-content-form.component').then((m) => m.AdminContentFormComponent) },
      { path: 'users', title: 'Users · hotstar admin', loadComponent: () => import('./pages/admin/admin-users.component').then((m) => m.AdminUsersComponent) },
    ],
  },
  { path: '**', title: 'Not found · hotstar', loadComponent: () => import('./pages/not-found.component').then((m) => m.NotFoundComponent) },
];
