import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { CommandGateway } from './command.gateway';
interface ActionDetails {
  action: string;
  device: string;
  room: string;
}
interface GemmaApiResponse {
  raw_response: string;
  action_details?: ActionDetails;
  error?: string;
}
const VALID_ROOMS = ['living room', 'kitchen', 'bedroom', 'bathroom', 'office', 'main'];
const VALID_ACTIONS = ['turn_on', 'turn_off', 'lock', 'unlock', 'open', 'close'];

@Injectable()
export class AppService {
  constructor(
    private readonly httpService: HttpService,
    private readonly commandGateway: CommandGateway
  ) {}
  private readonly gemmaApiUrl = 'http://localhost:8000/generate';

  async processCommand(command: string): Promise<GemmaApiResponse> {
    /**
    * @param command - The user's command, e.g., "turn on lights in kitchen"
    * @returns Parsed JSON response from Gemma
    * @throws Error if API call or parsing fails
    */
    try {
      console.log(`Processing command: "${command}"`);
      const apiResponse = await firstValueFrom(
        this.httpService.post<GemmaApiResponse>(this.gemmaApiUrl, { command }),
      );

      const gemmaData = apiResponse.data;
      if (!gemmaData || typeof gemmaData.raw_response !== 'string') {
        this.commandGateway.sendToAll('info', 'SYSTEM_ERROR: Invalid response structure from LLM API.');
        throw new Error('Invalid or empty response structure from Gemma API');
      }

      if (gemmaData.error) {
        console.error(`Error from Gemma API: ${gemmaData.error}`);
        this.commandGateway.sendToAll('info', `LLM_ERROR: ${gemmaData.error}`);
        return gemmaData;
      }

      if (gemmaData.action_details) {
        const { action, device, room } = gemmaData.action_details;
        if (action && device && room) {
          const lowerCaseRoom = room.toLowerCase();
          if (VALID_ROOMS.includes(lowerCaseRoom) && VALID_ACTIONS.includes(action)) {
            const commandString = `${action} ${device} ${room}`;
            console.log(`Sending command to clients: "${commandString}"`);
            this.commandGateway.sendToAll('command', commandString);
            return gemmaData;
          } else {
            console.warn(`Action identified but invalid room/action: Room="${room}", Action="${action}". Treating as info.`);
          }
        }
      }
      console.log(`Sending info to clients: "${gemmaData.raw_response}"`);
      this.commandGateway.sendToAll('info', gemmaData.raw_response);
      return gemmaData;
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Unknown error during command processing';
      console.error(`Error processing command "${command}":`, errorMessage, error.stack);
      this.commandGateway.sendToAll('info', `SYSTEM_ERROR: ${errorMessage}`);
      return { raw_response: `System error: ${errorMessage}`, error: errorMessage };
    }
  }
}