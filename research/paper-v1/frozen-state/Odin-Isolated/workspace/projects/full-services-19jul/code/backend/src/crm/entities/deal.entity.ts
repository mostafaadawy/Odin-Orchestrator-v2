import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn, UpdateDateColumn } from 'typeorm';

@Entity('crm_deals')
export class CrmDeal {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'hubspot_id', type: 'text', unique: true, nullable: true })
  hubspotId: string;

  @Column({ type: 'text' })
  name: string;

  @Column({ type: 'text', nullable: true })
  stage: string;

  @Column({ type: 'text', nullable: true })
  pipeline: string;

  @Column({ type: 'numeric', precision: 14, scale: 2, default: 0 })
  amount: number;

  @Column({ name: 'close_date', type: 'timestamptz', nullable: true })
  closeDate: Date;

  @Column({ name: 'is_closed', type: 'boolean', default: false })
  isClosed: boolean;

  @Column({ name: 'is_won', type: 'boolean', default: false })
  isWon: boolean;

  @Column({ name: 'contact_id', type: 'uuid', nullable: true })
  contactId: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
