import { HttpErrorResponse } from '@angular/common/http';
import { MediaKind } from './models';

/** Turn any HTTP failure into a human readable message (uses the platform's error envelope when present). */
export function errMsg(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) return 'Cannot reach the server. Check your connection and try again.';
    const e = err.error?.error;
    if (e?.details?.length) return e.details.map((d: { field: string; message: string }) => (d.field ? `${d.field}: ` : '') + d.message).join(' · ');
    if (e?.message) return e.message;
    if (err.status === 413) return 'The file is too large.';
    if (err.status === 429) return 'Too many attempts. Please wait a minute.';
  }
  return fallback;
}

export function errCode(err: unknown): string | undefined {
  return err instanceof HttpErrorResponse ? err.error?.error?.code : undefined;
}

export const mediaUrl = (id: number, kind: MediaKind, bust?: string | number) =>
  `/api/videos/media/${id}/${kind}${bust ? `?v=${bust}` : ''}`;

export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60), m = minutes % 60;
  return h ? `${h}h ${m ? m + 'm' : ''}`.trim() : `${m}m`;
}

export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return (h ? `${h}:${String(m).padStart(2, '0')}` : `${m}`) + `:${String(sec).padStart(2, '0')}`;
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1073741824) return `${(n / 1048576).toFixed(1)} MB`;
  return `${(n / 1073741824).toFixed(2)} GB`;
}

/** Deterministic gradient so posters without artwork still look good. */
export function gradientFor(id: number): string {
  const hue = (id * 47) % 360;
  return `linear-gradient(160deg, hsl(${hue} 65% 38%), hsl(${(hue + 40) % 360} 70% 14%))`;
}
