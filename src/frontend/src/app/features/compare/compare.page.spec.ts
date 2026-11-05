import { CultureService } from '../../core/services/culture.service';
import { $, $$, render, text } from '../../../testing/render';
import { ComparePage } from './compare.page';

describe('Culture comparison (US11)', () => {
  it('[AC11.1] bản đã duyệt hiển thị nhãn "Đã được biên tập viên duyệt"', async () => {
    const f = await render(ComparePage);
    expect(text(f)).toContain('Đã được biên tập viên duyệt');
  });

  it('[AC11.2] ô thiếu bằng chứng hiển thị "Chưa đủ nguồn để kết luận"', async () => {
    const svc = new CultureService();
    Object.assign(svc, { comparison: { ...svc.comparison, rows: [{ ...svc.comparison.rows[0], a: null }] } });
    const f = await render(ComparePage, {}, [{ provide: CultureService, useValue: svc }]);
    expect($(f, 'td .na')!.textContent).toContain('Chưa đủ nguồn để kết luận');
  });

  it('[AC11.2] ô có nội dung luôn kèm chip nguồn', async () => {
    const f = await render(ComparePage);
    for (const td of $$(f, 'tbody td:not(.aspect)')) {
      if (!td.querySelector('.na')) expect(td.querySelectorAll('.cite').length).toBeGreaterThan(0);
    }
  });

  it.skip('[AC11.3] PENDING: bản AI sinh chưa duyệt gắn nhãn "Chưa duyệt"', async () => {
    const f = await render(ComparePage);
    expect(text(f)).toContain('Chưa duyệt');
  });

  it.skip('[AC11.4] PENDING: chọn A = B thì nút So sánh bị vô hiệu kèm thông báo', async () => {
    const f = await render(ComparePage);
    f.componentInstance.b.set('VN');
    f.detectChanges();
    expect(($(f, '.picker .btn') as HTMLButtonElement).disabled).toBe(true);
    expect(text(f)).toMatch(/hai quốc gia khác nhau/i);
  });
});
