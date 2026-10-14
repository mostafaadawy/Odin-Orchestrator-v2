import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { FulfillmentOrder } from './entities/order.entity';
import { FulfillmentShipment } from './entities/shipment.entity';
import { VeeqoClient } from './veeqo.client';

@Injectable()
export class FulfillmentService {
  constructor(
    @InjectRepository(FulfillmentOrder) private readonly orders: Repository<FulfillmentOrder>,
    @InjectRepository(FulfillmentShipment) private readonly shipments: Repository<FulfillmentShipment>,
    private readonly veeqo: VeeqoClient,
  ) {}

  listOrders(): Promise<FulfillmentOrder[]> {
    return this.orders.find({ take: 200 });
  }

  listShipments(): Promise<FulfillmentShipment[]> {
    return this.shipments.find({ take: 200 });
  }

  /** Pull live orders + shipments from Veeqo and upsert them. */
  async syncOrders(): Promise<{ orders: number; shipments: number }> {
    const remote = await this.veeqo.fetchOrders(50);
    let orderCount = 0;
    let shipmentCount = 0;
    for (const o of remote) {
      const existing = await this.orders.findOne({ where: { veeqoId: o.veeqoId } });
      const saved = await this.orders.save(
        this.orders.create({ ...existing, ...o, shipments: undefined }),
      );
      orderCount++;
      for (const s of o.shipments || []) {
        const ex = await this.shipments.findOne({ where: { veeqoId: s.veeqoId } });
        await this.shipments.save(this.shipments.create({ ...ex, ...s, orderId: saved.id }));
        shipmentCount++;
      }
    }
    return { orders: orderCount, shipments: shipmentCount };
  }

  async throughputSummary() {
    const all = await this.shipments.find();
    const byStatus = all.reduce((acc: Record<string, number>, s) => {
      const k = s.status || 'unknown';
      acc[k] = (acc[k] || 0) + 1;
      return acc;
    }, {});
    return { shipments: all.length, byStatus, orders: await this.orders.count() };
  }
}
