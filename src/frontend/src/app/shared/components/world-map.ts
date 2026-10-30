import { Component, computed, input, output } from '@angular/core';
import { geoNaturalEarth1, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import type { GeometryCollection, Topology } from 'topojson-specification';
import type { Feature, FeatureCollection, Geometry } from 'geojson';
import world from 'world-atlas/countries-110m.json';
import { Country } from '../../core/models/culture.models';

const W = 960, H = 480;
const topo = world as unknown as Topology<{ countries: GeometryCollection }>;
const geo = feature(topo, topo.objects.countries) as FeatureCollection<Geometry, { name: string }>;
const projection = geoNaturalEarth1().fitExtent([[8, 8], [W - 8, H - 8]], { type: 'Sphere' });
const path = geoPath(projection);

/** Bản đồ thế giới SVG (Natural Earth qua world-atlas). Bản thật dùng MapLibre GL. */
@Component({
  selector: 'ca-world-map',
  template: `
    <svg [attr.viewBox]="'0 0 ' + w + ' ' + h" role="img" aria-label="Bản đồ văn hoá thế giới">
      <path class="sphere" [attr.d]="sphere" />
      @for (s of shapes(); track s.id) {
        <path [attr.d]="s.d" [class.on]="s.country" [class.sel]="s.country?.iso2 === selected()"
              [style.--cov]="s.country ? s.country.coverage / 100 : 0"
              (click)="s.country && pick.emit(s.country)">
          <title>{{ s.country ? s.country.nameVi + ' · độ phủ ' + s.country.coverage + '%' : s.name }}</title>
        </path>
      }
      @for (p of pins(); track p.c.iso2) {
        <g class="pin" [attr.transform]="'translate(' + p.x + ',' + p.y + ')'" (click)="pick.emit(p.c)">
          <circle r="11" /><text y="4" text-anchor="middle">{{ p.c.flag }}</text>
        </g>
      }
    </svg>`,
  styleUrl: './world-map.css',
})
export class WorldMap {
  countries = input.required<Country[]>();
  selected = input<string | null>(null);
  pick = output<Country>();
  w = W; h = H;
  sphere = path({ type: 'Sphere' }) ?? '';

  shapes = computed(() => {
    const byNum = new Map(this.countries().map((c) => [c.isoNumeric, c]));
    return geo.features.map((f: Feature<Geometry, { name: string }>) => ({
      id: String(f.id), name: f.properties.name, d: path(f) ?? '', country: byNum.get(String(f.id)),
    }));
  });

  pins = computed(() => {
    const byNum = new Map(geo.features.map((f) => [String(f.id), f]));
    return this.countries().filter((c) => c.featured).flatMap((c) => {
      const f = byNum.get(c.isoNumeric);
      if (!f) return [];
      const [x, y] = path.centroid(f);
      return [{ c, x, y }];
    });
  });
}
