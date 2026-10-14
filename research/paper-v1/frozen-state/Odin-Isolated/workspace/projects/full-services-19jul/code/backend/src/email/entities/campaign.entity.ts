import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity('email_campaigns')
export class EmailCampaign {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'klaviyo_id', type: 'text', unique: true, nullable: true })
  klaviyoId: string;

  @Column({ type: 'text' })
  name: string;

  @Column({ type: 'text', nullable: true })
  status: string; // live | draft

  @Column({ type: 'text', default: 'email' })
  channel: string;

  @Column({ name: 'send_time', type: 'timestamptz', nullable: true })
  sendTime: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
