/**
 * Type definitions for the voice widget.
 */

export type VoiceWidgetState = 
  | "idle" 
  | "listening" 
  | "processing" 
  | "speaking" 
  | "error";

export interface VoiceWidgetConfig {
  apiBaseUrl?: string;
  project?: string;
  userId?: string;
  language?: string;
  voicePreference?: Record<string, unknown>;
}

export interface VoiceSession {
  sessionId: string;
  websocketUrl: string;
  expiresAt: Date;
  initialGreeting?: string;
}

