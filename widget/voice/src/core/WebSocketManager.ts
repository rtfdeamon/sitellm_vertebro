/**
 * WebSocket manager for real-time voice assistant communication.
 */

import { VoiceLogger } from "../utils/logger";

export type WSMessage = 
  | { type: "audio_chunk"; data: string; sequence: number; is_final: boolean }
  | { type: "text_input"; text: string }
  | { type: "navigation_command"; action: string; params: Record<string, unknown> }
  | { type: "ping" };

export type WSResponse =
  | { type: "transcription"; text: string; is_final: boolean; confidence: number }
  | { type: "response"; text: string; audio_url?: string; sources?: unknown[]; suggested_actions?: unknown[] }
  | { type: "status"; status: "listening" | "thinking" | "speaking" | "error"; message?: string }
  | { type: "pong" }
  | { type: "error"; message: string };

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private logger = new VoiceLogger();
  private messageHandlers: Map<string, (data: WSResponse) => void> = new Map();

  constructor(
    private wsUrl: string,
    private pingIntervalMs: number = 30000
  ) {}

  connect(sessionId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      this.sessionId = sessionId;
      const url = this.wsUrl.replace("{session_id}", sessionId);
      this.logger.log("Connecting to WebSocket", { url, sessionId });

      try {
        this.ws = new WebSocket(url);
        
        this.ws.onopen = () => {
          this.logger.log("WebSocket connected", { sessionId });
          this.reconnectAttempts = 0;
          this.startPingInterval();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data: WSResponse = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            this.logger.error("Failed to parse WebSocket message", error);
          }
        };

        this.ws.onerror = (error) => {
          this.logger.error("WebSocket error", error);
          reject(error);
        };

        this.ws.onclose = () => {
          this.logger.log("WebSocket closed", { sessionId });
          this.stopPingInterval();
          this.attemptReconnect();
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  disconnect(): void {
    this.stopPingInterval();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.sessionId = null;
    this.messageHandlers.clear();
  }

  send(message: WSMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.logger.error("Cannot send message: WebSocket not connected");
      return;
    }

    try {
      this.ws.send(JSON.stringify(message));
    } catch (error) {
      this.logger.error("Failed to send WebSocket message", error);
    }
  }

  onMessage(type: string, handler: (data: WSResponse) => void): void {
    this.messageHandlers.set(type, handler);
  }

  private handleMessage(data: WSResponse): void {
    const handler = this.messageHandlers.get(data.type);
    if (handler) {
      handler(data);
    }
  }

  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      this.send({ type: "ping" });
    }, this.pingIntervalMs);
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private attemptReconnect(): void {
    if (!this.sessionId || this.reconnectAttempts >= this.maxReconnectAttempts) {
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    this.logger.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      this.connect(this.sessionId!).catch((error) => {
        this.logger.error("Reconnection failed", error);
      });
    }, delay);
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

