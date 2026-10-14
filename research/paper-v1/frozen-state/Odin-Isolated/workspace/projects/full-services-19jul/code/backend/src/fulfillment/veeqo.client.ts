import { Injectable, Logger } from '@nestjs/common';
import axios, { AxiosInstance } from 'axios';

/**
 * Veeqo fulfillment client. Reads VEEQO_API_KEY from the environment.
 * Pulls orders and their shipment/tracking status.
 */
@Injectable()
export class VeeqoClient {
  private readonly logger = new Logger(VeeqoClient.name);
  private readonly http: AxiosInstance;

  constructor() {
    this.http = axios.create({
      baseURL: process.env.VEEQO_BASE_URL || 'https://api.veeqo.com',
      timeout: 15000,
      headers: {
        'x-api-key': process.env.VEEQO_API_KEY || '',
        'Content-Type': 'application/json',
      },
    });
  }

  async fetchOrders(pageSize = 50): Promise<any[]> {
    try {
      const { data } = await this.http.get('/orders', { params: { page_size: pageSize } });
      const rows = Array.isArray(data) ? data : data?.orders || [];
      return rows.map((o: any) => ({
        veeqoId: String(o.id),
        number: o.number,
        status: o.status,
        totalPrice: Number(o.total_price || 0),
        customerName: o.customer?.full_name || o.deliver_to?.full_name,
        placedAt: o.created_at ? new Date(o.created_at) : null,
        shipments: (o.allocations || o.shipments || []).map((s: any) => ({
          veeqoId: String(s.id),
          carrier: s.carrier || s.shipment?.carrier,
          trackingNo: s.tracking_number || s.shipment?.tracking_number,
          status: s.status || (s.shipped_at ? 'shipped' : 'pending'),
          shippedAt: s.shipped_at ? new Date(s.shipped_at) : null,
        })),
      }));
    } catch (err: any) {
      this.logger.warn(`Veeqo fetchOrders failed: ${err?.message}`);
      throw err;
    }
  }
}
