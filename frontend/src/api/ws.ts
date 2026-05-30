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
    socket = new WebSocket(`${proto}://${window.location.host}/ws/${domain}?token=${encodeURIComponent(token)}`);

    socket.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data) as StreamMessage);
      } catch {
        /* ignore malformed frames */
      }
    };
    socket.onopen = () => {
      retry = 0;
    };
    socket.onclose = () => {
      if (closed) return;
      retry = Math.min(retry + 1, 6);
      timer = setTimeout(connect, 500 * retry);
    };
    socket.onerror = () => socket?.close();
  };

  connect();

  return () => {
    closed = true;
    if (timer) clearTimeout(timer);
    socket?.close();
  };
}
