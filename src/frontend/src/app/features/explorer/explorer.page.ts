import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Country } from '../../core/models/culture.models';
import { CultureService } from '../../core/services/culture.service';
import { PhotoComponent } from '../../shared/components/photo';
import { WorldMap } from '../../shared/components/world-map';

@Component({
  selector: 'ca-explorer-page',
  imports: [WorldMap, RouterLink, PhotoComponent],
  templateUrl: './explorer.page.html',
  styleUrl: './explorer.page.css',
})
export class ExplorerPage {
  svc = inject(CultureService);
  private router = inject(Router);
  query = signal('');
  region = signal('Tất cả');
  selected = signal<Country | null>(this.svc.country('JP') ?? null);
  regions = ['Tất cả', ...new Set(this.svc.countries.map((c) => c.region))];
  heroIsos = ['JP', 'VN', 'IN', 'FR', 'MX'];
  heroIndex = signal(0);
  hero = computed(() => this.svc.country(this.heroIsos[this.heroIndex()])!);

  features = [
    { title: 'AI Cultural Guide', text: 'Hỏi “vì sao” — câu trả lời luôn có nguồn.', img: 'jp-kyoto', link: '/guide', icon: '✦' },
    { title: 'So sánh văn hoá', text: 'Việt Nam và thế giới, khác nhau ở đâu?', img: 'jp-tea', link: '/compare', icon: '⇄' },
    { title: 'Culture Quiz', text: '2 phút để nhớ lâu hơn.', img: 'jp-753', link: '/quiz', icon: '?' },
    { title: 'Di sản UNESCO', text: 'Hơn 2.100 di sản vật thể & phi vật thể.', img: 'jp-himeji', link: '/countries/JP', icon: '🏯' },
  ];

  sources = computed(() => {
    const s = this.svc.snapshotInfo.sources;
    return [
      { key: 'unesco_whc', label: 'UNESCO World Heritage', value: `${s['unesco_whc'].records} di sản` },
      { key: 'unesco_ich', label: 'UNESCO Intangible Heritage', value: `${s['unesco_ich'].records} di sản phi vật thể` },
      { key: 'smithsonian', label: 'Smithsonian Open Access', value: 'Hiện vật CC0' },
      { key: 'europeana', label: 'Europeana', value: 'Tư liệu số châu Âu' },
      { key: 'scale', label: 'SCALE Cultural Data', value: '29 quốc gia · taxonomy' },
      { key: 'rest_countries', label: 'REST Countries', value: 'Hồ sơ quốc gia' },
    ].map((x) => ({ ...x, url: s[x.key].url }));
  });

  filtered = computed(() => {
    const q = this.query().trim().toLowerCase();
    return this.svc.countries.filter((c) =>
      (this.region() === 'Tất cả' || c.region === this.region()) &&
      (!q || c.nameVi.toLowerCase().includes(q) || c.nameEn.toLowerCase().includes(q)));
  });

  open(c: Country) { this.router.navigate(['/countries', c.iso2]); }
}
