import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { CrmController } from './crm.controller';
import { CrmService } from './crm.service';
import { HubspotClient } from './hubspot.client';
import { CrmDeal } from './entities/deal.entity';
import { CrmContact } from './entities/contact.entity';

@Module({
  imports: [TypeOrmModule.forFeature([CrmDeal, CrmContact])],
  controllers: [CrmController],
  providers: [CrmService, HubspotClient],
  exports: [CrmService],
})
export class CrmModule {}
