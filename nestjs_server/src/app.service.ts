import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { CommandGateway } from './command.gateway';

interface CommandDetails {
  action: string;
  device: string;
  room: string;
}

interface SequenceDetails {
  commands: CommandDetails[];
  repeat: number | 'infinite';
  delay_ms?: number;
}

type ActionDetails = CommandDetails | SequenceDetails;

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

      let conversationalPart = gemmaData.raw_response;
      const jsonStartIndex = conversationalPart.indexOf('{');
      if (jsonStartIndex !== -1) {
        conversationalPart = conversationalPart.substring(0, jsonStartIndex).trim();
      }

      if (gemmaData.action_details) {
        if ('commands' in gemmaData.action_details) {
          const sequence = gemmaData.action_details as SequenceDetails;
          if (Array.isArray(sequence.commands) && sequence.commands.length > 0 &&
              (typeof sequence['repeat'] === 'number' || sequence['repeat'] === 'infinite')) {
            let allCommandsValid = true;
            for (const cmd of sequence.commands) {
              if (!(cmd && typeof cmd.action === 'string' && typeof cmd.device === 'string' && typeof cmd.room === 'string' &&
                    VALID_ACTIONS.includes(cmd.action) &&
                    VALID_ROOMS.includes(cmd.room.toLowerCase()))) {
                allCommandsValid = false;
                console.warn(`Invalid command in sequence: ${JSON.stringify(cmd)}`);
                break;
              }
            }
            if (allCommandsValid) {
              const normalizedCommands = sequence.commands.map(cmd => ({
                ...cmd,
                room: cmd.room.toLowerCase()
              }));
              const sequencePayload = {
                commands: normalizedCommands,
                repeat: sequence['repeat'],
                delay_ms: sequence.delay_ms
              };
              if (conversationalPart && conversationalPart.trim() !== '') {
                this.commandGateway.sendToAll('info', conversationalPart);
              }
              console.log(`Sending sequence_command to clients: ${JSON.stringify(sequencePayload)}`);
              this.commandGateway.sendToAll('sequence_command', JSON.stringify(sequencePayload));
              return gemmaData;
            } else {
              console.warn('Sequence identified but contained invalid command details. Treating as info.');
            }
          } else {
            console.warn('Invalid sequence structure in action_details.');
          }
        } else if ('action' in gemmaData.action_details && 'device' in gemmaData.action_details && 'room' in gemmaData.action_details) {
          const cmd = gemmaData.action_details as CommandDetails;
          if (typeof cmd.action === 'string' && typeof cmd.device === 'string' && typeof cmd.room === 'string' &&
              VALID_ACTIONS.includes(cmd.action) &&
              VALID_ROOMS.includes(cmd.room.toLowerCase())) {
            const commandString = `${cmd.action} ${cmd.device} ${cmd.room.toLowerCase()}`;
            if (conversationalPart && conversationalPart.trim() !== '') {
              this.commandGateway.sendToAll('info', conversationalPart);
            }
            console.log(`Sending command to clients: "${commandString}"`);
            this.commandGateway.sendToAll('command', commandString);
            return gemmaData;
          } else {
            console.warn(`Invalid single command details: ${JSON.stringify(cmd)}`);
          }
        } else {
          console.warn('Unrecognized action_details structure.');
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