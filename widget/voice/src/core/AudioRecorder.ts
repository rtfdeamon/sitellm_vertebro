/**
 * Audio recording manager for voice input.
 */

import { VoiceLogger } from "../utils/logger";

export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private chunks: Blob[] = [];
  private logger = new VoiceLogger();

  async start(): Promise<void> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.stream = stream;
      
      const options = { mimeType: "audio/webm" };
      this.mediaRecorder = new MediaRecorder(stream, options);
      
      this.chunks = [];
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.chunks.push(event.data);
        }
      };

      this.mediaRecorder.start(1000); // Collect chunks every 1s
      this.logger.log("Audio recording started");
    } catch (error) {
      this.logger.error("Failed to start audio recording", error);
      throw error;
    }
  }

  stop(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder || this.mediaRecorder.state === "inactive") {
        reject(new Error("Recording not active"));
        return;
      }

      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.chunks, { type: "audio/webm" });
        this.cleanup();
        this.logger.log("Audio recording stopped", { size: blob.size });
        resolve(blob);
      };

      this.mediaRecorder.stop();
    });
  }

  async getChunk(): Promise<Blob | null> {
    if (!this.mediaRecorder || this.mediaRecorder.state !== "recording") {
      return null;
    }

    if (this.chunks.length === 0) {
      return null;
    }

    const chunk = this.chunks.shift();
    return chunk || null;
  }

  private cleanup(): void {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    this.mediaRecorder = null;
    this.chunks = [];
  }

  isRecording(): boolean {
    return this.mediaRecorder?.state === "recording";
  }
}

