import { AudioRecorder } from "../src/core/AudioRecorder";

describe("AudioRecorder", () => {
  let recorder: AudioRecorder;
  let mockMediaRecorder: {
    state: string;
    start: jest.Mock;
    stop: jest.Mock;
    ondataavailable: ((event: { data: Blob }) => void) | null;
    onstop: (() => void) | null;
  };
  let mockStream: { getTracks: jest.Mock };

  beforeEach(() => {
    recorder = new AudioRecorder();

    mockMediaRecorder = {
      state: "inactive",
      start: jest.fn(),
      stop: jest.fn(),
      ondataavailable: null,
      onstop: null,
    };

    mockStream = {
      getTracks: jest.fn(() => [
        { stop: jest.fn() },
        { stop: jest.fn() },
      ]),
    };

    (global as unknown as { MediaRecorder: typeof MediaRecorder }).MediaRecorder = jest.fn(
      () => mockMediaRecorder as unknown as MediaRecorder
    ) as unknown as typeof MediaRecorder;

    global.navigator.mediaDevices = {
      getUserMedia: jest.fn(() => Promise.resolve(mockStream as MediaStream)),
    } as unknown as MediaDevices;
  });

  it("starts recording", async () => {
    await recorder.start();

    expect(mockMediaRecorder.start).toHaveBeenCalledWith(1000);
    expect(recorder.isRecording()).toBe(true);
  });

  it("stops recording and returns blob", async () => {
    await recorder.start();
    mockMediaRecorder.state = "recording";

    const stopPromise = recorder.stop();

    // Simulate data available
    const testBlob = new Blob(["test audio"], { type: "audio/webm" });
    if (mockMediaRecorder.ondataavailable) {
      mockMediaRecorder.ondataavailable({ data: testBlob });
    }

    // Simulate stop
    mockMediaRecorder.state = "inactive";
    if (mockMediaRecorder.onstop) {
      mockMediaRecorder.onstop();
    }

    const result = await stopPromise;

    expect(mockMediaRecorder.stop).toHaveBeenCalled();
    expect(result).toBeInstanceOf(Blob);
    expect(mockStream.getTracks().every((track: { stop: jest.Mock }) => track.stop.mock.calls.length > 0)).toBe(true);
  });

  it("handles microphone access errors", async () => {
    global.navigator.mediaDevices.getUserMedia = jest.fn(() =>
      Promise.reject(new Error("Permission denied"))
    );

    await expect(recorder.start()).rejects.toThrow("Permission denied");
  });

  it("returns null chunk when not recording", async () => {
    const chunk = await recorder.getChunk();
    expect(chunk).toBeNull();
  });
});

