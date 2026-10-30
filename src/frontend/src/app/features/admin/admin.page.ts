import { Component, inject, signal } from '@angular/core';
import { coverageCell } from '../../core/mock/mock-data';
import { CultureService } from '../../core/services/culture.service';

@Component({
  selector: 'ca-admin-page',
  templateUrl: './admin.page.html',
  styleUrl: './admin.page.css',
})
export class AdminPage {
  svc = inject(CultureService);
  tab = signal<'all' | 'ai_generated' | 'user_report'>('all');
  cell = coverageCell;
  typeLabel: Record<string, string> = { entry: 'Bài viết', quiz: 'Quiz', comparison: 'So sánh', feedback: 'Báo cáo' };
  originLabel: Record<string, string> = { ai_generated: 'AI sinh', editor: 'Biên tập viên', user_report: 'Người dùng' };
  stats = [
    { label: 'Chờ duyệt', value: 18, tone: 'gold' },
    { label: 'Báo cáo sai mở', value: 4, tone: 'red' },
    { label: 'Claim đã duyệt', value: '1.284', tone: 'teal' },
    { label: 'Citation correctness', value: '92%', tone: 'teal' },
  ];
  sources() {
    const state: Record<string, [string, string]> = {
      unesco_whc: ['published', 'Đã đồng bộ'], unesco_ich: ['published', 'Đã đồng bộ'], smithsonian: ['published', 'Đã đồng bộ (CC0)'],
      europeana: ['in_review', 'Cần kiểm tra rights'], scale: ['draft', 'Chỉ tham khảo'], rest_countries: ['flagged', 'Cần token v5'],
    };
    return Object.entries(this.svc.snapshotInfo.sources).map(([key, v]) => ({ key, ...v, state: state[key][0], stateLabel: state[key][1] }));
  }
  rows() {
    const t = this.tab();
    return this.svc.reviewQueue.filter((r) => t === 'all' || r.origin === t);
  }
}
