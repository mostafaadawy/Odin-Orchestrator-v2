import { Controller, Get, Post } from '@nestjs/common';
import { FulfillmentService } from './fulfillment.service';

@Controller('fulfillment')
export class FulfillmentController {
  constructor(private readonly fulfillment: FulfillmentService) {}

  @Get('orders')
  orders() {
    return this.fulfillment.listOrders();
  }

  @Get('shipments')
  shipments() {
    return this.fulfillment.listShipments();
  }

  @Get('throughput')
  throughput() {
    return this.fulfillment.throughputSummary();
  }

  @Post('sync')
  sync() {
    return this.fulfillment.syncOrders();
  }
}
