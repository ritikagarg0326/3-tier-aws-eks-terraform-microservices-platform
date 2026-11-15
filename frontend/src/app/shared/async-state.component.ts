import { Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

/** Standard loading / error / empty wrapper so every page handles all three states the same way. */
@Component({
  selector: 'hs-async',
  standalone: true,
  imports: [MatProgressSpinnerModule, MatButtonModule],
  template: `
    @if (loading()) {
      <div class="state"><mat-spinner diameter="40" /><span>Loading…</span></div>
    } @else if (error()) {
      <div class="state error" role="alert">
        <span>{{ error() }}</span>
        <button mat-stroked-button (click)="retry.emit()">Try again</button>
      </div>
    } @else if (empty()) {
      <div class="state muted">{{ emptyText() }}</div>
    } @else {
      <ng-content />
    }
  `,
})
export class AsyncStateComponent {
  loading = input(false);
  error = input<string | null>(null);
  empty = input(false);
  emptyText = input('Nothing to show here yet.');
  retry = output<void>();
}
