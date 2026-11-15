import { HttpClient, HttpEvent, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
  AuthStats, Content, ContentInput, ContentQuery, ContentStats, Facets, HistoryEntry, MediaAsset, MediaKind, Page,
  Profile, ProfileInput, User, WatchlistEntry,
} from './models';

/** Typed client for every backend endpoint. All calls go through the API gateway (/api/...). */
@Injectable({ providedIn: 'root' })
export class Api {
  private http = inject(HttpClient);

  // ---- content
  listContent(q: ContentQuery = {}): Observable<Page<Content>> {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(q)) {
      if (v === undefined || v === null || v === '') continue;
      params = params.set(k, Array.isArray(v) ? v.join(',') : String(v));
    }
    return this.http.get<Page<Content>>('/api/content', { params });
  }
  getContent(id: number) { return this.http.get<Content>(`/api/content/${id}`); }
  facets() { return this.http.get<Facets>('/api/content/facets'); }
  createContent(body: ContentInput) { return this.http.post<Content>('/api/content', body); }
  updateContent(id: number, body: ContentInput) { return this.http.put<Content>(`/api/content/${id}`, body); }
  deleteContent(id: number) { return this.http.delete<void>(`/api/content/${id}`); }
  contentStats() { return this.http.get<ContentStats>('/api/content/admin/stats'); }

  // ---- media
  mediaFor(id: number) { return this.http.get<Partial<Record<MediaKind, MediaAsset>>>(`/api/videos/media/${id}`); }
  streamToken(id: number) { return this.http.post<{ token: string; expires_in: number }>(`/api/videos/stream-token/${id}`, {}); }
  upload(id: number, kind: MediaKind, file: File): Observable<HttpEvent<MediaAsset>> {
    const form = new FormData();
    form.append('file', file, file.name);
    return this.http.post<MediaAsset>(`/api/videos/media/${id}/${kind}`, form, { reportProgress: true, observe: 'events' });
  }
  deleteMedia(id: number, kind: MediaKind) { return this.http.delete<void>(`/api/videos/media/${id}/${kind}`); }

  // ---- watchlist
  watchlist(page = 1, pageSize = 100) { return this.http.get<Page<WatchlistEntry>>('/api/watchlist', { params: { page, page_size: pageSize } }); }
  watchlistIds() { return this.http.get<number[]>('/api/watchlist/ids'); }
  addToWatchlist(contentId: number) { return this.http.post<WatchlistEntry>('/api/watchlist', { content_id: contentId }); }
  removeFromWatchlist(contentId: number) { return this.http.delete<void>(`/api/watchlist/${contentId}`); }

  // ---- history
  history(opts: { inProgress?: boolean; page?: number; pageSize?: number } = {}) {
    return this.http.get<Page<HistoryEntry>>('/api/history', { params: { in_progress: !!opts.inProgress, page: opts.page ?? 1, page_size: opts.pageSize ?? 50 } });
  }
  historyFor(contentId: number) { return this.http.get<HistoryEntry>(`/api/history/${contentId}`); }
  saveProgress(contentId: number, position: number, duration: number) {
    return this.http.put<HistoryEntry>(`/api/history/${contentId}`, { position_seconds: position, duration_seconds: duration });
  }
  removeHistory(contentId: number) { return this.http.delete<void>(`/api/history/${contentId}`); }
  clearHistory() { return this.http.delete<void>('/api/history'); }

  // ---- profile / account
  profile() { return this.http.get<Profile>('/api/users/me'); }
  updateProfile(body: ProfileInput) { return this.http.put<Profile>('/api/users/me', body); }
  changePassword(current_password: string, new_password: string) { return this.http.post<void>('/api/auth/change-password', { current_password, new_password }); }

  // ---- admin users
  adminUsers(q: { q?: string; role?: string; page?: number; page_size?: number }) {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(q)) if (v !== undefined && v !== '') params = params.set(k, String(v));
    return this.http.get<Page<User>>('/api/auth/admin/users', { params });
  }
  adminUpdateUser(id: number, body: { role?: string; is_active?: boolean }) { return this.http.patch<User>(`/api/auth/admin/users/${id}`, body); }
  adminDeleteUser(id: number) { return this.http.delete<void>(`/api/auth/admin/users/${id}`); }
  userStats() { return this.http.get<AuthStats>('/api/auth/admin/stats'); }
}
