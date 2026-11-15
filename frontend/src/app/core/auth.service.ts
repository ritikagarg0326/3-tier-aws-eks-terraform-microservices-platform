import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, finalize, map, of, shareReplay, tap, throwError } from 'rxjs';
import { TokenResponse, User } from './models';

interface Session { access: string; refresh: string; user: User; }
const KEY = 'hotstar.session';

/**
 * JWT session handling. Access + refresh tokens live in localStorage so a session survives reloads.
 * (Trade-off documented in docs/ARCHITECTURE.md: httpOnly cookies are the hardened alternative for same-site deployments.)
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private session = signal<Session | null>(this.read());
  private refreshing$?: Observable<string>;

  readonly user = computed(() => this.session()?.user ?? null);
  readonly isLoggedIn = computed(() => this.session() !== null);
  readonly isAdmin = computed(() => this.session()?.user.role === 'admin');

  get accessToken(): string | null { return this.session()?.access ?? null; }
  get hasRefreshToken(): boolean { return !!this.session()?.refresh; }

  login(email: string, password: string) {
    return this.http.post<TokenResponse>('/api/auth/login', { email, password }).pipe(tap((r) => this.store(r)));
  }

  register(email: string, username: string, password: string) {
    return this.http.post<TokenResponse>('/api/auth/register', { email, username, password }).pipe(tap((r) => this.store(r)));
  }

  /** One in-flight refresh shared by all requests that hit an expired token at the same time. */
  refresh(): Observable<string> {
    const refresh = this.session()?.refresh;
    if (!refresh) return throwError(() => new Error('no refresh token'));
    this.refreshing$ ??= this.http.post<TokenResponse>('/api/auth/refresh', { refresh_token: refresh }).pipe(
      tap((r) => this.store(r)),
      map((r) => r.access_token),
      finalize(() => (this.refreshing$ = undefined)),
      shareReplay(1),
    );
    return this.refreshing$;
  }

  logout(expired = false): void {
    const refresh = this.session()?.refresh;
    if (refresh && !expired) this.http.post('/api/auth/logout', { refresh_token: refresh }).pipe(catchError(() => of(null))).subscribe();
    this.clear();
    this.router.navigate(['/login'], expired ? { queryParams: { expired: 1 } } : {});
  }

  updateUser(user: User): void {
    const s = this.session();
    if (s) this.persist({ ...s, user });
  }

  private store(r: TokenResponse): void {
    this.persist({ access: r.access_token, refresh: r.refresh_token, user: r.user });
  }

  private persist(s: Session): void {
    this.session.set(s);
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch { /* private mode: keep in memory only */ }
  }

  private clear(): void {
    this.session.set(null);
    try { localStorage.removeItem(KEY); } catch { /* ignore */ }
  }

  private read(): Session | null {
    try {
      const raw = localStorage.getItem(KEY);
      const s = raw ? (JSON.parse(raw) as Session) : null;
      return s?.access && s.refresh && s.user ? s : null;
    } catch { return null; }
  }
}
