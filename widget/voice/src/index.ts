import "./index.css";
import { VoiceLogger } from "./utils/logger";
import { WebSocketManager } from "./core/WebSocketManager";
import { AudioRecorder } from "./core/AudioRecorder";
import { AudioPlayer } from "./core/AudioPlayer";
import { VoiceWidgetState, VoiceWidgetConfig, VoiceSession } from "./types";

export class VoiceWidget {
  private root: HTMLElement;
  private logger = new VoiceLogger();
  private state: VoiceWidgetState = "idle";
  private wsManager: WebSocketManager | null = null;
  private audioRecorder: AudioRecorder | null = null;
  private audioPlayer: AudioPlayer | null = null;
  private session: VoiceSession | null = null;
  private config: VoiceWidgetConfig;

  constructor(root: HTMLElement, config: VoiceWidgetConfig = {}) {
    this.root = root;
    this.config = {
      apiBaseUrl: config.apiBaseUrl || "",
      project: config.project || "default",
      userId: config.userId,
      language: config.language || "ru-RU",
      voicePreference: config.voicePreference || {},
    };
    this.audioRecorder = new AudioRecorder();
    this.audioPlayer = new AudioPlayer();
  }

  mount(): void {
    this.render();
    this.setupEventListeners();
  }

  async startSession(): Promise<void> {
    if (this.state !== "idle") {
      this.logger.log("Session already active");
      return;
    }

    try {
      this.setState("processing");
      const session = await this.createSession();
      this.session = session;

      const wsUrl = this.buildWebSocketUrl(session.websocketUrl);
      this.wsManager = new WebSocketManager(wsUrl);
      this.setupWebSocketHandlers();

      await this.wsManager.connect(session.sessionId);
      
      if (session.initialGreeting) {
        this.logger.log("Initial greeting", session.initialGreeting);
        // Could display greeting or play it
      }

      this.setState("idle");
    } catch (error) {
      this.logger.error("Failed to start session", error);
      this.setState("error");
    }
  }

  async stopSession(): Promise<void> {
    if (this.wsManager) {
      this.wsManager.disconnect();
      this.wsManager = null;
    }
    if (this.audioRecorder?.isRecording()) {
      await this.audioRecorder.stop();
    }
    if (this.audioPlayer?.isPlaying()) {
      this.audioPlayer.stop();
    }
    this.session = null;
    this.setState("idle");
  }

  async startListening(): Promise<void> {
    if (!this.wsManager?.isConnected()) {
      this.logger.error("WebSocket not connected");
      return;
    }

    try {
      await this.audioRecorder!.start();
      this.setState("listening");
      
      // Stream audio chunks to WebSocket
      const chunkInterval = setInterval(async () => {
        if (!this.audioRecorder?.isRecording() || !this.wsManager?.isConnected()) {
          clearInterval(chunkInterval);
          return;
        }

        const chunk = await this.audioRecorder.getChunk();
        if (chunk) {
          const base64 = await this.blobToBase64(chunk);
          this.wsManager.send({
            type: "audio_chunk",
            data: base64,
            sequence: Date.now(),
            is_final: false,
          });
        }
      }, 1000);
    } catch (error) {
      this.logger.error("Failed to start listening", error);
      this.setState("error");
    }
  }

  async stopListening(): Promise<void> {
    if (!this.audioRecorder?.isRecording()) {
      return;
    }

    try {
      const finalBlob = await this.audioRecorder.stop();
      const base64 = await this.blobToBase64(finalBlob);
      
      if (this.wsManager?.isConnected()) {
        this.wsManager.send({
          type: "audio_chunk",
          data: base64,
          sequence: Date.now(),
          is_final: true,
        });
      }

      this.setState("processing");
    } catch (error) {
      this.logger.error("Failed to stop listening", error);
      this.setState("error");
    }
  }

  private async createSession(): Promise<VoiceSession> {
    const apiUrl = `${this.config.apiBaseUrl}/api/v1/voice/session/start`;
    const response = await fetch(apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project: this.config.project,
        user_id: this.config.userId,
        language: this.config.language,
        voice_preference: this.config.voicePreference,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      sessionId: data.session_id,
      websocketUrl: data.websocket_url,
      expiresAt: new Date(data.expires_at),
      initialGreeting: data.initial_greeting,
    };
  }

  private buildWebSocketUrl(url: string): string {
    // Replace protocol if needed
    if (url.startsWith("ws://") || url.startsWith("wss://")) {
      return url;
    }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return url.replace(/^https?:/, protocol);
  }

  private setupWebSocketHandlers(): void {
    if (!this.wsManager) return;

    this.wsManager.onMessage("transcription", (data) => {
      if (data.type === "transcription") {
        this.logger.log("Transcription received", data.text);
        if (data.is_final) {
          this.setState("processing");
        }
      }
    });

    this.wsManager.onMessage("response", async (data) => {
      if (data.type === "response") {
        this.logger.log("Response received", data.text);
        if (data.audio_url) {
          this.setState("speaking");
          const fullUrl = data.audio_url.startsWith("http")
            ? data.audio_url
            : `${this.config.apiBaseUrl}${data.audio_url}`;
          await this.audioPlayer!.play(fullUrl);
          this.setState("idle");
        }
      }
    });

    this.wsManager.onMessage("status", (data) => {
      if (data.type === "status") {
        const statusMap: Record<string, VoiceWidgetState> = {
          listening: "listening",
          thinking: "processing",
          speaking: "speaking",
          error: "error",
        };
        this.setState(statusMap[data.status] || "idle");
      }
    });

    this.wsManager.onMessage("error", (data) => {
      if (data.type === "error") {
        this.logger.error("WebSocket error", data.message);
        this.setState("error");
      }
    });
  }

  private setState(newState: VoiceWidgetState): void {
    this.state = newState;
    const statusEl = this.root.querySelector("[data-test='status']");
    if (statusEl) {
      statusEl.textContent = this.getStateLabel(newState);
      statusEl.className = `voice-widget__status voice-widget__status--${newState}`;
    }
  }

  private getStateLabel(state: VoiceWidgetState): string {
    const labels: Record<VoiceWidgetState, string> = {
      idle: "Idle",
      listening: "Listening…",
      processing: "Processing…",
      speaking: "Speaking…",
      error: "Error",
    };
    return labels[state];
  }

  private render(): void {
    this.root.innerHTML = `
      <div class="voice-widget">
        <div data-test="status" class="voice-widget__status voice-widget__status--idle">Idle</div>
        <div class="voice-widget__controls">
          <button data-action="start" class="voice-widget__button">Start Session</button>
          <button data-action="listen" class="voice-widget__button" disabled>Listen</button>
          <button data-action="stop" class="voice-widget__button" disabled>Stop</button>
        </div>
      </div>
    `;
  }

  private setupEventListeners(): void {
    this.root.querySelector("[data-action='start']")?.addEventListener("click", () => {
      this.startSession();
    });

    this.root.querySelector("[data-action='listen']")?.addEventListener("click", () => {
      if (this.state === "listening") {
        this.stopListening();
      } else {
        this.startListening();
      }
    });

    this.root.querySelector("[data-action='stop']")?.addEventListener("click", () => {
      this.stopSession();
    });
  }

  private async blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = reader.result as string;
        const base64 = result.split(",")[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  destroy(): void {
    this.stopSession();
    this.root.innerHTML = "";
  }
}

export function createVoiceWidget(
  root: HTMLElement,
  config?: VoiceWidgetConfig
): VoiceWidget {
  const widget = new VoiceWidget(root, config);
  widget.mount();
  return widget;
}
