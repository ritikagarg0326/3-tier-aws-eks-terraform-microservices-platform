import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'hs-admin-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, MatIconModule],
  template: `
    <div class="admin">
      <aside>
        <h3>Admin</h3>
        <a routerLink="/admin" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }"><mat-icon>dashboard</mat-icon>Dashboard</a>
        <a routerLink="/admin/content" routerLinkActive="active"><mat-icon>video_library</mat-icon>Content</a>
        <a routerLink="/admin/users" routerLinkActive="active"><mat-icon>group</mat-icon>Users</a>
        <a routerLink="/"><mat-icon>arrow_back</mat-icon>Back to site</a>
      </aside>
      <section class="content"><router-outlet /></section>
    </div>
  `,
})
export class AdminLayoutComponent {}
