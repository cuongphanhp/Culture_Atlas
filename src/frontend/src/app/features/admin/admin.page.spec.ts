import { $$, render } from '../../../testing/render';
import { AdminPage } from './admin.page';

describe('Admin (US16–US19)', () => {
  it('[AC19.1] ô độ phủ có < 3 claim được tô cảnh báo', async () => {
    const f = await render(AdminPage);
    const cells = $$(f, '.cell');
    expect(cells.length).toBeGreaterThan(0);
    for (const c of cells) expect(c.classList.contains('low')).toBe(Number(c.textContent) < 3);
  });

  it.skip('[AC19.2] PENDING: bấm ô độ phủ mở danh sách bài viết quốc gia × danh mục', async () => {
    const f = await render(AdminPage);
    $$(f, '.cell')[0].click();
    f.detectChanges();
    expect($$(f, '[data-testid="cell-entries"]').length).toBe(1);
  });

  it.skip('[AC16.2] PENDING: từ chối bắt buộc nhập lý do', async () => {
    const f = await render(AdminPage);
    expect($$(f, '[data-testid="reject-reason"][required]').length).toBeGreaterThan(0);
  });

  it.skip('[AC15.2] PENDING: token hết hạn → chuyển về trang đăng nhập', async () => {
    expect(true).toBe(false);
  });
});
