import { Controller, Get } from '@nestjs/common';

@Controller('health')
export class HealthController {
  @Get()
  check() {
    return { status: 'ok', service: 'odin-ops-api', ts: new Date().toISOString() };
  }
}
