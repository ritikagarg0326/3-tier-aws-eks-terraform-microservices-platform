import { Component, effect, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { filter } from 'rxjs';
import { AuthService } from './core/auth.service';
import { WatchlistStore } from './core/watchlist.store';

@Component({
  selector: 'hs-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, FormsModule, MatIconModule, MatMenuModule],
  template: `
    @if (auth.isLoggedIn()) {
      <header class="nav" [class.solid]="scrolled()">
        <a routerLink="/" class="logo" aria-label="hotstar home"><span class="logo-mark">▶</span>hotstar</a>
        <nav class="links">
          <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">Home</a>
          <a routerLink="/browse" [queryParams]="{ category: 'movie' }" routerLinkActive="active">Movies</a>
          <a routerLink="/browse" [queryParams]="{ category: 'tv_show' }" routerLinkActive="active">TV</a>
          <a routerLink="/browse" [queryParams]="{ category: 'web_series' }" routerLinkActive="active">Web Series</a>
          <a routerLink="/watchlist" routerLinkActive="active">Watchlist</a>
        </nav>
        <form class="search" (ngSubmit)="search()" role="search">
          <mat-icon>search</mat-icon>
          <input name="q" [(ngModel)]="q" placeholder="Search titles" aria-label="Search titles" autocomplete="off" />
        </form>
        <button class="avatar" [matMenuTriggerFor]="menu" aria-label="Account menu" [style.background]="'#1f80e0'">{{ initial() }}</button>
        <mat-menu #menu="matMenu" xPosition="before">
          <div class="menu-head"><strong>{{ auth.user()?.username }}</strong><small>{{ auth.user()?.email }}</small></div>
          <a mat-menu-item routerLink="/profile"><mat-icon>person</mat-icon>Profile</a>
          <a mat-menu-item routerLink="/watchlist"><mat-icon>bookmark</mat-icon>Watchlist</a>
          <a mat-menu-item routerLink="/history"><mat-icon>history</mat-icon>Watch history</a>
          @if (auth.isAdmin()) { <a mat-menu-item routerLink="/admin"><mat-icon>admin_panel_settings</mat-icon>Admin dashboard</a> }
          <button mat-menu-item (click)="auth.logout()"><mat-icon>logout</mat-icon>Sign out</button>
        </mat-menu>
      </header>
    }
    <main [class.with-nav]="auth.isLoggedIn()"><router-outlet /></main>
    @if (auth.isLoggedIn()) { <footer class="foot">hotstar · demo OTT platform built with Angular, FastAPI, MySQL and MinIO</footer> }
  `,
})
export class AppComponent {
  readonly auth = inject(AuthService);
  private router = inject(Router);
  private watchlist = inject(WatchlistStore);
  q = '';
  scrolled = signal(false);

  constructor() {
    effect(() => { this.auth.isLoggedIn() ? this.watchlist.load() : this.watchlist.reset(); }, { allowSignalWrites: true });
    window.addEventListener('scroll', () => this.scrolled.set(window.scrollY > 20), { passive: true });
    this.router.events.pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd)).subscribe((e) => {
      if (!e.urlAfterRedirects.startsWith('/browse')) this.q = '';
    });
  }

  initial(): string { return (this.auth.user()?.username ?? '?').charAt(0).toUpperCase(); }

  search(): void {
    const q = this.q.trim();
    this.router.navigate(['/browse'], { queryParams: q ? { q } : {} });
  }
}
