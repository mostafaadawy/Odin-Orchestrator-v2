import { Injectable } from '@nestjs/common';
import { InjectDataSource } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';

/**
 * Analytics service — reads the SQL views defined in
 * prisma/migrations/0002_analytics_views.sql and returns aggregated
 * operations metrics (pipeline value, open/close & win rates, campaign
 * opens/clicks, shipment throughput). All heavy aggregation is pushed to
 * Postgres; this layer just shapes the rows for the API.
 */
@Injectable()
export class AnalyticsService {
  constructor(@InjectDataSource() private readonly db: DataSource) {}

  private async one<T = any>(sql: string): Promise<T | null> {
    const rows = await this.db.query(sql);
    return (rows && rows[0]) || null;
  }

  private rows<T = any>(sql: string): Promise<T[]> {
    return this.db.query(sql);
  }

  /** CRM: pipeline value + open/close/win rates, plus per-stage breakdown. */
  async crm() {
    const [summary, byStage] = await Promise.all([
      this.one('SELECT * FROM analytics_crm_pipeline'),
      this.rows('SELECT * FROM analytics_crm_by_stage'),
    ]);
    return { summary, byStage };
  }

  /** Email: overall opens/clicks/deliverability + per-campaign engagement. */
  async email() {
    const [overview, campaigns] = await Promise.all([
      this.one('SELECT * FROM analytics_email_overview'),
      this.rows('SELECT * FROM analytics_email_campaigns ORDER BY opens DESC'),
    ]);
    return { overview, campaigns };
  }

  /** Fulfillment: shipment throughput by status + order/shipment overview. */
  async fulfillment() {
    const [overview, throughput] = await Promise.all([
      this.one('SELECT * FROM analytics_fulfillment_overview'),
      this.rows('SELECT * FROM analytics_fulfillment_throughput'),
    ]);
    return { overview, throughput };
  }

  /** One unified operations snapshot for the analytics dashboard. */
  async overview() {
    const [crm, email, fulfillment] = await Promise.all([
      this.crm(),
      this.email(),
      this.fulfillment(),
    ]);
    return {
      generatedAt: new Date().toISOString(),
      crm,
      email,
      fulfillment,
    };
  }
}
