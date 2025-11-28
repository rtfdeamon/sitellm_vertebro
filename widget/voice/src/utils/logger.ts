export class VoiceLogger {
  log(message: string, data?: unknown): void {
    // eslint-disable-next-line no-console
    console.log(`[VoiceWidget] ${message}`, data ?? "");
  }

  error(message: string, data?: unknown): void {
    // eslint-disable-next-line no-console
    console.error(`[VoiceWidget] ${message}`, data ?? "");
  }
}

