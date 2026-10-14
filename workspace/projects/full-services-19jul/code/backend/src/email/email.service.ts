import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { EmailCampaign } from './entities/campaign.entity';
import { EmailEngagement } from './entities/engagement.entity';
import { KlaviyoClient } from './klaviyo.client';

@Injectable()
export class EmailService {
  constructor(
    @InjectRepository(EmailCampaign) private readonly campaigns: Repository<EmailCampaign>,
    @InjectRepository(EmailEngagement) private readonly engagement: Repository<EmailEngagement>,
    private readonly klaviyo: KlaviyoClient,
  ) {}

  listCampaigns(): Promise<EmailCampaign[]> {
    return this.campaigns.find({ take: 200 });
  }

  /** Pull live flows from Klaviyo and upsert them as campaigns. */
  async syncFlows(): Promise<{ synced: number; live: number; draft: number }> {
    const flows = await this.klaviyo.fetchFlows();
    let synced = 0;
    for (const f of flows) {
      const existing = await this.campaigns.findOne({ where: { klaviyoId: f.klaviyoId } });
      await this.campaigns.save(this.campaigns.create({ ...existing, ...f }));
      synced++;
    }
    const live = flows.filter((f) => f.status === 'live').length;
    const draft = flows.filter((f) => f.status === 'draft').length;
    return { synced, live, draft };
  }

  /** Aggregate engagement across all recorded metrics. */
  async engagementSummary() {
    const rows = await this.engagement.find();
    const sum = (k: keyof EmailEngagement) =>
      rows.reduce((s, r) => s + Number((r[k] as number) || 0), 0);
    const delivered = sum('delivered');
    const opens = sum('opens');
    const clicks = sum('clicks');
    return {
      campaigns: await this.campaigns.count(),
      delivered,
      opens,
      clicks,
      openRate: delivered ? +(opens / delivered).toFixed(4) : 0,
      clickRate: delivered ? +(clicks / delivered).toFixed(4) : 0,
    };
  }
}
