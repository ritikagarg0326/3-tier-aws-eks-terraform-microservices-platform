import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Api } from '../core/api.service';
import { Content } from '../core/models';
import { WatchlistStore } from '../core/watchlist.store';
import { errMsg } from '../core/util';
import { AsyncStateComponent } from '../shared/async-state.component';
import { PosterCardComponent } from '../shared/poster-card.component';

@Component({
  selector: 'hs-watchlist',
  standalone: true,
  imports: [RouterLink, AsyncStateComponent, PosterCardComponent],
  template: `
    <div class="page">
      <h1 class="page-title">My watchlist</h1>
      <hs-async [loading]="loading()" [error]="error()" [empty]="!loading() && !visible().length" emptyText="Your watchlist is empty. Tap + on any title to save it for later." (retry)="load()">
        <div class="grid">@for (c of visible(); track c.id) { <hs-card [content]="c" /> }</div>
      </hs-async>
      @if (!loading() && !visible().length && !error()) { <div class="pager"><a class="btn" routerLink="/browse">Browse titles</a></div> }
    </div>
  `,
})
export class WatchlistComponent {
  private api = inject(Api);
  private store = inject(WatchlistStore);
  loading = signal(true);
  error = signal<string | null>(null);
  items = signal<Content[]>([]);
  /** Titles removed via the card's toggle disappear immediately without a reload. */
  visible = computed(() => this.items().filter((c) => !this.store.loaded() || this.store.ids().has(c.id)));

  constructor() { this.load(); }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.watchlist(1, 100).subscribe({
      next: (page) => {
        const order = page.items.map((i) => i.content_id);
        if (!order.length) { this.items.set([]); this.loading.set(false); return; }
        this.api.listContent({ ids: order, page_size: 100 }).subscribe({
          next: (r) => { this.items.set(r.items.slice().sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id))); this.loading.set(false); },
          error: (e) => { this.error.set(errMsg(e)); this.loading.set(false); },
        });
      },
      error: (e) => { this.error.set(errMsg(e)); this.loading.set(false); },
    });
  }
}
