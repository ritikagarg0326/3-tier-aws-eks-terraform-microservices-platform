import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { catchError, forkJoin, of, switchMap } from 'rxjs';
import { Api } from '../core/api.service';
import { CATEGORY_LABELS, CATEGORY_SINGULAR, Content, HistoryEntry, Page } from '../core/models';
import { errMsg, formatDuration, gradientFor, mediaUrl } from '../core/util';
import { AsyncStateComponent } from '../shared/async-state.component';
import { ContentRowComponent } from '../shared/content-row.component';
import { WatchlistStore } from '../core/watchlist.store';

interface Row { title: string; link: string; query: Record<string, string>; items: Content[]; }
const empty: Page<never> = { items: [], total: 0, page: 1, page_size: 0, pages: 0 };

@Component({
  selector: 'hs-home',
  standalone: true,
  imports: [RouterLink, MatIconModule, AsyncStateComponent, ContentRowComponent],
  template: `
    <hs-async [loading]="loading()" [error]="error()" [empty]="!loading() && !hero() && !rows().length" emptyText="No content has been published yet. An admin can add titles from the dashboard." (retry)="load()">
      @if (hero(); as h) {
        <section class="hero">
          <div class="bg" [style.background-image]="heroBg()"></div>
          <div class="inner">
            <div class="meta"><span class="chip">{{ categoryLabel(h) }}</span><span>{{ h.release_year }}</span><span>{{ duration(h) }}</span><span>{{ h.maturity_rating }}</span></div>
            <h1>{{ h.title }}</h1>
            <p class="desc">{{ h.description }}</p>
            <div class="meta">{{ h.genre }} · {{ h.language }}</div>
            <div class="actions">
              <a class="btn" [routerLink]="['/watch', h.id]"><mat-icon>play_arrow</mat-icon>Watch now</a>
              <a class="btn ghost" [routerLink]="['/title', h.id]"><mat-icon>info</mat-icon>More info</a>
              <button class="btn ghost" type="button" (click)="store.toggle(h.id)"><mat-icon>{{ store.ids().has(h.id) ? 'check' : 'add' }}</mat-icon>{{ store.ids().has(h.id) ? 'In watchlist' : 'Watchlist' }}</button>
            </div>
          </div>
        </section>
      }
      <hs-row title="Continue watching" [items]="continueItems()" [progress]="progress()" link="/history" />
      @for (r of rows(); track r.title) { <hs-row [title]="r.title" [items]="r.items" [link]="r.link" [query]="r.query" /> }
    </hs-async>
  `,
})
export class HomeComponent {
  private api = inject(Api);
  readonly store = inject(WatchlistStore);
  loading = signal(true);
  error = signal<string | null>(null);
  hero = signal<Content | null>(null);
  rows = signal<Row[]>([]);
  continueItems = signal<Content[]>([]);
  progress = signal<Record<number, number>>({});
  heroBg = computed(() => {
    const h = this.hero();
    return h ? `url(${mediaUrl(h.id, 'thumbnail')}), ${gradientFor(h.id)}` : '';
  });

  constructor() { this.load(); }

  categoryLabel(c: Content) { return CATEGORY_SINGULAR[c.category]; }
  duration(c: Content) { return formatDuration(c.duration_minutes); }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    const q = (category: string) => this.api.listContent({ category, page_size: 16 });
    forkJoin({
      featured: this.api.listContent({ featured: true, page_size: 12 }),
      movie: q('movie'), tv_show: q('tv_show'), web_series: q('web_series'), other: q('other'),
      hist: this.api.history({ inProgress: true, pageSize: 12 }).pipe(catchError(() => of(empty as Page<HistoryEntry>))),
    })
      .pipe(switchMap((r) => (r.hist.items.length ? this.api.listContent({ ids: r.hist.items.map((h) => h.content_id), page_size: 12 }).pipe(catchError(() => of(empty as Page<Content>))) : of(empty as Page<Content>)).pipe(switchMap((cont) => of({ r, cont })))))
      .subscribe({
        next: ({ r, cont }) => {
          const order = r.hist.items.map((h) => h.content_id);
          this.continueItems.set(cont.items.slice().sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id)));
          this.progress.set(Object.fromEntries(r.hist.items.map((h) => [h.content_id, h.duration_seconds ? Math.min(100, (h.position_seconds / h.duration_seconds) * 100) : 0])));
          this.hero.set(r.featured.items[0] ?? r.movie.items[0] ?? r.tv_show.items[0] ?? r.web_series.items[0] ?? r.other.items[0] ?? null);
          const rows: Row[] = [];
          if (r.featured.items.length) rows.push({ title: 'Featured & trending', link: '/browse', query: {}, items: r.featured.items });
          for (const k of ['movie', 'tv_show', 'web_series', 'other'] as const) {
            if (r[k].items.length) rows.push({ title: CATEGORY_LABELS[k], link: '/browse', query: { category: k }, items: r[k].items });
          }
          this.rows.set(rows);
          this.loading.set(false);
        },
        error: (e) => { this.error.set(errMsg(e, 'Could not load the catalogue.')); this.loading.set(false); },
      });
  }
}
