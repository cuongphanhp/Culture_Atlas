import { Component, input } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ClaimScope, Confidence } from '../../core/models/culture.models';
import { ConfidenceBadge, ScopeBadge } from './badges';

@Component({
  imports: [ScopeBadge, ConfidenceBadge],
  template: `<ca-scope-badge [scope]="scope()" /><ca-confidence-badge [level]="level()" />`,
})
class Host {
  scope = input<ClaimScope>('common_practice');
  level = input<Confidence>('verified');
}

describe('Badges — claim có phạm vi (US03)', () => {
  const cases: [ClaimScope, string][] = [
    ['common_practice', 'Phổ biến'], ['historical_tradition', 'Truyền thống lịch sử'],
    ['regional', 'Vùng miền'], ['community_specific', 'Cộng đồng cụ thể'],
  ];
  for (const [scope, label] of cases) {
    it(`[AC03.1] nhãn scope ${scope} → "${label}"`, () => {
      const f = TestBed.createComponent(Host);
      f.componentRef.setInput('scope', scope);
      f.detectChanges();
      expect(f.nativeElement.querySelector('.scope').textContent.trim()).toBe(label);
    });
  }

  it('[AC03.1] nhãn confidence hiển thị bằng tiếng Việt', () => {
    const f = TestBed.createComponent(Host);
    f.componentRef.setInput('level', 'partially_supported');
    f.detectChanges();
    expect(f.nativeElement.querySelector('.conf').textContent).toContain('Hỗ trợ một phần');
  });
});
