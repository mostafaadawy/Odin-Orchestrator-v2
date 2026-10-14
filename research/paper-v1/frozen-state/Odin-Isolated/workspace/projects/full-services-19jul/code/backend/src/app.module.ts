import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { CrmModule } from './crm/crm.module';
import { EmailModule } from './email/email.module';
import { FulfillmentModule } from './fulfillment/fulfillment.module';
import { SupportModule } from './support/support.module';
import { AnalyticsModule } from './analytics/analytics.module';
import { HealthController } from './health/health.controller';
import { CrmContact } from './crm/entities/contact.entity';
import { CrmDeal } from './crm/entities/deal.entity';
import { EmailCampaign } from './email/entities/campaign.entity';
import { EmailEngagement } from './email/entities/engagement.entity';
import { FulfillmentOrder } from './fulfillment/entities/order.entity';
import { FulfillmentShipment } from './fulfillment/entities/shipment.entity';
import { SupportTicket } from './support/entities/ticket.entity';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    TypeOrmModule.forRoot({
      type: 'postgres',
      url: process.env.DATABASE_URL,
      entities: [
        CrmContact,
        CrmDeal,
        EmailCampaign,
        EmailEngagement,
        FulfillmentOrder,
        FulfillmentShipment,
        SupportTicket,
      ],
      synchronize: false, // schema is owned by SQL migrations (prisma/migrations)
    }),
    CrmModule,
    EmailModule,
    FulfillmentModule,
    SupportModule,
    AnalyticsModule,
  ],
  controllers: [HealthController],
})
export class AppModule {}
