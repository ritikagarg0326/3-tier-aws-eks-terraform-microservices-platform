import { Component, inject, input, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { AuthService } from '../core/auth.service';
import { errMsg } from '../core/util';

@Component({
  selector: 'hs-login',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, MatFormFieldModule, MatInputModule, MatIconModule, MatButtonModule],
  template: `
    <div class="auth-wrap">
      <div class="box">
        <div class="logo"><span class="logo-mark">▶</span>hotstar</div>
        <h1>Sign in</h1>
        <p class="lead">Watch movies, TV shows and web series.</p>
        @if (expired()) { <div class="err-banner" role="alert">Your session expired. Please sign in again.</div> }
        @if (error()) { <div class="err-banner" role="alert">{{ error() }}</div> }
        <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
          <mat-form-field appearance="outline">
            <mat-label>Email</mat-label>
            <input matInput type="email" formControlName="email" autocomplete="username" />
            @if (form.controls.email.touched && form.controls.email.invalid) { <mat-error>Enter a valid email address</mat-error> }
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Password</mat-label>
            <input matInput [type]="show() ? 'text' : 'password'" formControlName="password" autocomplete="current-password" />
            <button mat-icon-button matSuffix type="button" (click)="show.set(!show())" [attr.aria-label]="show() ? 'Hide password' : 'Show password'"><mat-icon>{{ show() ? 'visibility_off' : 'visibility' }}</mat-icon></button>
            @if (form.controls.password.touched && form.controls.password.invalid) { <mat-error>Password is required</mat-error> }
          </mat-form-field>
          <button class="btn" type="submit" [disabled]="loading()">{{ loading() ? 'Signing in…' : 'Sign in' }}</button>
        </form>
        <div class="alt">New to hotstar? <a routerLink="/register">Create an account</a></div>
      </div>
    </div>
  `,
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  returnUrl = input<string>();
  expired = input<string>();
  loading = signal(false);
  error = signal<string | null>(null);
  show = signal(false);
  form = this.fb.nonNullable.group({ email: ['', [Validators.required, Validators.email]], password: ['', Validators.required] });

  submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading.set(true);
    this.error.set(null);
    const { email, password } = this.form.getRawValue();
    this.auth.login(email.trim(), password).subscribe({
      next: () => {
        const url = this.returnUrl();
        this.router.navigateByUrl(url && url.startsWith('/') && !url.startsWith('//') ? url : '/');
      },
      error: (e) => { this.error.set(errMsg(e)); this.loading.set(false); },
    });
  }
}
