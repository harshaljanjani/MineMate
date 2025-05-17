import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { WsAdapter } from '@nestjs/platform-ws';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useWebSocketAdapter(new WsAdapter(app));
  app.enableCors({
    origin: '*',
    methods: ['GET', 'POST'],
  });
  await app.listen(3000);
  console.log('NestJS server running on http://localhost:3000');
}
bootstrap();