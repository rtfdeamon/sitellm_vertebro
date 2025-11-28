/**
 * Audio playback manager for voice output.
 */

import { VoiceLogger } from "../utils/logger";

export class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;
  private logger = new VoiceLogger();

  async play(audioUrl: string): Promise<void> {
    try {
      const response = await fetch(audioUrl);
      if (!response.ok) {
        throw new Error(`Failed to fetch audio: ${response.statusText}`);
      }

      const arrayBuffer = await response.arrayBuffer();
      if (!this.audioContext) {
        this.audioContext = new AudioContext();
      }

      const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
      
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);

      this.currentSource = source;
      
      return new Promise((resolve, reject) => {
        source.onended = () => {
          this.currentSource = null;
          resolve();
        };

        try {
          source.start(0);
          this.logger.log("Audio playback started", { duration: audioBuffer.duration });
        } catch (error) {
          this.logger.error("Audio playback error", error);
          this.currentSource = null;
          reject(error);
        }
      });
    } catch (error) {
      this.logger.error("Failed to play audio", error);
      throw error;
    }
  }

  stop(): void {
    if (this.currentSource) {
      try {
        this.currentSource.stop();
      } catch (error) {
        // Source may already be stopped
        this.logger.log("Audio already stopped");
      }
      this.currentSource = null;
    }
  }

  isPlaying(): boolean {
    return this.currentSource !== null;
  }
}

