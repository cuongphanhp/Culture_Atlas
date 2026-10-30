import { Component, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CategoryCode } from '../../core/models/culture.models';
import { CultureService } from '../../core/services/culture.service';
import { CiteChips, ConfidenceBadge, ScopeBadge } from '../../shared/components/badges';
import { PhotoComponent } from '../../shared/components/photo';

@Component({
  selector: 'ca-country-page',
  imports: [RouterLink, ScopeBadge, ConfidenceBadge, CiteChips, PhotoComponent],
  templateUrl: './country.page.html',
  styleUrl: './country.page.css',
})
export class CountryPage {
  svc = inject(CultureService);
  iso = input<string>('JP');
  category = signal<CategoryCode | null>(null);
  heritageTab = signal<'whc' | 'ich'>('whc');
  tipIcons = ['🙇', '🤲', '🥢', '👞', '🤫'];

  country = computed(() => this.svc.country(this.iso()) ?? this.svc.country('JP')!);
  data = computed(() => this.svc.data(this.country().iso2));
  entries = computed(() => this.svc.entries(this.country().iso2, this.category() ?? undefined));
  tips = computed(() => this.svc.tips(this.country().iso2));
  gallery = computed(() => this.svc.gallery(this.country().iso2));
  sourceIds = computed(() => [...new Set(this.entries().flatMap((e) => e.claims.flatMap((c) => c.sourceIds)))]);
  scaleRows = computed(() => {
    const s = this.data().scale;
    return s ? [
      { label: '🍜 Ẩm thực', items: s.cuisine, n: s.counts['cuisine'] },
      { label: '🏮 Lễ hội', items: s.holidays_and_festivals, n: s.counts['holidays_and_festivals'] },
      { label: '👘 Trang phục', items: s.clothing_and_accessories, n: s.counts['clothing_and_accessories'] },
      { label: '🏯 Địa danh', items: s.landmarks, n: s.counts['landmarks'] },
    ] : [];
  });
}
