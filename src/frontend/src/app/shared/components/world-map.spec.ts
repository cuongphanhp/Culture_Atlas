import { COUNTRIES } from '../../core/mock/mock-data';
import { $, render } from '../../../testing/render';
import { WorldMap } from './world-map';

describe('WorldMap (US01)', () => {
  it('[AC01.3] bản đồ có role="img" và aria-label', async () => {
    const f = await render(WorldMap, { countries: COUNTRIES });
    const svg = $(f, 'svg')!;
    expect(svg.getAttribute('role')).toBe('img');
    expect(svg.getAttribute('aria-label')).toBeTruthy();
  });

  it('[AC01.1] bấm vào quốc gia có nội dung phát sự kiện pick', async () => {
    const f = await render(WorldMap, { countries: COUNTRIES });
    let picked = '';
    f.componentInstance.pick.subscribe((c) => (picked = c.iso2));
    $(f, 'path.on')!.dispatchEvent(new MouseEvent('click'));
    expect(COUNTRIES.map((c) => c.iso2)).toContain(picked);
  });

  it.skip('[AC01.3] PENDING: có danh sách quốc gia thay thế, Tab tới được bằng bàn phím', async () => {
    const f = await render(WorldMap, { countries: COUNTRIES });
    const items = f.nativeElement.querySelectorAll('[data-testid="country-list"] button');
    expect(items.length).toBeGreaterThan(0);
  });
});
