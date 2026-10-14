import { Injectable, Logger } from '@nestjs/common';
import axios, { AxiosInstance } from 'axios';

/**
 * Thin HubSpot CRM client. Reads the API key from the environment
 * (HUBSPOT_API_KEY) — never hardcoded. Used to pull deals + contacts.
 */
@Injectable()
export class HubspotClient {
  private readonly logger = new Logger(HubspotClient.name);
  private readonly http: AxiosInstance;

  constructor() {
    this.http = axios.create({
      baseURL: process.env.HUBSPOT_BASE_URL || 'https://api.hubapi.com',
      timeout: 15000,
      headers: {
        Authorization: `Bearer ${process.env.HUBSPOT_API_KEY || ''}`,
        'Content-Type': 'application/json',
      },
    });
  }

  /** Fetch deals from the HubSpot CRM v3 objects API. */
  async fetchDeals(limit = 50): Promise<any[]> {
    try {
      const { data } = await this.http.get('/crm/v3/objects/deals', {
        params: { limit, properties: 'dealname,amount,dealstage,pipeline,closedate' },
      });
      return (data.results || []).map((d: any) => ({
        hubspotId: d.id,
        name: d.properties?.dealname,
        amount: Number(d.properties?.amount || 0),
        stage: d.properties?.dealstage,
        pipeline: d.properties?.pipeline,
        closeDate: d.properties?.closedate ? new Date(d.properties.closedate) : null,
      }));
    } catch (err: any) {
      this.logger.warn(`HubSpot fetchDeals failed: ${err?.message}`);
      throw err;
    }
  }

  async fetchContacts(limit = 50): Promise<any[]> {
    try {
      const { data } = await this.http.get('/crm/v3/objects/contacts', {
        params: { limit, properties: 'email,firstname,lastname,company,lifecyclestage' },
      });
      return (data.results || []).map((c: any) => ({
        hubspotId: c.id,
        email: c.properties?.email,
        firstName: c.properties?.firstname,
        lastName: c.properties?.lastname,
        company: c.properties?.company,
        lifecycle: c.properties?.lifecyclestage,
      }));
    } catch (err: any) {
      this.logger.warn(`HubSpot fetchContacts failed: ${err?.message}`);
      throw err;
    }
  }
}
