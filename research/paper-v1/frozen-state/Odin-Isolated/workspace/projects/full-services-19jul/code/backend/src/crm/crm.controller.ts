import { Controller, Get, Post } from '@nestjs/common';
import { CrmService } from './crm.service';

@Controller('crm')
export class CrmController {
  constructor(private readonly crm: CrmService) {}

  @Get('deals')
  deals() {
    return this.crm.listDeals();
  }

  @Get('contacts')
  contacts() {
    return this.crm.listContacts();
  }

  @Get('pipeline')
  pipeline() {
    return this.crm.pipelineSummary();
  }

  @Post('sync')
  sync() {
    return this.crm.syncDeals();
  }
}
