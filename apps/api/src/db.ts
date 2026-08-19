/** Minimal shape apps/api needs from a Postgres pool — real pg.Pool satisfies this, tests inject a fake. */
export interface QueryablePool {
  query<T>(sql: string, params?: unknown[]): Promise<{ rows: T[] }>;
}
