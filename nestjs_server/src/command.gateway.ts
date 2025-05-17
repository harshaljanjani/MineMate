import { WebSocketGateway, OnGatewayConnection, OnGatewayDisconnect } from '@nestjs/websockets';
import { Server, WebSocket } from 'ws';

@WebSocketGateway()
export class CommandGateway implements OnGatewayConnection, OnGatewayDisconnect {
  public server: Server;
  private clients: Set<WebSocket> = new Set();

  constructor() {
    this.server = new Server({ noServer: true });
    this.server.on('connection', (client) => {
      this.handleConnection(client);
    });
  }

  afterInit() {
    console.log('WebSocket Gateway initialized');
  }

  handleConnection(client: WebSocket) {
    console.log('Client connected');
    this.clients.add(client);
    client.on('message', (message) => {
      console.log('Received:', message.toString());
    });
    client.on('close', () => {
      this.handleDisconnect(client);
    });
    client.send(JSON.stringify({ type: 'info', payload: 'Connection to NestJS server successful!' }));
  }

  handleDisconnect(client: WebSocket) {
    console.log('Client disconnected');
    this.clients.delete(client);
  }

  sendToAll(type: string, payload: string) {
    const message = JSON.stringify({ type, payload });
    for (const client of this.clients) {
      if (client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    }
  }
}