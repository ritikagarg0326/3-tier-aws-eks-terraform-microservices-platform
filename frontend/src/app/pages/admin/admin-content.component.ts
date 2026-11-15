import { Component, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Api } from '../../core/api.service';
import { CATEGORY_SINGULAR, Content } from '../../core/models';
import { errMsg, mediaUrl } from '../../core/util';
import { AsyncStateComponent } from '../../shared/async-state.component';

@Component({
  selector: 'hs-admin-content',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, MatFormFieldModule, MatInputModule, MatIconModule, AsyncStateComponent],
  template: `
    <div class="toolbar"><h1 class="page-title" style="margin:0">Content</h1><span class="spacer"></span>
      <mat-form-field appearance="outline" subscriptSizing="dynamic"><mat-label>Search titles</mat-label><input matInput [formControl]="search" /></mat-form-field>
      <a class="btn sm" routerLink="/admin/content/new"><mat-icon>add</mat-icon>Add content</a></div>
    <hs-async [loading]="loading()" [error]="error()" [empty]="!loading() && !items().length" emptyText="No content found." (retry)="load()">
      <div class="panel table-wrap" style="padding:8px">
        <table class="data">
          <thead><tr><th></th><th>Title</th><th>Category</th><th>Genre</th><th>Language</th><th>Year</th><th>Length</th><th></th></tr></thead>
          <tbody>
            @for (c of items(); track c.id) {
              <tr>
                <td><img class="thumb-sm" [src]="poster(c.id)" alt="" loading="lazy" (error)="hide($event)" /></td>
                <td><a [routerLink]="['/admin/content', c.id]"><b>{{ c.title }}</b></a>@if (c.is_featured) { <span class="chip" style="margin-left:8px">Featured</span> }</td>
                <td>{{ cat(c) }}</td><td>{{ c.genre }}</td><td>{{ c.language }}</td><td>{{ c.release_year }}</td><td>{{ c.duration_minutes }}m</td>
                <td><div class="actions-cell">
                  <a class="btn ghost sm" [routerLink]="['/admin/content', c.id]"><mat-icon>edit</mat-icon>Edit</a>
                  <button class="btn danger sm" type="button" (click)="remove(c)"><mat-icon>delete</mat-icon></button></div></td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <div class="pager" style="gap:12px;align-items:center">
        <button class="btn ghost sm" type="button" [disabled]="page() <= 1" (click)="go(page() - 1)">Previous</button>
        <span class="muted">Page {{ page() }} of {{ pages() }} · {{ total() }} titles</span>
        <button class="btn ghost sm" type="button" [disabled]="page() >= pages()" (click)="go(page() + 1)">Next</button>
      </div>
    </hs-async>
  `,
})
export class AdminContentComponent {
  private api = inject(Api);
  private snack = inject(MatSnackBar);
  search = new FormControl('', { nonNullable: true });
  loading = signal(true);
  error = signal<string | null>(null);
  items = signal<Content[]>([]);
  page = signal(1);
  pages = signal(1);
  total = signal(0);
  poster = (id: number) => mediaUrl(id, 'poster');
  cat = (c: Content) => CATEGORY_SINGULAR[c.category];

  constructor() {
    this.load();
    this.search.valueChanges.pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed()).subscribe(() => this.go(1));
  }

  hide(ev: Event) { (ev.target as HTMLImageElement).style.visibility = 'hidden'; }
  go(p: number) { this.page.set(p); this.load(); }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.listContent({ q: this.search.value.trim(), page: this.page(), page_size: 15 }).subscribe({
      next: (r) => { this.items.set(r.items); this.pages.set(Math.max(1, r.pages)); this.total.set(r.total); this.loading.set(false); },
      error: (e) => { this.error.set(errMsg(e)); this.loading.set(false); },
    });
  }

  remove(c: Content): void {
    if (!confirm(`Delete "${c.title}" and its uploaded media? This cannot be undone.`)) return;
    this.api.deleteContent(c.id).subscribe({
      next: () => { this.snack.open('Content deleted', undefined, { duration: 2500 }); this.load(); },
      error: (e) => this.snack.open(errMsg(e), 'Dismiss', { duration: 4000 }),
    });
  }
}
