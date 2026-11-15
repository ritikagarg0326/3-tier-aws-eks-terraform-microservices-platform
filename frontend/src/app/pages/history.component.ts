import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Api } from '../core/api.service';
import { Content, HistoryEntry } from '../core/models';
import { errMsg, formatClock, gradientFor, mediaUrl } from '../core/util';
import { AsyncStateComponent } from '../shared/async-state.component';

interface Item { entry: HistoryEntry; content: Content; pct: number; failed: boolean; }

@Component({
  selector: 'hs-history',
  standalone: true,
  imports: [RouterLink, DatePipe, MatIconModule, AsyncStateComponent],
  template: `
    <div class="page">
      <div class="toolbar"><h1 class="page-title" style="margin:0">Watch history</h1><span class="spacer"></span>
        @if (items().length) { <button class="btn ghost sm" type="button" (click)="clear()"><mat-icon>delete_sweep</mat-icon>Clear history</button> }
      </div>
      <hs-async [loading]="loading()" [error]="error()" [empty]="!loading() && !items().length" emptyText="Nothing watched yet. Start a title and it will show up here." (retry)="load()">
        <div class="list">
          @for (i of items(); track i.entry.content_id) {
            <div class="row-item">
              <a class="thumb" [routerLink]="['/title', i.content.id]">
                @if (!i.failed) { <img [src]="poster(i.content.id)" [alt]="i.content.title" loading="lazy" (error)="i.failed = true" /> }
                @else { <div class="fallback" [style.background]="gradient(i.content.id)">{{ i.content.title.charAt(0) }}</div> }
              </a>
              <div>
                <a class="title" [routerLink]="['/title', i.content.id]">{{ i.content.title }}</a><br />
                <small>{{ i.entry.completed ? 'Finished' : clock(i.entry.position_seconds) + ' of ' + clock(i.entry.duration_seconds) }} · {{ i.entry.last_watched_at + 'Z' | date: 'medium' }}</small>
                <div class="bar"><span [style.width.%]="i.entry.completed ? 100 : i.pct"></span></div>
                <a class="btn sm" [routerLink]="['/watch', i.content.id]"><mat-icon>play_arrow</mat-icon>{{ i.entry.completed ? 'Watch again' : 'Resume' }}</a>
              </div>
              <button class="btn ghost sm" type="button" (click)="remove(i)" [attr.aria-label]="'Remove ' + i.content.title + ' from history'"><mat-icon>close</mat-icon></button>
            </div>
          }
        </div>
      </hs-async>
    </div>
  `,
})
export class HistoryComponent {
  private api = inject(Api);
  private snack = inject(MatSnackBar);
  loading = signal(true);
  error = signal<string | null>(null);
  items = signal<Item[]>([]);
  clock = formatClock;
  poster = (id: number) => mediaUrl(id, 'poster');
  gradient = gradientFor;

  constructor() { this.load(); }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.history({ pageSize: 100 }).subscribe({
      next: (page) => {
        const ids = page.items.map((h) => h.content_id);
        if (!ids.length) { this.items.set([]); this.loading.set(false); return; }
        this.api.listContent({ ids, page_size: 100 }).subscribe({
          next: (r) => {
            const byId = new Map(r.items.map((c) => [c.id, c]));
            this.items.set(page.items.filter((h) => byId.has(h.content_id)).map((h) => ({ entry: h, content: byId.get(h.content_id)!, pct: h.duration_seconds ? Math.min(100, (h.position_seconds / h.duration_seconds) * 100) : 0, failed: false })));
            this.loading.set(false);
          },
          error: (e) => { this.error.set(errMsg(e)); this.loading.set(false); },
        });
      },
      error: (e) => { this.error.set(errMsg(e)); this.loading.set(false); },
    });
  }

  remove(i: Item): void {
    this.api.removeHistory(i.entry.content_id).subscribe({
      next: () => this.items.update((list) => list.filter((x) => x !== i)),
      error: (e) => this.snack.open(errMsg(e), 'Dismiss', { duration: 4000 }),
    });
  }

  clear(): void {
    if (!confirm('Clear your entire watch history?')) return;
    this.api.clearHistory().subscribe({ next: () => this.items.set([]), error: (e) => this.snack.open(errMsg(e), 'Dismiss', { duration: 4000 }) });
  }
}
