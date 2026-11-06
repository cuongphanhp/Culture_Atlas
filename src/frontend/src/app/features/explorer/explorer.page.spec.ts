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

describe('Explorer — ảnh nền theo quốc gia (AC01.4)', () => {
  it('[AC01.4] bấm ảnh nhỏ của từng quốc gia ở hero → ảnh nền đổi theo quốc gia đó', async () => {
    const f = await render(ExplorerPage);
    const svc = f.componentInstance.svc;
    const thumbs = $$(f, '.hero-pick .thumb');
    expect(thumbs.length).toBe(f.componentInstance.heroIsos.length);
    f.componentInstance.heroIsos.forEach((iso, i) => {
      thumbs[i].click();
      f.detectChanges();
      expect($(f, '.hero-bg img')!.getAttribute('src')).toBe(svc.photo(iso).src);
      expect(thumbs[i].classList).toContain('on');
      expect($(f, '.hero-caption')!.textContent).toContain(svc.country(iso)!.nameVi);
    });
  });

  it('[AC01.4] bấm quốc gia trên bản đồ → ảnh nền hero và ảnh panel xem nhanh đổi theo quốc gia đó', async () => {
    const f = await render(ExplorerPage);
    const svc = f.componentInstance.svc;
    for (const iso of ['KR', 'EG', 'VN']) {
      const country = svc.country(iso)!;
      const path = $$(f, 'ca-world-map path.on').find((p) => p.querySelector('title')!.textContent!.startsWith(country.nameVi))!;
      path.dispatchEvent(new MouseEvent('click'));
      f.detectChanges();
      expect($(f, '.hero-bg img')!.getAttribute('src')).toBe(svc.photo(iso).src);
      expect($(f, '.peek .peek-img img')!.getAttribute('src')).toBe(svc.photo(iso).src);
      expect($(f, '.peek h2')!.textContent).toContain(country.nameVi);
    }
  });

  it('[AC01.4] mỗi quốc gia có ảnh nền riêng (không dùng chung một ảnh)', async () => {
    const f = await render(ExplorerPage);
    const svc = f.componentInstance.svc;
    const srcs = svc.countries.map((c) => svc.photo(c.iso2)?.src);
    expect(srcs.every(Boolean)).toBe(true);
    expect(new Set(srcs).size).toBe(srcs.length);
  });
});
