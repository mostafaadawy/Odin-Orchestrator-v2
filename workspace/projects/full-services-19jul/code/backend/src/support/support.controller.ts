import { Body, Controller, Get, Param, Patch, Post } from '@nestjs/common';
import { SupportService } from './support.service';
import { SupportTicket } from './entities/ticket.entity';

@Controller('support')
export class SupportController {
  constructor(private readonly support: SupportService) {}

  @Get('tickets')
  list() {
    return this.support.list();
  }

  @Get('summary')
  summary() {
    return this.support.summary();
  }

  @Post('tickets')
  create(@Body() dto: Partial<SupportTicket>) {
    return this.support.create(dto);
  }

  @Patch('tickets/:id/status')
  transition(@Param('id') id: string, @Body('status') status: string) {
    return this.support.transition(id, status);
  }
}
