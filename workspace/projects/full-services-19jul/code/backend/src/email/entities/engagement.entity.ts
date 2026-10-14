import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity('email_engagement')
export class EmailEngagement {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'campaign_id', type: 'uuid', nullable: true })
  campaignId: string;

  @Column({ name: 'klaviyo_id', type: 'text', nullable: true })
  klaviyoId: string;

  @Column({ type: 'int', default: 0 })
  recipients: number;

  @Column({ type: 'int', default: 0 })
  delivered: number;

  @Column({ type: 'int', default: 0 })
  opens: number;

  @Column({ type: 'int', default: 0 })
  clicks: number;

  @Column({ type: 'int', default: 0 })
  bounces: number;

  @Column({ type: 'int', default: 0 })
  unsubscribes: number;

  @CreateDateColumn({ name: 'recorded_at' })
  recordedAt: Date;
}
