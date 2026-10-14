import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn, UpdateDateColumn } from 'typeorm';

@Entity('support_tickets')
export class SupportTicket {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'text' })
  subject: string;

  @Column({ type: 'text', nullable: true })
  body: string;

  @Column({ type: 'text', default: 'open' })
  status: string; // open | pending | resolved | closed

  @Column({ type: 'text', default: 'normal' })
  priority: string;

  @Column({ name: 'contact_id', type: 'uuid', nullable: true })
  contactId: string;

  @Column({ type: 'text', nullable: true })
  assignee: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
