import { Injectable, Logger } from '@nestjs/common';
import axios, { AxiosInstance } from 'axios';

/**
 * Klaviyo engagement client. Reads KLAVIYO_API_KEY from the environment.
 * Pulls campaigns/flows and their open/click engagement metrics.
 */
@Injectable()
export class KlaviyoClient {
  private readonly logger = new Logger(KlaviyoClient.name);
  private readonly http: AxiosInstance;

  constructor() {
    this.http = axios.create({
      baseURL: process.env.KLAVIYO_BASE_URL || 'https://a.klaviyo.com/api',
      timeout: 15000,
      headers: {
        Authorization: `Klaviyo-API-Key ${process.env.KLAVIYO_API_KEY || ''}`,
        accept: 'application/json',
        revision: '2024-10-15',
      },
    });
  }

  /** Fetch flows (live/draft) — mirrors the platform's live-data shape. */
  async fetchFlows(): Promise<any[]> {
    try {
      const { data } = await this.http.get('/flows', { params: { 'page[size]': 50 } });
      return (data.data || []).map((f: any) => ({
        klaviyoId: f.id,
        name: f.attributes?.name,
        status: f.attributes?.status,
        channel: 'email',
      }));
    } catch (err: any) {
      this.logger.warn(`Klaviyo fetchFlows failed: ${err?.message}`);
      throw err;
    }
  }

  async fetchCampaigns(): Promise<any[]> {
    try {
      const { data } = await this.http.get('/campaigns', {
        params: { 'filter': "equals(messages.channel,'email')" },
      });
      return (data.data || []).map((c: any) => ({
        klaviyoId: c.id,
        name: c.attributes?.name,
        status: c.attributes?.status,
        sendTime: c.attributes?.send_time ? new Date(c.attributes.send_time) : null,
      }));
    } catch (err: any) {
      this.logger.warn(`Klaviyo fetchCampaigns failed: ${err?.message}`);
      throw err;
    }
  }
}
