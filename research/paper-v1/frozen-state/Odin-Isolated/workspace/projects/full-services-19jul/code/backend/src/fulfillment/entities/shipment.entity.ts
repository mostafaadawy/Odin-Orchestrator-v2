import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity('fulfillment_shipments')
export class FulfillmentShipment {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'veeqo_id', type: 'text', unique: true, nullable: true })
  veeqoId: string;

  @Column({ name: 'order_id', type: 'uuid', nullable: true })
  orderId: string;

  @Column({ type: 'text', nullable: true })
  carrier: string;

  @Column({ name: 'tracking_no', type: 'text', nullable: true })
  trackingNo: string;

  @Column({ type: 'text', nullable: true })
  status: string; // pending | shipped | delivered

  @Column({ name: 'shipped_at', type: 'timestamptz', nullable: true })
  shippedAt: Date;

  @Column({ name: 'delivered_at', type: 'timestamptz', nullable: true })
  deliveredAt: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
