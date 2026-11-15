import { Component, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Content } from '../core/models';
import { WatchlistStore } from '../core/watchlist.store';
import { CATEGORY_SINGULAR } from '../core/models';
import { gradientFor, mediaUrl } from '../core/util';

@Component({
  selector: 'hs-card',
  standalone: true,
  imports: [RouterLink, MatIconModule, MatTooltipModule],
  template: `
    <article class="card">
      <a [routerLink]="['/title', content().id]" class="poster" [attr.aria-label]="content().title">
        @if (!failed()) {
          <img [src]="poster()" [alt]="content().title" loading="lazy" (error)="failed.set(true)" />
        } @else {
          <div class="fallback" [style.background]="gradient()"><span>{{ content().title }}</span></div>
        }
        <span class="badge">{{ categoryLabel() }}</span>
        @if (progress() > 0) { <span class="progress"><span [style.width.%]="progress()"></span></span> }
      </a>
      <div class="meta">
        <a [routerLink]="['/title', content().id]" class="title">{{ content().title }}</a>
        <button type="button" class="wl" (click)="store.toggle(content().id)" [matTooltip]="inList() ? 'Remove from watchlist' : 'Add to watchlist'" [attr.aria-pressed]="inList()" [attr.aria-label]="inList() ? 'Remove from watchlist' : 'Add to watchlist'">
          <mat-icon>{{ inList() ? 'check_circle' : 'add_circle_outline' }}</mat-icon>
        </button>
      </div>
      <div class="sub">{{ content().release_year }} · {{ content().language }} · {{ content().genre }}</div>
    </article>
  `,
})
export class PosterCardComponent {
  readonly store = inject(WatchlistStore);
  content = input.required<Content>();
  progress = input(0);
  failed = signal(false);
  poster = computed(() => mediaUrl(this.content().id, 'poster'));
  gradient = computed(() => gradientFor(this.content().id));
  categoryLabel = computed(() => CATEGORY_SINGULAR[this.content().category] ?? '');
  inList = computed(() => this.store.ids().has(this.content().id));
}
