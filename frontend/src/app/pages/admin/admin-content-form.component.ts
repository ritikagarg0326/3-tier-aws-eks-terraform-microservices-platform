import { HttpEventType } from '@angular/common/http';
import { Component, computed, effect, inject, input, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Observable, concat, lastValueFrom, of } from 'rxjs';
import { Api } from '../../core/api.service';
import { CATEGORY_LABELS, Content, ContentInput, Facets, MediaAsset, MediaKind } from '../../core/models';
import { errMsg, formatBytes, mediaUrl } from '../../core/util';
import { AsyncStateComponent } from '../../shared/async-state.component';

interface Slot { kind: MediaKind; label: string; accept: string; hint: string; file: File | null; preview: string | null; progress: number; status: string; }
const RATINGS = ['U', 'U/A 7+', 'U/A 13+', 'U/A 16+', 'A'];

@Component({
  selector: 'hs-admin-content-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, MatFormFieldModule, MatInputModule, MatSelectModule, MatCheckboxModule, MatIconModule, AsyncStateComponent],
  template: `
    <div class="toolbar"><h1 class="page-title" style="margin:0">{{ editing() ? 'Edit content' : 'Add content' }}</h1><span class="spacer"></span><a class="btn ghost sm" routerLink="/admin/content">Back to list</a></div>
    <hs-async [loading]="loading()" [error]="loadError()" (retry)="init()">
      @if (error()) { <div class="err-banner" role="alert">{{ error() }}</div> }
      <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
        <section class="panel" style="margin-bottom:18px">
          <div class="form-grid">
            <mat-form-field appearance="outline" class="full"><mat-label>Title</mat-label><input matInput formControlName="title" maxlength="200" />
              @if (f.title.touched && f.title.invalid) { <mat-error>Title is required</mat-error> }</mat-form-field>
            <mat-form-field appearance="outline" class="full"><mat-label>Description</mat-label><textarea matInput rows="4" formControlName="description" maxlength="5000"></textarea>
              @if (f.description.touched && f.description.invalid) { <mat-error>Description is required</mat-error> }</mat-form-field>
            <mat-form-field appearance="outline"><mat-label>Category</mat-label>
              <mat-select formControlName="category">@for (c of categories; track c[0]) { <mat-option [value]="c[0]">{{ c[1] }}</mat-option> }</mat-select></mat-form-field>
            <mat-form-field appearance="outline"><mat-label>Genre</mat-label><input matInput formControlName="genre" list="genres" maxlength="50" />
              <datalist id="genres">@for (g of facets()?.genres ?? []; track g) { <option [value]="g"></option> }</datalist>
              @if (f.genre.touched && f.genre.invalid) { <mat-error>Genre is required</mat-error> }</mat-form-field>
            <mat-form-field appearance="outline"><mat-label>Language</mat-label><input matInput formControlName="language" list="languages" maxlength="50" />
              <datalist id="languages">@for (g of facets()?.languages ?? []; track g) { <option [value]="g"></option> }</datalist>
              @if (f.language.touched && f.language.invalid) { <mat-error>Language is required</mat-error> }</mat-form-field>
            <mat-form-field appearance="outline"><mat-label>Release year</mat-label><input matInput type="number" formControlName="release_year" />
              @if (f.release_year.touched && f.release_year.invalid) { <mat-error>Enter a year between 1888 and 2100</mat-error> }</mat-form-field>
            <mat-form-field appearance="outline"><mat-label>Duration (minutes)</mat-label><input matInput type="number" formControlName="duration_minutes" />
              @if (f.duration_minutes.touched && f.duration_minutes.invalid) { <mat-error>Enter a duration of 1-6000 minutes</mat-error> }</mat-form-field>
            <mat-form-field appearance="outline"><mat-label>Maturity rating</mat-label>
              <mat-select formControlName="maturity_rating">@for (r of ratings; track r) { <mat-option [value]="r">{{ r }}</mat-option> }</mat-select></mat-form-field>
            <div style="display:flex;align-items:center"><mat-checkbox formControlName="is_featured">Featured on home page</mat-checkbox></div>
          </div>
        </section>

        <section class="panel" style="margin-bottom:18px">
          <h2 style="font-size:17px;margin-bottom:4px">Media</h2>
          <p class="muted" style="margin:0 0 16px;font-size:13px">Posters/thumbnails: JPEG, PNG or WebP (max 10 MB). Video: MP4 (H.264/AAC recommended) or WebM. Files are validated by content, not by extension.</p>
          <div class="upload-grid">
            @for (s of slots(); track s.kind) {
              <div class="upload-box">
                <h4>{{ s.label }}</h4>
                @if (existing()[s.kind]; as a) {
                  <small>Current: {{ a.original_filename || a.kind }} · {{ size(a.size_bytes) }}</small>
                  @if (s.kind !== 'video') { <img class="preview" [src]="url(s.kind)" [alt]="s.label" /> }
                }
                <input type="file" [accept]="s.accept" (change)="pick(s, $event)" [attr.aria-label]="'Choose ' + s.label" />
                @if (s.preview) { <img class="preview" [src]="s.preview" alt="Selected preview" /> }
                @if (s.file) { <small>Selected: {{ s.file.name }} ({{ size(s.file.size) }})</small> }
                @if (s.progress > 0 || s.status) { <div class="progress-line"><span [style.width.%]="s.progress"></span></div><small>{{ s.status || s.progress + '%' }}</small> }
                @if (existing()[s.kind]) { <button class="btn danger sm" type="button" style="align-self:flex-start" (click)="removeMedia(s.kind)"><mat-icon>delete</mat-icon>Remove</button> }
                <small>{{ s.hint }}</small>
              </div>
            }
          </div>
        </section>

        <button class="btn" type="submit" [disabled]="saving()">{{ saving() ? (stage() || 'Saving…') : editing() ? 'Save changes' : 'Create content' }}</button>
      </form>
    </hs-async>
  `,
})
export class AdminContentFormComponent {
  private api = inject(Api);
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private snack = inject(MatSnackBar);
  id = input<string>();
  readonly categories = Object.entries(CATEGORY_LABELS);
  readonly ratings = RATINGS;
  editing = computed(() => !!this.id());
  loading = signal(true);
  loadError = signal<string | null>(null);
  error = signal<string | null>(null);
  saving = signal(false);
  stage = signal('');
  facets = signal<Facets | null>(null);
  existing = signal<Partial<Record<MediaKind, MediaAsset>>>({});
  bust = signal(Date.now());
  slots = signal<Slot[]>([
    { kind: 'poster', label: 'Poster', accept: 'image/jpeg,image/png,image/webp', hint: 'Portrait 2:3 works best', file: null, preview: null, progress: 0, status: '' },
    { kind: 'thumbnail', label: 'Thumbnail / hero image', accept: 'image/jpeg,image/png,image/webp', hint: 'Used as the hero backdrop and video poster', file: null, preview: null, progress: 0, status: '' },
    { kind: 'video', label: 'Video', accept: 'video/mp4,video/webm', hint: 'Large files upload in a single streaming request', file: null, preview: null, progress: 0, status: '' },
  ]);
  form = this.fb.nonNullable.group({
    title: ['', [Validators.required, Validators.maxLength(200)]],
    description: ['', [Validators.required, Validators.maxLength(5000)]],
    genre: ['', [Validators.required, Validators.maxLength(50)]],
    language: ['', [Validators.required, Validators.maxLength(50)]],
    release_year: [new Date().getFullYear(), [Validators.required, Validators.min(1888), Validators.max(2100)]],
    duration_minutes: [90, [Validators.required, Validators.min(1), Validators.max(6000)]],
    category: ['movie' as Content['category'], Validators.required],
    maturity_rating: ['U/A 13+', Validators.required],
    is_featured: false,
  });
  get f() { return this.form.controls; }
  size = formatBytes;
  url = (k: MediaKind) => mediaUrl(Number(this.id()), k, this.bust());

  constructor() { effect(() => { this.id(); this.init(); }, { allowSignalWrites: true }); }

  init(): void {
    this.loading.set(true);
    this.loadError.set(null);
    this.api.facets().subscribe({ next: (f) => this.facets.set(f), error: () => undefined });
    const id = this.id();
    if (!id) { this.loading.set(false); return; }
    this.api.getContent(Number(id)).subscribe({
      next: (c) => {
        this.form.reset({ title: c.title, description: c.description, genre: c.genre, language: c.language, release_year: c.release_year, duration_minutes: c.duration_minutes, category: c.category, maturity_rating: c.maturity_rating, is_featured: c.is_featured });
        this.api.mediaFor(c.id).subscribe({ next: (m) => this.existing.set(m), error: () => undefined });
        this.loading.set(false);
      },
      error: (e) => { this.loadError.set(e?.status === 404 ? 'Content not found.' : errMsg(e)); this.loading.set(false); },
    });
  }

  pick(slot: Slot, ev: Event): void {
    const file = (ev.target as HTMLInputElement).files?.[0] ?? null;
    this.slots.update((list) => list.map((s) => {
      if (s !== slot) return s;
      if (s.preview) URL.revokeObjectURL(s.preview);
      return { ...s, file, preview: file && s.kind !== 'video' ? URL.createObjectURL(file) : null, progress: 0, status: '' };
    }));
  }

  async submit(): Promise<void> {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving.set(true);
    this.error.set(null);
    try {
      const body = this.form.getRawValue() as ContentInput;
      this.stage.set('Saving details…');
      const saved = this.editing() ? await lastValueFrom(this.api.updateContent(Number(this.id()), body)) : await lastValueFrom(this.api.createContent(body));
      for (const slot of this.slots().filter((s) => s.file)) {
        this.stage.set(`Uploading ${slot.label.toLowerCase()}…`);
        await this.upload(saved.id, slot);
      }
      this.snack.open(this.editing() ? 'Changes saved' : 'Content created', undefined, { duration: 2500 });
      this.router.navigate(['/admin/content']);
    } catch (e) {
      this.error.set(errMsg(e));
    } finally {
      this.saving.set(false);
      this.stage.set('');
    }
  }

  private upload(contentId: number, slot: Slot): Promise<unknown> {
    const patch = (p: Partial<Slot>) => this.slots.update((l) => l.map((s) => (s.kind === slot.kind ? { ...s, ...p } : s)));
    return new Promise((resolve, reject) => {
      this.api.upload(contentId, slot.kind, slot.file as File).subscribe({
        next: (ev) => {
          if (ev.type === HttpEventType.UploadProgress && ev.total) patch({ progress: Math.round((ev.loaded / ev.total) * 100) });
          if (ev.type === HttpEventType.Response) { patch({ progress: 100, status: 'Uploaded ✓', file: null }); resolve(ev.body); }
        },
        error: (e) => { patch({ status: 'Failed' }); reject(new Error(`${slot.label}: ${errMsg(e)}`)); },
      });
    }).catch((e) => { throw e instanceof Error ? Object.assign(new Error(e.message), { name: 'UploadError' }) : e; });
  }

  removeMedia(kind: MediaKind): void {
    const id = Number(this.id());
    if (!id || !confirm(`Remove the current ${kind}?`)) return;
    this.api.deleteMedia(id, kind).subscribe({
      next: () => this.existing.update((m) => { const c = { ...m }; delete c[kind]; return c; }),
      error: (e) => this.snack.open(errMsg(e), 'Dismiss', { duration: 4000 }),
    });
  }
}
