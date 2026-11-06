import { $$, render, text } from '../../../testing/render';
import { CountryPage } from './country.page';

describe('Country profile (US02, US03)', () => {
  it('[AC02.1] có 12 chip danh mục (+ "Tất cả") và thẻ "5 điều cần biết"', async () => {
    const f = await render(CountryPage, { iso: 'JP' });
    expect($$(f, '.cats .cat').length).toBe(13);
    expect(text(f)).toContain('Hãy biết 5 điều này');
    expect($$(f, '.tip').length).toBeLessThanOrEqual(5);
  });

  it('[AC02.2] chọn danh mục chỉ hiện bài thuộc danh mục đó', async () => {
    const f = await render(CountryPage, { iso: 'JP' });
    f.componentInstance.category.set('gift_giving');
    f.detectChanges();
    expect(f.componentInstance.entries().every((e) => e.category === 'gift_giving')).toBe(true);
  });

  it.skip('[AC02.2] PENDING: danh mục rỗng hiển thị trạng thái rỗng kèm gợi ý hỏi AI', async () => {
    const f = await render(CountryPage, { iso: 'KE' });
    f.componentInstance.category.set('business_culture');
    f.detectChanges();
    expect(text(f)).toMatch(/Hỏi AI/);
  });

  it('[AC03.2] mỗi claim có ít nhất 1 chip nguồn kèm tooltip nhà xuất bản', async () => {
    const f = await render(CountryPage, { iso: 'JP' });
    const claims = $$(f, '.claims li');
    expect(claims.length).toBeGreaterThan(0);
    for (const li of claims) {
      const chips = li.querySelectorAll('.cite');
      expect(chips.length).toBeGreaterThan(0);
      expect(chips[0].getAttribute('title')).toBeTruthy();
    }
  });

  it.skip('[AC02.3] PENDING: <title> và meta description theo quốc gia (SSR)', async () => {
    await render(CountryPage, { iso: 'JP' });
    expect(document.title).toContain('Nhật Bản');
    expect(document.querySelector('meta[name="description"]')?.getAttribute('content')).toContain('Nhật Bản');
  });

  it.skip('[AC03.3] PENDING: claim unverified không hiển thị', async () => {
    const f = await render(CountryPage, { iso: 'JP' });
    expect(text(f)).not.toContain('Chưa kiểm chứng');
  });
});

describe('Country profile — ảnh nền theo quốc gia (AC01.4)', () => {
  for (const iso of ['JP', 'VN', 'FR', 'KE']) {
    it('[AC01.4] hồ sơ ' + iso + ' dùng ảnh nền của chính quốc gia đó', async () => {
      const f = await render(CountryPage, { iso });
      const svc = f.componentInstance.svc;
      const img = (f.nativeElement as HTMLElement).querySelector('.banner-bg img')!;
      expect(img.getAttribute('src')).toBe(svc.photo(iso).src);
      expect(text(f)).toContain(svc.country(iso)!.nameVi);
    });
  }
});
