import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { EmailController } from './email.controller';
import { EmailService } from './email.service';
import { KlaviyoClient } from './klaviyo.client';
import { EmailCampaign } from './entities/campaign.entity';
import { EmailEngagement } from './entities/engagement.entity';

@Module({
  imports: [TypeOrmModule.forFeature([EmailCampaign, EmailEngagement])],
  controllers: [EmailController],
  providers: [EmailService, KlaviyoClient],
  exports: [EmailService],
})
export class EmailModule {}
