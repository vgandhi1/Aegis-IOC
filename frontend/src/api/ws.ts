export interface StreamMessage {
  channel: string;
  batch: Record<string, unknown>[];
  snapshot?: boolean;
}

export type StreamHandler = (msg: StreamMessage) => void;

/**
 * Subscribe to a domain's live WebSocket stream. Reconnects with backoff.
 * Returns a disposer that closes the socket.
 */
export function subscribeStream(domain: string, token: string, onMessage: StreamHandler): () => void {
  let socket: WebSocket | null = null;
  let closed = false;
  let retry = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const connect = () => {
    if (closed) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/${domain}?token=${encodeURIComponent(token)}`);
    socket = ws;

    ws.onopen = () => {
      retry = 0;
      // If the subscription was disposed while still connecting (e.g. React
      // StrictMode's mount→cleanup→mount), close cleanly now that the socket is
      // OPEN. Closing a CONNECTING socket is what triggers the browser warning
      // "WebSocket is closed before the connection is established".
      if (closed) ws.close(1000, "disposed");
    };
    ws.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data) as StreamMessage);
      } catch {
        /* ignore malformed frames */
      }
    };
    ws.onclose = () => {
      if (closed) return;
      retry = Math.min(retry + 1, 6);
      timer = setTimeout(connect, 500 * retry);
    };
    // Let onclose drive reconnection; closing here would race with CONNECTING.
    ws.onerror = () => {};
  };

  connect();

  return () => {
    closed = true;
    if (timer) clearTimeout(timer);
    if (!socket) return;
    // Only call close() once the handshake is done; otherwise defer to onopen.
    if (socket.readyState === WebSocket.OPEN) {
      socket.close(1000, "disposed");
    } else if (socket.readyState === WebSocket.CLOSING || socket.readyState === WebSocket.CLOSED) {
      /* already closing/closed */
    }
    // CONNECTING: onopen handler closes it once established (see above).
  };
}
