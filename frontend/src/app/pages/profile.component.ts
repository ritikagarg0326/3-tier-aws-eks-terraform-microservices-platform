import { Component, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Api } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { Profile } from '../core/models';
import { errMsg } from '../core/util';
import { AsyncStateComponent } from '../shared/async-state.component';

const LANGUAGES = ['English', 'Hindi', 'Tamil', 'Telugu', 'Kannada', 'Malayalam', 'Bengali', 'Marathi'];
const COLORS = ['#1f80e0', '#e0457b', '#2fb56d', '#e08a1f', '#8a5cf6', '#14b8c4'];
const pwMatch = (g: AbstractControl): ValidationErrors | null => (g.get('next')?.value === g.get('confirm')?.value ? null : { mismatch: true });

@Component({
  selector: 'hs-profile',
  standalone: true,
  imports: [ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatSelectModule, AsyncStateComponent],
  template: `
    <div class="page">
      <h1 class="page-title">My profile</h1>
      <hs-async [loading]="loading()" [error]="error()" (retry)="load()">
        @if (profile(); as p) {
          <div class="two-col">
            <section class="panel">
              <div style="display:flex;align-items:center;gap:16px;margin-bottom:18px">
                <div class="avatar" style="width:64px;height:64px;border-radius:50%;display:grid;place-items:center;font-size:28px;font-weight:700" [style.background]="form.controls.avatar_color.value">{{ form.controls.display_name.value.charAt(0).toUpperCase() || '?' }}</div>
                <div><strong>{{ p.username }}</strong><br /><span class="muted">{{ p.email }} · {{ p.role === 'admin' ? 'Administrator' : 'Viewer' }}</span></div>
              </div>
              @if (saved()) { <div class="ok-banner">Profile saved.</div> }
              @if (saveError()) { <div class="err-banner" role="alert">{{ saveError() }}</div> }
              <form [formGroup]="form" (ngSubmit)="save()" novalidate>
                <mat-form-field appearance="outline"><mat-label>Display name</mat-label><input matInput formControlName="display_name" maxlength="60" />
                  @if (form.controls.display_name.invalid && form.controls.display_name.touched) { <mat-error>Display name is required</mat-error> }</mat-form-field>
                <mat-form-field appearance="outline"><mat-label>Bio</mat-label><textarea matInput rows="3" formControlName="bio" maxlength="500"></textarea></mat-form-field>
                <mat-form-field appearance="outline"><mat-label>Preferred language</mat-label>
                  <mat-select formControlName="preferred_language">@for (l of languages; track l) { <mat-option [value]="l">{{ l }}</mat-option> }</mat-select></mat-form-field>
                <div style="margin:0 0 18px"><div class="muted" style="margin-bottom:8px;font-size:13px">Avatar colour</div>
                  <div style="display:flex;gap:10px">@for (c of colors; track c) { <button type="button" (click)="form.controls.avatar_color.setValue(c)" [attr.aria-label]="'Colour ' + c" [style.background]="c" [style.outline]="form.controls.avatar_color.value === c ? '2px solid #fff' : 'none'" style="width:30px;height:30px;border-radius:50%;border:0;cursor:pointer"></button> }</div></div>
                <button class="btn" type="submit" [disabled]="saving()">{{ saving() ? 'Saving…' : 'Save profile' }}</button>
              </form>
            </section>
            <section class="panel">
              <h2 style="font-size:18px;margin-bottom:14px">Change password</h2>
              @if (pwOk()) { <div class="ok-banner">Password changed. Other devices have been signed out.</div> }
              @if (pwError()) { <div class="err-banner" role="alert">{{ pwError() }}</div> }
              <form [formGroup]="pwForm" (ngSubmit)="changePassword()" novalidate>
                <mat-form-field appearance="outline"><mat-label>Current password</mat-label><input matInput type="password" formControlName="current" autocomplete="current-password" /></mat-form-field>
                <mat-form-field appearance="outline"><mat-label>New password</mat-label><input matInput type="password" formControlName="next" autocomplete="new-password" />
                  <mat-hint>At least 8 characters with a letter and a digit</mat-hint>
                  @if (pwForm.controls.next.invalid && pwForm.controls.next.touched) { <mat-error>Min 8 characters, including a letter and a digit</mat-error> }</mat-form-field>
                <mat-form-field appearance="outline"><mat-label>Confirm new password</mat-label><input matInput type="password" formControlName="confirm" autocomplete="new-password" />
                  @if (pwForm.hasError('mismatch') && pwForm.controls.confirm.touched) { <mat-error>Passwords do not match</mat-error> }</mat-form-field>
                <button class="btn" type="submit" [disabled]="pwSaving()">{{ pwSaving() ? 'Updating…' : 'Update password' }}</button>
              </form>
            </section>
          </div>
        }
      </hs-async>
    </div>
  `,
})
export class ProfileComponent {
  private api = inject(Api);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private auth = inject(AuthService);
  readonly languages = LANGUAGES;
  readonly colors = COLORS;
  loading = signal(true);
  error = signal<string | null>(null);
  profile = signal<Profile | null>(null);
  saving = signal(false);
  saved = signal(false);
  saveError = signal<string | null>(null);
  pwSaving = signal(false);
  pwOk = signal(false);
  pwError = signal<string | null>(null);
  form = this.fb.nonNullable.group({ display_name: ['', [Validators.required, Validators.maxLength(60)]], bio: '', preferred_language: 'English', avatar_color: '#1f80e0' });
  pwForm = this.fb.nonNullable.group(
    { current: ['', Validators.required], next: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(72), (c: AbstractControl) => (/[A-Za-z]/.test(c.value) && /\d/.test(c.value) ? null : { weak: true })]], confirm: ['', Validators.required] },
    { validators: pwMatch },
  );

  constructor() { this.load(); }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.profile().subscribe({
      next: (p) => { this.profile.set(p); this.form.reset({ display_name: p.display_name, bio: p.bio ?? '', preferred_language: p.preferred_language, avatar_color: p.avatar_color }); this.loading.set(false); },
      error: (e) => { this.error.set(errMsg(e, 'Could not load your profile.')); this.loading.set(false); },
    });
  }

  save(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving.set(true); this.saved.set(false); this.saveError.set(null);
    const v = this.form.getRawValue();
    this.api.updateProfile({ ...v, bio: v.bio.trim() || null }).subscribe({
      next: (p) => { this.profile.set(p); this.saving.set(false); this.saved.set(true); },
      error: (e) => { this.saveError.set(errMsg(e)); this.saving.set(false); },
    });
  }

  changePassword(): void {
    if (this.pwForm.invalid) { this.pwForm.markAllAsTouched(); return; }
    this.pwSaving.set(true); this.pwOk.set(false); this.pwError.set(null);
    const { current, next } = this.pwForm.getRawValue();
    this.api.changePassword(current, next).subscribe({
      next: () => {
        this.pwSaving.set(false); this.pwOk.set(true); this.pwForm.reset();
        // all refresh tokens were revoked server-side; sign in again to obtain a fresh pair
        this.snack.open('Password updated. Please sign in again.', undefined, { duration: 3000 });
        setTimeout(() => this.auth.logout(true), 1500);
      },
      error: (e) => { this.pwError.set(errMsg(e)); this.pwSaving.set(false); },
    });
  }
}
