import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { SupportTicket } from './entities/ticket.entity';

@Injectable()
export class SupportService {
  constructor(
    @InjectRepository(SupportTicket) private readonly tickets: Repository<SupportTicket>,
  ) {}

  list(): Promise<SupportTicket[]> {
    return this.tickets.find({ order: { createdAt: 'DESC' }, take: 200 });
  }

  create(dto: Partial<SupportTicket>): Promise<SupportTicket> {
    return this.tickets.save(this.tickets.create(dto));
  }

  async transition(id: string, status: string): Promise<SupportTicket> {
    await this.tickets.update({ id }, { status });
    return this.tickets.findOne({ where: { id } });
  }

  async summary() {
    const all = await this.tickets.find();
    const byStatus = all.reduce((acc: Record<string, number>, t) => {
      acc[t.status] = (acc[t.status] || 0) + 1;
      return acc;
    }, {});
    return { tickets: all.length, byStatus };
  }
}
