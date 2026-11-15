import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'hs-not-found',
  standalone: true,
  imports: [RouterLink],
  template: `<div class="state"><h1>404</h1><p>We couldn't find that page.</p><a class="btn" routerLink="/">Back to home</a></div>`,
})
export class NotFoundComponent {}
