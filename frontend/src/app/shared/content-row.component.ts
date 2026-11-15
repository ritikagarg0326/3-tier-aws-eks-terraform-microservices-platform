import { Component, ElementRef, input, viewChild } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { Content } from '../core/models';
import { PosterCardComponent } from './poster-card.component';

@Component({
  selector: 'hs-row',
  standalone: true,
  imports: [PosterCardComponent, RouterLink, MatIconModule],
  template: `
    @if (items().length) {
      <section class="rail">
        <header>
          <h2>{{ title() }}</h2>
          @if (link()) { <a [routerLink]="link()" [queryParams]="query()">See all <mat-icon>chevron_right</mat-icon></a> }
        </header>
        <div class="rail-wrap">
          <button class="nav left" type="button" (click)="scroll(-1)" aria-label="Scroll left"><mat-icon>chevron_left</mat-icon></button>
          <div class="rail-track" #track>
            @for (c of items(); track c.id) { <hs-card [content]="c" [progress]="progressFor(c.id)" /> }
          </div>
          <button class="nav right" type="button" (click)="scroll(1)" aria-label="Scroll right"><mat-icon>chevron_right</mat-icon></button>
        </div>
      </section>
    }
  `,
})
export class ContentRowComponent {
  title = input.required<string>();
  items = input.required<Content[]>();
  link = input<string | null>(null);
  query = input<Record<string, string>>({});
  progress = input<Record<number, number>>({});
  private track = viewChild<ElementRef<HTMLElement>>('track');

  progressFor(id: number): number { return this.progress()[id] ?? 0; }

  scroll(dir: number): void {
    const el = this.track()?.nativeElement;
    el?.scrollBy({ left: dir * el.clientWidth * 0.85, behavior: 'smooth' });
  }
}
