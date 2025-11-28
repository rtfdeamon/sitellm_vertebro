import { WebSocketManager, WSMessage } from "../src/core/WebSocketManager";

describe("WebSocketManager", () => {
  let mockWs: {
    readyState: number;
    send: jest.Mock;
    close: jest.Mock;
    onopen: ((event: Event) => void) | null;
    onmessage: ((event: MessageEvent) => void) | null;
    onerror: ((event: Event) => void) | null;
    onclose: ((event: CloseEvent) => void) | null;
  };
  let manager: WebSocketManager;

  beforeEach(() => {
    mockWs = {
      readyState: WebSocket.CONNECTING,
      send: jest.fn(),
      close: jest.fn(),
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
    };

    (global as unknown as { WebSocket: typeof WebSocket }).WebSocket = jest.fn(
      () => mockWs as unknown as WebSocket
    ) as unknown as typeof WebSocket;

    manager = new WebSocketManager("ws://localhost:8000/api/v1/voice/ws/{session_id}", 30000);
  });

  afterEach(() => {
    manager.disconnect();
  });

  it("connects successfully", async () => {
    const connectPromise = manager.connect("test-session");

    // Simulate successful connection
    mockWs.readyState = WebSocket.OPEN;
    if (mockWs.onopen) {
      mockWs.onopen(new Event("open"));
    }

    await connectPromise;

    expect(mockWs.send).not.toHaveBeenCalled(); // No messages sent on connect
    expect(manager.isConnected()).toBe(true);
  });

  it("sends messages when connected", async () => {
    await manager.connect("test-session");
    mockWs.readyState = WebSocket.OPEN;
    if (mockWs.onopen) {
      mockWs.onopen(new Event("open"));
    }

    const message: WSMessage = { type: "text_input", text: "Hello" };
    manager.send(message);

    expect(mockWs.send).toHaveBeenCalledWith(JSON.stringify(message));
  });

  it("handles incoming messages", async () => {
    const messageHandler = jest.fn();
    manager.onMessage("transcription", messageHandler);

    await manager.connect("test-session");
    mockWs.readyState = WebSocket.OPEN;
    if (mockWs.onopen) {
      mockWs.onopen(new Event("open"));
    }

    const incomingMessage = {
      type: "transcription",
      text: "Test transcription",
      is_final: true,
      confidence: 0.9,
    };

    if (mockWs.onmessage) {
      mockWs.onmessage({
        data: JSON.stringify(incomingMessage),
      } as MessageEvent);
    }

    expect(messageHandler).toHaveBeenCalledWith(incomingMessage);
  });

  it("sends ping messages on interval", async () => {
    manager = new WebSocketManager("ws://localhost:8000/api/v1/voice/ws/{session_id}", 100);
    await manager.connect("test-session");
    mockWs.readyState = WebSocket.OPEN;
    if (mockWs.onopen) {
      mockWs.onopen(new Event("open"));
    }

    // Wait for ping interval
    await new Promise((resolve) => setTimeout(resolve, 150));

    expect(mockWs.send).toHaveBeenCalledWith(JSON.stringify({ type: "ping" }));
  });

  it("disconnects cleanly", async () => {
    await manager.connect("test-session");
    mockWs.readyState = WebSocket.OPEN;
    if (mockWs.onopen) {
      mockWs.onopen(new Event("open"));
    }

    manager.disconnect();

    expect(mockWs.close).toHaveBeenCalled();
    expect(manager.isConnected()).toBe(false);
  });

  it("does not send when not connected", () => {
    const message: WSMessage = { type: "ping" };
    manager.send(message);

    expect(mockWs.send).not.toHaveBeenCalled();
  });
});

