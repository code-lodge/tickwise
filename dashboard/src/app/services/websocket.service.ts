import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class WebsocketService {
  private socket: WebSocket | null = null;
  readonly lastMessage = signal<unknown>(null);
  readonly connected = signal<boolean>(false);

  connect(): void {
    if (this.socket && this.socket.readyState <= WebSocket.OPEN) return;
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${window.location.host}/ws/live`;
    this.socket = new WebSocket(url);
    this.socket.onopen = () => this.connected.set(true);
    this.socket.onclose = () => this.connected.set(false);
    this.socket.onerror = () => this.connected.set(false);
    this.socket.onmessage = (event) => {
      try {
        this.lastMessage.set(JSON.parse(event.data));
      } catch {
        this.lastMessage.set(event.data);
      }
    };
  }

  send(message: unknown): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(typeof message === 'string' ? message : JSON.stringify(message));
    }
  }

  close(): void {
    this.socket?.close();
    this.socket = null;
    this.connected.set(false);
  }
}
