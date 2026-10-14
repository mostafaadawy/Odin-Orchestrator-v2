import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn, UpdateDateColumn } from 'typeorm';

@Entity('crm_contacts')
export class CrmContact {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'hubspot_id', type: 'text', unique: true, nullable: true })
  hubspotId: string;

  @Column({ type: 'text', nullable: true })
  email: string;

  @Column({ name: 'first_name', type: 'text', nullable: true })
  firstName: string;

  @Column({ name: 'last_name', type: 'text', nullable: true })
  lastName: string;

  @Column({ type: 'text', nullable: true })
  company: string;

  @Column({ type: 'text', nullable: true })
  lifecycle: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
