import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { CrmDeal } from './entities/deal.entity';
import { CrmContact } from './entities/contact.entity';
import { HubspotClient } from './hubspot.client';

@Injectable()
export class CrmService {
  constructor(
    @InjectRepository(CrmDeal) private readonly deals: Repository<CrmDeal>,
    @InjectRepository(CrmContact) private readonly contacts: Repository<CrmContact>,
    private readonly hubspot: HubspotClient,
  ) {}

  listDeals(): Promise<CrmDeal[]> {
    return this.deals.find({ order: { amount: 'DESC' }, take: 200 });
  }

  listContacts(): Promise<CrmContact[]> {
    return this.contacts.find({ take: 200 });
  }

  /** Pull live deals from HubSpot and upsert them into Postgres. */
  async syncDeals(): Promise<{ synced: number }> {
    const remote = await this.hubspot.fetchDeals(100);
    let synced = 0;
    for (const d of remote) {
      const existing = await this.deals.findOne({ where: { hubspotId: d.hubspotId } });
      const entity = this.deals.create({ ...existing, ...d });
      await this.deals.save(entity);
      synced++;
    }
    return { synced };
  }

  async pipelineSummary() {
    const all = await this.deals.find();
    const totalValue = all.reduce((s, d) => s + Number(d.amount || 0), 0);
    const won = all.filter((d) => d.isWon).length;
    const open = all.filter((d) => !d.isClosed).length;
    return { deals: all.length, totalValue, won, open };
  }
}
