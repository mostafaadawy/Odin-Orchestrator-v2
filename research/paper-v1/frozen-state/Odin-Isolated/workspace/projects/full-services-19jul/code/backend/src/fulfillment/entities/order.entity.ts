import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity('fulfillment_orders')
export class FulfillmentOrder {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'veeqo_id', type: 'text', unique: true, nullable: true })
  veeqoId: string;

  @Column({ type: 'text', nullable: true })
  number: string;

  @Column({ type: 'text', nullable: true })
  status: string;

  @Column({ name: 'total_price', type: 'numeric', precision: 14, scale: 2, default: 0 })
  totalPrice: number;

  @Column({ name: 'customer_name', type: 'text', nullable: true })
  customerName: string;

  @Column({ name: 'placed_at', type: 'timestamptz', nullable: true })
  placedAt: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
