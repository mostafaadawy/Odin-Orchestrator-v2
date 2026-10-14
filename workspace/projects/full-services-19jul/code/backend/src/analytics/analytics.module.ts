import { Module } from '@nestjs/common';
import { AnalyticsController } from './analytics.controller';
import { AnalyticsService } from './analytics.service';

// Analytics operations layer — reads the SQL views (0002_analytics_views.sql)
// via the shared TypeORM DataSource; no extra entities needed.
@Module({
  controllers: [AnalyticsController],
  providers: [AnalyticsService],
  exports: [AnalyticsService],
})
export class AnalyticsModule {}
