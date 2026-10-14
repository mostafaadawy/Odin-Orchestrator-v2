import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { FulfillmentController } from './fulfillment.controller';
import { FulfillmentService } from './fulfillment.service';
import { VeeqoClient } from './veeqo.client';
import { FulfillmentOrder } from './entities/order.entity';
import { FulfillmentShipment } from './entities/shipment.entity';

@Module({
  imports: [TypeOrmModule.forFeature([FulfillmentOrder, FulfillmentShipment])],
  controllers: [FulfillmentController],
  providers: [FulfillmentService, VeeqoClient],
  exports: [FulfillmentService],
})
export class FulfillmentModule {}
