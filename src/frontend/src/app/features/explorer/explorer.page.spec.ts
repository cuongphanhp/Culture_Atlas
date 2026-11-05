import { $, $$, render, text } from '../../../testing/render';
import { ExplorerPage } from './explorer.page';

describe('Explorer (US01, US05)', () => {
  it('[AC01.1] panel xem nhanh có tên, thủ đô, độ phủ và nút "Xem hồ sơ văn hoá"', async () => {
    const f = await render(ExplorerPage);
    const peek = $(f, '.peek')!;
    expect(peek.textContent).toContain('Nhật Bản');
    expect(peek.textContent).toContain('Tokyo');
    expect(peek.textContent).toMatch(/\d+%/);
    expect(peek.querySelector('button')!.textContent).toContain('Xem hồ sơ văn hoá');
  });

  it.skip('[AC01.1] PENDING: panel xem nhanh hiện ngôn ngữ và tiền tệ', async () => {
    const f = await render(ExplorerPage);
    expect($(f, '.peek')!.textContent).toMatch(/Tiếng Nhật|Japanese/);
    expect($(f, '.peek')!.textContent).toMatch(/JPY|Yên/);
  });

  it.skip('[AC01.2] PENDING: quốc gia chưa có nội dung hiển thị "Chưa có trong giai đoạn này", không điều hướng', async () => {
    const f = await render(ExplorerPage);
    f.componentInstance.selected.set({ ...f.componentInstance.svc.country('KE')!, coverage: 0 });
    f.detectChanges();
    expect(text(f)).toContain('Chưa có trong giai đoạn này');
  });

  it('[AC05.1] lọc theo tên có dấu', async () => {
    const f = await render(ExplorerPage);
    f.componentInstance.query.set('Nhật');
    f.detectChanges();
    expect($$(f, '.dest-card h3').map((e) => e.textContent)).toEqual(['Nhật Bản']);
  });

  it.skip('[AC05.1] PENDING: gõ "nhat ban" (không dấu) vẫn ra "Nhật Bản"', async () => {
    const f = await render(ExplorerPage);
    f.componentInstance.query.set('nhat ban');
    f.detectChanges();
    expect($$(f, '.dest-card h3').map((e) => e.textContent)).toContain('Nhật Bản');
  });
});
