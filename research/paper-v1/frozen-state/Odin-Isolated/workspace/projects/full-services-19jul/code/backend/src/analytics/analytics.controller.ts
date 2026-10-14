import { Controller, Get } from '@nestjs/common';
import { AnalyticsService } from './analytics.service';

// /analytics — aggregated operations metrics across CRM, Email and Fulfillment.
@Controller('analytics')
export class AnalyticsController {
  constructor(private readonly analytics: AnalyticsService) {}

  /** Unified snapshot used by the dashboard analytics view. */
  @Get()
  overview() {
    return this.analytics.overview();
  }

  @Get('crm')
  crm() {
    return this.analytics.crm();
  }

  @Get('email')
  email() {
    return this.analytics.email();
  }

  @Get('fulfillment')
  fulfillment() {
    return this.analytics.fulfillment();
  }
}
