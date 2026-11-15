import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from './auth.service';

const AUTH_ENDPOINT = /\/api\/auth\/(login|register|refresh|logout)$/;

/** Adds the bearer token to API calls and transparently refreshes it once when it has expired. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  if (!req.url.startsWith('/api/')) return next(req);
  const isAuthEndpoint = AUTH_ENDPOINT.test(req.url.split('?')[0]);
  const withToken = (r: HttpRequest<unknown>, token: string | null) => (token ? r.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : r);

  return next(isAuthEndpoint ? req : withToken(req, auth.accessToken)).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse && err.status === 401 && !isAuthEndpoint) {
        if (!auth.hasRefreshToken) { auth.logout(true); return throwError(() => err); }
        return auth.refresh().pipe(
          switchMap((token) => next(withToken(req, token))),
          catchError((e) => { auth.logout(true); return throwError(() => e); }),
        );
      }
      return throwError(() => err);
    }),
  );
};

/** Surfaces infrastructure-level failures (offline, 5xx, throttling) once, centrally. */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const snack = inject(MatSnackBar);
  return next(req).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse && req.url.startsWith('/api/')) {
        if (err.status === 0) snack.open('Cannot reach the server. Check your connection.', 'Dismiss', { duration: 5000 });
        else if (err.status >= 500) snack.open('The server had a problem. Please try again shortly.', 'Dismiss', { duration: 5000 });
        else if (err.status === 429) snack.open('Too many requests. Please slow down.', 'Dismiss', { duration: 5000 });
      }
      return throwError(() => err);
    }),
  );
};
