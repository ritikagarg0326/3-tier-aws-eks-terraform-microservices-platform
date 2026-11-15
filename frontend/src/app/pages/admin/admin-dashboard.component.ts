import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { KeyValuePipe } from '@angular/common';
import { forkJoin } from 'rxjs';
import { Api } from '../../core/api.service';
import { AuthStats, CATEGORY_LABELS, ContentStats } from '../../core/models';
import { errMsg } from '../../core/util';
import { AsyncStateComponent } from '../../shared/async-state.component';

@Component({
  selector: 'hs-admin-dashboard',
  standalone: true,
  imports: [RouterLink, KeyValuePipe, AsyncStateComponent],
  template: `
    <div class="toolbar"><h1 class="page-title" style="margin:0">Dashboard</h1><span class="spacer"></span><a class="btn sm" routerLink="/admin/content/new">+ Add content</a></div>
    <hs-async [loading]="loading()" [error]="error()" (retry)="load()">
      @if (content(); as c) {
        @if (users(); as u) {
          <div class="stat-grid">
            <div class="stat"><div class="n">{{ c.total }}</div><div class="l">Titles in catalogue</div></div>
            <div class="stat"><div class="n">{{ c.featured }}</div><div class="l">Featured titles</div></div>
            <div class="stat"><div class="n">{{ c.added_last_7_days }}</div><div class="l">Added in last 7 days</div></div>
            <div class="stat"><div class="n">{{ u.total_users }}</div><div class="l">Registered users</div></div>
            <div class="stat"><div class="n">{{ u.active_users }}</div><div class="l">Active accounts</div></div>
            <div class="stat"><div class="n">{{ u.admins }}</div><div class="l">Administrators</div></div>
          </div>
        }
        <div class="two-col">
          <section class="panel"><h2 style="font-size:17px;margin-bottom:14px">By category</h2>
            <div class="bars">@for (e of c.by_category | keyvalue; track e.key) {
              <div class="bar-row"><span>{{ label(e.key) }}</span><div class="track"><span [style.width.%]="pct(e.value, c.total)"></span></div><b>{{ e.value }}</b></div>
            } @empty { <span class="muted">No data</span> }</div></section>
          <section class="panel"><h2 style="font-size:17px;margin-bottom:14px">By genre</h2>
            <div class="bars">@for (e of c.by_genre | keyvalue; track e.key) {
              <div class="bar-row"><span>{{ e.key }}</span><div class="track"><span [style.width.%]="pct(e.value, c.total)"></span></div><b>{{ e.value }}</b></div>
            } @empty { <span class="muted">No data</span> }</div></section>
          <section class="panel"><h2 style="font-size:17px;margin-bottom:14px">By language</h2>
            <div class="bars">@for (e of c.by_language | keyvalue; track e.key) {
              <div class="bar-row"><span>{{ e.key }}</span><div class="track"><span [style.width.%]="pct(e.value, c.total)"></span></div><b>{{ e.value }}</b></div>
            } @empty { <span class="muted">No data</span> }</div></section>
        </div>
      }
    </hs-async>
  `,
})
export class AdminDashboardComponent {
  private api = inject(Api);
  loading = signal(true);
  error = signal<string | null>(null);
  content = signal<ContentStats | null>(null);
  users = signal<AuthStats | null>(null);

  constructor() { this.load(); }

  label(k: string) { return CATEGORY_LABELS[k] ?? k; }
  pct(v: number, total: number) { return total ? Math.max(3, (v / total) * 100) : 0; }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    forkJoin({ content: this.api.contentStats(), users: this.api.userStats() }).subscribe({
      next: (r) => { this.content.set(r.content); this.users.set(r.users); this.loading.set(false); },
      error: (e) => { this.error.set(errMsg(e)); this.loading.set(false); },
    });
  }
}
