import { Component, DestroyRef, ElementRef, effect, inject, input, signal, viewChild } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { catchError, forkJoin, of } from 'rxjs';
import { Api } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { Content } from '../core/models';
import { errMsg, formatClock, mediaUrl } from '../core/util';
import { AsyncStateComponent } from '../shared/async-state.component';

const SAVE_EVERY_MS = 10_000;

@Component({
  selector: 'hs-watch',
  standalone: true,
  imports: [RouterLink, MatIconModule, AsyncStateComponent],
  template: `
    <hs-async [loading]="loading()" [error]="error()" (retry)="load()">
      @if (content(); as c) {
        <div class="player-page">
          <a class="muted" [routerLink]="['/title', c.id]" style="display:inline-flex;align-items:center;gap:4px;margin-bottom:10px"><mat-icon>arrow_back</mat-icon>Back to details</a>
          <div class="stage">
            <video #video [src]="src()" [poster]="poster()" controls autoplay playsinline preload="metadata"
              (loadedmetadata)="onMeta()" (timeupdate)="onTime()" (pause)="save()" (ended)="save()" (play)="startTimer()" (error)="onError()"></video>
          </div>
          <div class="controls">
            <button class="btn ghost sm" type="button" (click)="skip(-10)"><mat-icon>replay_10</mat-icon>10s</button>
            <button class="btn ghost sm" type="button" (click)="skip(10)"><mat-icon>forward_10</mat-icon>10s</button>
            <label class="muted">Speed
              <select (change)="speed($any($event.target).value)" aria-label="Playback speed">
                @for (s of speeds; track s) { <option [value]="s" [selected]="s === 1">{{ s }}x</option> }
              </select>
            </label>
            @if (resumed()) { <span class="chip">Resumed from {{ clock(resumed()) }}</span> }
            @if (playError()) { <span class="err-banner" style="margin:0">{{ playError() }}</span> }
          </div>
          <div class="info"><h1>{{ c.title }}</h1><p>{{ c.description }}</p></div>
        </div>
      }
    </hs-async>
  `,
})
export class WatchComponent {
  private api = inject(Api);
  private auth = inject(AuthService);
  private destroyRef = inject(DestroyRef);
  id = input.required<string>();
  videoEl = viewChild<ElementRef<HTMLVideoElement>>('video');
  loading = signal(true);
  error = signal<string | null>(null);
  content = signal<Content | null>(null);
  src = signal('');
  poster = signal('');
  resumed = signal(0);
  playError = signal<string | null>(null);
  readonly speeds = [0.5, 0.75, 1, 1.25, 1.5, 2];
  clock = formatClock;
  private resumeAt = 0;
  private timer?: ReturnType<typeof setInterval>;
  private lastSaved = -1;
  private retried = false;

  constructor() {
    effect(() => { this.id(); this.load(); }, { allowSignalWrites: true });
    const flush = () => this.flushKeepalive();
    window.addEventListener('pagehide', flush);
    this.destroyRef.onDestroy(() => { window.removeEventListener('pagehide', flush); this.stopTimer(); this.save(); });
  }

  load(): void {
    const id = Number(this.id());
    this.loading.set(true);
    this.error.set(null);
    this.retried = false;
    forkJoin({
      content: this.api.getContent(id),
      history: this.api.historyFor(id).pipe(catchError(() => of(null))),
      token: this.api.streamToken(id),
    }).subscribe({
      next: ({ content, history, token }) => {
        this.content.set(content);
        this.resumeAt = history && !history.completed && history.position_seconds > 5 ? history.position_seconds : 0;
        this.poster.set(mediaUrl(id, 'thumbnail'));
        this.src.set(this.streamUrl(id, token.token));
        this.loading.set(false);
      },
      error: (e) => { this.error.set(e?.status === 404 ? 'No video has been uploaded for this title yet.' : errMsg(e, 'Could not start playback.')); this.loading.set(false); },
    });
  }

  private streamUrl(id: number, token: string) { return `/api/videos/media/${id}/video?stream_token=${encodeURIComponent(token)}`; }

  onMeta(): void {
    const v = this.videoEl()?.nativeElement;
    if (v && this.resumeAt > 0 && this.resumeAt < v.duration - 5) { v.currentTime = this.resumeAt; this.resumed.set(this.resumeAt); }
    this.resumeAt = 0;
  }
  onTime(): void { if (this.resumed() && (this.videoEl()?.nativeElement.currentTime ?? 0) > 0) setTimeout(() => this.resumed.set(0), 4000); }
  skip(s: number): void { const v = this.videoEl()?.nativeElement; if (v) v.currentTime = Math.max(0, Math.min(v.duration || 0, v.currentTime + s)); }
  speed(v: string): void { const el = this.videoEl()?.nativeElement; if (el) el.playbackRate = Number(v); }

  /** The stream token may have expired during a very long session: fetch a new one once and continue. */
  onError(): void {
    const id = Number(this.id());
    const v = this.videoEl()?.nativeElement;
    if (!this.retried && v) {
      this.retried = true;
      this.resumeAt = v.currentTime;
      this.api.streamToken(id).subscribe({ next: (t) => this.src.set(this.streamUrl(id, t.token)), error: (e) => this.playError.set(errMsg(e, 'Playback failed.')) });
    } else {
      this.playError.set('This video cannot be played in your browser (supported: MP4/H.264 or WebM).');
    }
  }

  startTimer(): void { if (!this.timer) this.timer = setInterval(() => this.save(), SAVE_EVERY_MS); }
  private stopTimer(): void { if (this.timer) { clearInterval(this.timer); this.timer = undefined; } }

  save(): void {
    const v = this.videoEl()?.nativeElement;
    if (!v || !isFinite(v.duration) || v.duration <= 0) return;
    if (v.paused) this.stopTimer();
    const pos = Math.floor(v.currentTime);
    if (pos === this.lastSaved) return;
    this.lastSaved = pos;
    this.api.saveProgress(Number(this.id()), v.currentTime, v.duration).subscribe({ error: () => undefined });
  }

  private flushKeepalive(): void {
    const v = this.videoEl()?.nativeElement;
    const token = this.auth.accessToken;
    if (!v || !token || !isFinite(v.duration) || v.duration <= 0) return;
    fetch(`/api/history/${this.id()}`, { method: 'PUT', keepalive: true, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ position_seconds: v.currentTime, duration_seconds: v.duration }) }).catch(() => undefined);
  }
}
