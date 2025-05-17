import { Controller, Post, Body, HttpException, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

interface CommandBody {
  command: string;
}

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('command')
  async handleCommand(@Body() body: CommandBody) {
    try {
      if (!body.command || typeof body.command !== 'string' || body.command.trim() === '') {
        throw new HttpException('Command is required and must be a non-empty string.', HttpStatus.BAD_REQUEST);
      }
      const result = await this.appService.processCommand(body.command);
      return result; 
    } catch (error) {
      const message = error.message || 'Internal server error in controller';
      const status = error.status || HttpStatus.INTERNAL_SERVER_ERROR;
      throw new HttpException(
        message,
        status,
      );
    }
  }
}