export type Category = 'movie' | 'tv_show' | 'web_series' | 'other';
export type Role = 'user' | 'admin';

export interface Content {
  id: number; title: string; description: string; genre: string; language: string;
  release_year: number; duration_minutes: number; category: Category; maturity_rating: string;
  is_featured: boolean; created_at: string; updated_at: string;
}
export type ContentInput = Omit<Content, 'id' | 'created_at' | 'updated_at'>;
export interface Page<T> { items: T[]; total: number; page: number; page_size: number; pages: number; }
export interface User { id: number; email: string; username: string; role: Role; is_active: boolean; created_at: string; last_login_at?: string | null; }
export interface TokenResponse { access_token: string; refresh_token: string; token_type: string; expires_in: number; user: User; }
export interface Profile {
  user_id: number; email: string; username: string; role: Role; display_name: string; bio: string | null;
  preferred_language: string; avatar_color: string; created_at: string; updated_at: string;
}
export interface ProfileInput { display_name: string; bio: string | null; preferred_language: string; avatar_color: string; }
export interface HistoryEntry { content_id: number; position_seconds: number; duration_seconds: number; completed: boolean; last_watched_at: string; }
export interface WatchlistEntry { content_id: number; added_at: string; }
export interface MediaAsset { content_id: number; kind: MediaKind; content_type: string; size_bytes: number; original_filename: string | null; updated_at: string; }
export type MediaKind = 'video' | 'poster' | 'thumbnail';
export interface Facets { genres: string[]; languages: string[]; categories: string[]; years: number[]; }
export interface ContentStats { total: number; featured: number; added_last_7_days: number; by_category: Record<string, number>; by_genre: Record<string, number>; by_language: Record<string, number>; }
export interface AuthStats { total_users: number; admins: number; active_users: number; new_last_7_days: number; }
export interface ContentQuery { q?: string; genre?: string; language?: string; category?: string; year?: number; featured?: boolean; ids?: number[]; sort?: string; page?: number; page_size?: number; }

export const CATEGORY_LABELS: Record<string, string> = { movie: 'Movies', tv_show: 'TV Shows', web_series: 'Web Series', other: 'Specials' };
export const CATEGORY_SINGULAR: Record<string, string> = { movie: 'Movie', tv_show: 'TV Show', web_series: 'Web Series', other: 'Special' };
