import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { Api } from '../core/api.service';
import { CATEGORY_LABELS, Content, Facets } from '../core/models';
import { errMsg } from '../core/util';
import { AsyncStateComponent } from '../shared/async-state.component';
import { PosterCardComponent } from '../shared/poster-card.component';

const KEYS = ['q', 'genre', 'language', 'category', 'sort'] as const;

@Component({
  selector: 'hs-browse',
  standalone: true,
  imports: [ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatIconModule, AsyncStateComponent, PosterCardComponent],
  template: `
    <div class="page">
      <h1 class="page-title">{{ heading() }}</h1>
      <form class="filters" [formGroup]="form">
        <mat-form-field appearance="outline" class="grow" subscriptSizing="dynamic">
          <mat-label>Search</mat-label>
          <input matInput formControlName="q" placeholder="Title or description" />
          <mat-icon matSuffix>search</mat-icon>
        </mat-form-field>
        <mat-form-field appearance="outline" subscriptSizing="dynamic">
          <mat-label>Category</mat-label>
          <mat-select formControlName="category">
            <mat-option value="">All</mat-option>
            @for (c of categories; track c[0]) { <mat-option [value]="c[0]">{{ c[1] }}</mat-option> }
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline" subscriptSizing="dynamic">
          <mat-label>Genre</mat-label>
          <mat-select formControlName="genre">
            <mat-option value="">All</mat-option>
            @for (g of facets()?.genres ?? []; track g) { <mat-option [value]="g">{{ g }}</mat-option> }
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline" subscriptSizing="dynamic">
          <mat-label>Language</mat-label>
          <mat-select formControlName="language">
            <mat-option value="">All</mat-option>
            @for (l of facets()?.languages ?? []; track l) { <mat-option [value]="l">{{ l }}</mat-option> }
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline" subscriptSizing="dynamic">
          <mat-label>Sort by</mat-label>
          <mat-select formControlName="sort">
            <mat-option value="newest">Recently added</mat-option>
            <mat-option value="year">Release year</mat-option>
            <mat-option value="title">Title A-Z</mat-option>
          </mat-select>
        </mat-form-field>
        @if (hasFilters()) { <button type="button" class="btn ghost sm" (click)="clear()">Clear filters</button> }
      </form>
      <hs-async [loading]="loading() && !items().length" [error]="error()" [empty]="!loading() && !items().length" emptyText="No titles match your filters." (retry)="reload()">
        <div class="muted" style="margin-bottom:14px">{{ total() }} {{ total() === 1 ? 'title' : 'titles' }}</div>
        <div class="grid">@for (c of items(); track c.id) { <hs-card [content]="c" /> }</div>
        @if (items().length < total()) {
          <div class="pager"><button class="btn ghost" type="button" (click)="more()" [disabled]="loading()">{{ loading() ? 'Loading…' : 'Load more' }}</button></div>
        }
      </hs-async>
    </div>
  `,
})
export class BrowseComponent {
  private api = inject(Api);
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  readonly categories = Object.entries(CATEGORY_LABELS);
  form = this.fb.nonNullable.group({ q: '', genre: '', language: '', category: '', sort: 'newest' });
  facets = signal<Facets | null>(null);
  items = signal<Content[]>([]);
  total = signal(0);
  page = signal(1);
  loading = signal(true);
  error = signal<string | null>(null);

  constructor() {
    this.api.facets().subscribe({ next: (f) => this.facets.set(f), error: () => undefined });
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe((p) => {
      this.form.patchValue(Object.fromEntries(KEYS.map((k) => [k, p.get(k) ?? (k === 'sort' ? 'newest' : '')])), { emitEvent: false });
      this.reload();
    });
    this.form.valueChanges.pipe(debounceTime(300), distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)), takeUntilDestroyed(this.destroyRef)).subscribe((v) => {
      const queryParams: Record<string, string> = {};
      for (const k of KEYS) if (v[k] && !(k === 'sort' && v[k] === 'newest')) queryParams[k] = v[k] as string;
      this.router.navigate([], { queryParams, replaceUrl: true });
    });
  }

  heading(): string {
    const c = this.form.controls.category.value;
    return c ? CATEGORY_LABELS[c] : this.form.controls.q.value ? `Results for "${this.form.controls.q.value}"` : 'Browse all';
  }
  hasFilters(): boolean { return !!(this.form.value.q || this.form.value.genre || this.form.value.language || this.form.value.category); }
  clear(): void { this.router.navigate([], { queryParams: {} }); }
  reload(): void { this.page.set(1); this.fetch(true); }
  more(): void { this.page.update((p) => p + 1); this.fetch(false); }

  private fetch(replace: boolean): void {
    const v = this.form.getRawValue();
    this.loading.set(true);
    this.error.set(null);
    this.api.listContent({ q: v.q.trim(), genre: v.genre, language: v.language, category: v.category, sort: v.sort, page: this.page(), page_size: 24 }).subscribe({
      next: (r) => { this.items.set(replace ? r.items : [...this.items(), ...r.items]); this.total.set(r.total); this.loading.set(false); },
      error: (e) => { this.error.set(errMsg(e, 'Could not load titles.')); this.loading.set(false); },
    });
  }
}
