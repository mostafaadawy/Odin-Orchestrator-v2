import { Controller, Get, Post } from '@nestjs/common';
import { EmailService } from './email.service';

@Controller('email')
export class EmailController {
  constructor(private readonly email: EmailService) {}

  @Get('campaigns')
  campaigns() {
    return this.email.listCampaigns();
  }

  @Get('engagement')
  engagement() {
    return this.email.engagementSummary();
  }

  @Post('sync')
  sync() {
    return this.email.syncFlows();
  }
}
