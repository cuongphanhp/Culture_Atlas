/** Trang so sánh văn hoá hai nước theo một chủ đề (prototype). */
import { Component, computed, inject, signal } from '@angular/core';
import { CategoryCode } from '../../core/models/culture.models';
import { CultureService } from '../../core/services/culture.service';
import { CiteChips } from '../../shared/components/badges';

/** Trang /compare. */
@Component({
  selector: 'ca-compare-page',
  imports: [CiteChips],
  templateUrl: './compare.page.html',
  styleUrl: './compare.page.css',
})
export class ComparePage {
  svc = inject(CultureService);
  a = signal('VN');
  b = signal('JP');
  topic = signal<CategoryCode>('gift_giving');
  result = this.svc.comparison;
  ca = computed(() => this.svc.country(this.a())!);
  cb = computed(() => this.svc.country(this.b())!);
  /** Đổi chỗ hai quốc gia. */
  swap() { const x = this.a(); this.a.set(this.b()); this.b.set(x); }
}
