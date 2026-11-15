import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { Api } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { User } from '../../core/models';
import { errMsg } from '../../core/util';
import { AsyncStateComponent } from '../../shared/async-state.component';

@Component({
  selector: 'hs-admin-users',
  standalone: true,
  imports: [DatePipe, FormsModule, ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatIconModule, AsyncStateComponent],
  template: `
    <div class="toolbar"><h1 class="page-title" style="margin:0">Users & roles</h1><span class="spacer"></span>
      <mat-form-field appearance="outline" subscriptSizing="dynamic"><mat-label>Search email or username</mat-label><input matInput [formControl]="search" /></mat-form-field></div>
    <hs-async [loading]="loading()" [error]="error()" [empty]="!loading() && !items().length" emptyText="No users found." (retry)="load()">
      <div class="panel table-wrap" style="padding:8px">
        <table class="data">
          <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Joined</th><th>Last login</th><th></th></tr></thead>
          <tbody>
            @for (u of items(); track u.id) {
              <tr>
                <td><b>{{ u.username }}</b><br /><span class="muted">{{ u.email }}</span></td>
                <td><select class="inline" [ngModel]="u.role" (ngModelChange)="setRole(u, $event)" [disabled]="isSelf(u)" [attr.aria-label]="'Role for ' + u.username"><option value="user">Viewer</option><option value="admin">Admin</option></select></td>
                <td><button class="btn sm" [class.ghost]="u.is_active" [class.danger]="!u.is_active" type="button" (click)="toggleActive(u)" [disabled]="isSelf(u)">{{ u.is_active ? 'Active' : 'Disabled' }}</button></td>
                <td>{{ u.created_at + 'Z' | date: 'mediumDate' }}</td>
                <td>{{ u.last_login_at ? ((u.last_login_at + 'Z') | date: 'medium') : '—' }}</td>
                <td><div class="actions-cell"><button class="btn danger sm" type="button" (click)="remove(u)" [disabled]="isSelf(u)" [attr.aria-label]="'Delete ' + u.username"><mat-icon>delete</mat-icon></button></div></td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <div class="pager" style="gap:12px;align-items:center">
        <button class="btn ghost sm" type="button" [disabled]="page() <= 1" (click)="go(page() - 1)">Previous</button>
        <span class="muted">Page {{ page() }} of {{ pages() }} · {{ total() }} users</span>
        <button class="btn ghost sm" type="button" [disabled]="page() >= pages()" (click)="go(page() + 1)">Next</button>
      </div>
    </hs-async>
  `,
})
export class AdminUsersComponent {
  private api = inject(Api);
  private auth = inject(AuthService);
  private snack = inject(MatSnackBar);
  search = new FormControl('', { nonNullable: true });
  loading = signal(true);
  error = signal<string | null>(null);
  items = signal<User[]>([]);
  page = signal(1);
  pages = signal(1);
  total = signal(0);

  constructor() {
    this.load();
    this.search.valueChanges.pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed()).subscribe(() => this.go(1));
  }

  isSelf(u: User) { return u.id === this.auth.user()?.id; }
  go(p: number) { this.page.set(p); this.load(); }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.adminUsers({ q: this.search.value.trim() || undefined, page: this.page(), page_size: 15 }).subscribe({
      next: (r) => { this.items.set(r.items); this.pages.set(Math.max(1, r.pages)); this.total.set(r.total); this.loading.set(false); },
      error: (e) => { this.error.set(errMsg(e)); this.loading.set(false); },
    });
  }

  private apply(u: User, body: { role?: string; is_active?: boolean }, msg: string): void {
    this.api.adminUpdateUser(u.id, body).subscribe({
      next: (nu) => { this.items.update((l) => l.map((x) => (x.id === nu.id ? nu : x))); this.snack.open(msg, undefined, { duration: 2000 }); },
      error: (e) => { this.snack.open(errMsg(e), 'Dismiss', { duration: 4000 }); this.load(); },
    });
  }
  setRole(u: User, role: string) { if (role !== u.role) this.apply(u, { role }, `${u.username} is now ${role === 'admin' ? 'an admin' : 'a viewer'}`); }
  toggleActive(u: User) { this.apply(u, { is_active: !u.is_active }, u.is_active ? `${u.username} disabled` : `${u.username} enabled`); }

  remove(u: User): void {
    if (!confirm(`Delete user "${u.username}"? This cannot be undone.`)) return;
    this.api.adminDeleteUser(u.id).subscribe({
      next: () => { this.snack.open('User deleted', undefined, { duration: 2000 }); this.load(); },
      error: (e) => this.snack.open(errMsg(e), 'Dismiss', { duration: 4000 }),
    });
  }
}
