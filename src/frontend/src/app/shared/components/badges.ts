/** Nhãn dùng chung: phạm vi claim, độ tin cậy, chip trích dẫn nguồn. */
import { Component, computed, inject, input } from '@angular/core';
import { ClaimScope, Confidence } from '../../core/models/culture.models';
import { CultureService } from '../../core/services/culture.service';

const SCOPE_LABEL: Record<ClaimScope, string> = {
  common_practice: 'Phổ biến',
  historical_tradition: 'Truyền thống lịch sử',
  regional: 'Vùng miền',
  community_specific: 'Cộng đồng cụ thể',
};
const CONF_LABEL: Record<Confidence | 'supported' | 'inferred' | 'insufficient' | 'none', string> = {
  verified: 'Đã kiểm chứng', partially_supported: 'Hỗ trợ một phần', unverified: 'Chưa kiểm chứng',
  supported: 'Có nguồn trực tiếp', inferred: 'Suy luận từ nguồn', insufficient: 'Chưa đủ nguồn', none: '',
};

/** Phạm vi áp dụng của một claim (phổ biến / vùng miền…). */
@Component({
  selector: 'ca-scope-badge',
  template: `<span class="badge scope">{{ label() }}</span>`,
})
export class ScopeBadge {
  scope = input.required<ClaimScope>();
  label = computed(() => SCOPE_LABEL[this.scope()]);
}

/** Độ tin cậy của claim hoặc câu trả lời AI. */
@Component({
  selector: 'ca-confidence-badge',
  template: `<span class="badge conf" [class]="'conf-' + level()"><span class="dot"></span>{{ label() }}</span>`,
})
export class ConfidenceBadge {
  level = input.required<Confidence | 'supported' | 'inferred' | 'insufficient' | 'none'>();
  label = computed(() => CONF_LABEL[this.level()]);
}

/** Danh sách số nguồn, rê chuột xem nhà xuất bản và tiêu đề. */
@Component({
  selector: 'ca-cite',
  template: `@for (id of ids(); track id) {<a class="cite" [title]="titleOf(id)" href="javascript:void(0)">{{ id }}</a>}`,
})
export class CiteChips {
  private svc = inject(CultureService);
  ids = input.required<number[]>();
  /** Tooltip của một nguồn. */
  titleOf(id: number) { const s = this.svc.source(id); return s ? `${s.publisher} — ${s.title}` : ''; }
}
