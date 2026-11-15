import { Component, computed, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { catchError, forkJoin, of } from 'rxjs';
import { Api } from '../core/api.service';
import { CATEGORY_SINGULAR, Content, HistoryEntry, MediaKind, MediaAsset } from '../core/models';
import { WatchlistStore } from '../core/watchlist.store';
import { errMsg, formatClock, formatDuration, gradientFor, mediaUrl } from '../core/util';
import { AsyncStateComponent } from '../shared/async-state.component';
import { ContentRowComponent } from '../shared/content-row.component';

@Component({
  selector: 'hs-detail',
  standalone: true,
  imports: [RouterLink, MatIconModule, AsyncStateComponent, ContentRowComponent],
  template: `
    <hs-async [loading]="loading()" [error]="error()" (retry)="load()">
      @if (content(); as c) {
        <div class="page">
          <div class="detail">
            <div class="poster-lg">
              @if (!posterFailed()) { <img [src]="poster()" [alt]="c.title" (error)="posterFailed.set(true)" /> }
              @else { <div class="fallback" [style.background]="gradient()">{{ c.title }}</div> }
            </div>
            <div>
              <h1>{{ c.title }}</h1>
              <div class="facts">
                <span class="chip">{{ category() }}</span><span class="chip">{{ c.release_year }}</span><span class="chip">{{ duration() }}</span>
                <span class="chip">{{ c.maturity_rating }}</span><span class="chip">{{ c.genre }}</span><span class="chip">{{ c.language }}</span>
              </div>
              <p class="desc">{{ c.description }}</p>
              <div class="actions">
                @if (hasVideo()) {
                  <a class="btn" [routerLink]="['/watch', c.id]"><mat-icon>play_arrow</mat-icon>{{ resumeLabel() }}</a>
                } @else {
                  <button class="btn" disabled><mat-icon>schedule</mat-icon>Video coming soon</button>
                }
                <button class="btn ghost" type="button" (click)="store.toggle(c.id)"><mat-icon>{{ inList() ? 'check' : 'add' }}</mat-icon>{{ inList() ? 'In your watchlist' : 'Add to watchlist' }}</button>
              </div>
              @if (history(); as h) {
                @if (!h.completed && h.position_seconds > 5) { <div class="resume">You stopped at {{ clock(h.position_seconds) }} of {{ clock(h.duration_seconds) }}.</div> }
                @if (h.completed) { <div class="resume">You've finished this title.</div> }
              }
            </div>
          </div>
        </div>
        <hs-row title="More like this" [items]="similar()" link="/browse" [query]="{ genre: c.genre }" />
      }
    </hs-async>
  `,
})
export class DetailComponent {
  private api = inject(Api);
  readonly store = inject(WatchlistStore);
  id = input.required<string>();
  loading = signal(true);
  error = signal<string | null>(null);
  content = signal<Content | null>(null);
  media = signal<Partial<Record<MediaKind, MediaAsset>>>({});
  history = signal<HistoryEntry | null>(null);
  similar = signal<Content[]>([]);
  posterFailed = signal(false);
  hasVideo = computed(() => !!this.media().video);
  inList = computed(() => this.store.ids().has(Number(this.id())));
  poster = computed(() => mediaUrl(Number(this.id()), 'poster'));
  gradient = computed(() => gradientFor(Number(this.id())));
  category = computed(() => CATEGORY_SINGULAR[this.content()?.category ?? 'other']);
  duration = computed(() => formatDuration(this.content()?.duration_minutes ?? 0));
  resumeLabel = computed(() => { const h = this.history(); return h && !h.completed && h.position_seconds > 5 ? 'Resume' : h?.completed ? 'Watch again' : 'Watch now'; });
  clock = formatClock;

  constructor() { effect(() => { this.id(); this.load(); }, { allowSignalWrites: true }); }

  load(): void {
    const id = Number(this.id());
    this.loading.set(true);
    this.error.set(null);
    this.posterFailed.set(false);
    forkJoin({
      content: this.api.getContent(id),
      media: this.api.mediaFor(id).pipe(catchError(() => of({}))),
      history: this.api.historyFor(id).pipe(catchError(() => of(null))),
    }).subscribe({
      next: (r) => {
        this.content.set(r.content);
        this.media.set(r.media);
        this.history.set(r.history);
        this.loading.set(false);
        this.api.listContent({ genre: r.content.genre, page_size: 13 }).subscribe({ next: (p) => this.similar.set(p.items.filter((x) => x.id !== id).slice(0, 12)), error: () => this.similar.set([]) });
      },
      error: (e) => { this.error.set(e?.status === 404 ? 'This title does not exist or was removed.' : errMsg(e)); this.loading.set(false); },
    });
  }
}
