import { Component, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AuthService } from '../core/auth.service';
import { errMsg } from '../core/util';

const strongPassword = (c: AbstractControl): ValidationErrors | null => {
  const v = (c.value as string) ?? '';
  return /[A-Za-z]/.test(v) && /\d/.test(v) ? null : { weak: true };
};
const matches = (g: AbstractControl): ValidationErrors | null =>
  g.get('password')?.value === g.get('confirm')?.value ? null : { mismatch: true };

@Component({
  selector: 'hs-register',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, MatFormFieldModule, MatInputModule],
  template: `
    <div class="auth-wrap">
      <div class="box">
        <div class="logo"><span class="logo-mark">▶</span>hotstar</div>
        <h1>Create your account</h1>
        <p class="lead">Free to join. Pick up where you left off on any device.</p>
        @if (error()) { <div class="err-banner" role="alert">{{ error() }}</div> }
        <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
          <mat-form-field appearance="outline">
            <mat-label>Email</mat-label>
            <input matInput type="email" formControlName="email" autocomplete="email" />
            @if (c.email.touched && c.email.invalid) { <mat-error>Enter a valid email address</mat-error> }
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Username</mat-label>
            <input matInput formControlName="username" autocomplete="username" />
            <mat-hint>3-30 characters: letters, digits, . _ -</mat-hint>
            @if (c.username.touched && c.username.invalid) { <mat-error>Use 3-30 letters, digits, '.', '_' or '-'</mat-error> }
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Password</mat-label>
            <input matInput type="password" formControlName="password" autocomplete="new-password" />
            <mat-hint>At least 8 characters with a letter and a digit</mat-hint>
            @if (c.password.touched && c.password.invalid) { <mat-error>Min 8 characters, including a letter and a digit</mat-error> }
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Confirm password</mat-label>
            <input matInput type="password" formControlName="confirm" autocomplete="new-password" />
            @if (c.confirm.touched && form.hasError('mismatch')) { <mat-error>Passwords do not match</mat-error> }
          </mat-form-field>
          <button class="btn" type="submit" [disabled]="loading()">{{ loading() ? 'Creating account…' : 'Create account' }}</button>
        </form>
        <div class="alt">Already have an account? <a routerLink="/login">Sign in</a></div>
      </div>
    </div>
  `,
})
export class RegisterComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  loading = signal(false);
  error = signal<string | null>(null);
  form = this.fb.nonNullable.group(
    {
      email: ['', [Validators.required, Validators.email]],
      username: ['', [Validators.required, Validators.pattern(/^[A-Za-z0-9_.-]{3,30}$/)]],
      password: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(72), strongPassword]],
      confirm: ['', Validators.required],
    },
    { validators: matches },
  );
  get c() { return this.form.controls; }

  submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading.set(true);
    this.error.set(null);
    const { email, username, password } = this.form.getRawValue();
    this.auth.register(email.trim(), username.trim(), password).subscribe({
      next: () => this.router.navigateByUrl('/'),
      error: (e) => { this.error.set(errMsg(e)); this.loading.set(false); },
    });
  }
}
