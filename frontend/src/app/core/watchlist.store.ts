import { Injectable, inject, signal } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Observable } from 'rxjs';
import { Api } from './api.service';
import { errMsg } from './util';

/** Shared, optimistic watchlist state so every card shows the right "+" / "✓" without extra requests. */
@Injectable({ providedIn: 'root' })
export class WatchlistStore {
  private api = inject(Api);
  private snack = inject(MatSnackBar);
  readonly ids = signal<ReadonlySet<number>>(new Set());
  readonly loaded = signal(false);

  load(): void {
    this.api.watchlistIds().subscribe({ next: (ids) => { this.ids.set(new Set(ids)); this.loaded.set(true); }, error: () => this.ids.set(new Set()) });
  }
  reset(): void { this.ids.set(new Set()); this.loaded.set(false); }
  has(id: number): boolean { return this.ids().has(id); }

  toggle(id: number): void {
    const adding = !this.has(id);
    this.set(id, adding);
    const request$: Observable<unknown> = adding ? this.api.addToWatchlist(id) : this.api.removeFromWatchlist(id);
    request$.subscribe({
      next: () => this.snack.open(adding ? 'Added to your watchlist' : 'Removed from your watchlist', undefined, { duration: 1800 }),
      error: (e) => { this.set(id, !adding); this.snack.open(errMsg(e), 'Dismiss', { duration: 4000 }); },
    });
  }

  private set(id: number, present: boolean): void {
    const next = new Set(this.ids());
    present ? next.add(id) : next.delete(id);
    this.ids.set(next);
  }
}
