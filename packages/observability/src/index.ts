import pino from "pino";

export interface CreateLoggerOptions {
  /** Logical service name, attached to every log line as `service`. */
  service: string;
  level?: "fatal" | "error" | "warn" | "info" | "debug" | "trace";
}

/**
 * Creates a structured JSON logger. Every log line carries `service` and an
 * ISO 8601 UTC `time` field so logs from every app/service are correlatable
 * without ad hoc parsing.
 */
export function createLogger(options: CreateLoggerOptions) {
  return pino({
    level: options.level ?? "info",
    base: { service: options.service },
    timestamp: () => `,"time":"${new Date().toISOString()}"`,
  });
}

export type Logger = ReturnType<typeof createLogger>;
