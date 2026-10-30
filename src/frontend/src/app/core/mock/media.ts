// Ảnh văn hoá từ Wikimedia Commons (giấy phép mở) — ghi công đầy đủ trong credits.json.
import credits from '../../../../public/images/culture/credits.json';
import snapshot from './sources-snapshot.json';

export interface Photo { src: string; author: string; license: string; sourceUrl: string; caption?: string }

const C = credits as Record<string, { file: string; author: string; license: string; sourceUrl: string }>;
export function photo(key: string, caption?: string): Photo {
  const c = C[key];
  return { src: `images/culture/${key}.jpg`, author: c?.author ?? '', license: c?.license ?? '', sourceUrl: c?.sourceUrl ?? '', caption };
}

export const COUNTRY_PHOTO: Record<string, Photo> = {
  VN: photo('vn', 'Đèn lồng phố cổ Hội An'),
  TH: photo('th', 'Chùa Wat Arun, Bangkok'),
  JP: photo('jp', 'Cổng torii đền Fushimi Inari, Kyoto'),
  KR: photo('kr', 'Hanbok tại cung Gyeongbokgung'),
  CN: photo('cn', 'Tử Cấm Thành nhìn từ đồi Cảnh Sơn'),
  IN: photo('in', 'Taj Mahal lúc bình minh'),
  FR: photo('fr', 'Mont-Saint-Michel lúc hoàng hôn'),
  MX: photo('mx', 'Día de Muertos ở Oaxaca'),
  EG: photo('eg', 'Quần thể kim tự tháp Giza'),
  KE: photo('ke', 'Điệu nhảy Adumu của người Maasai'),
};

export const GALLERY: Record<string, Photo[]> = {
  JP: [photo('jp-fuji', 'Chùa Chureito và núi Phú Sĩ'), photo('jp-tea', 'Trà đạo'), photo('jp-kaiseki', 'Ẩm thực kaiseki'),
       photo('jp-seijin', 'Lễ trưởng thành Seijin-shiki'), photo('jp-himeji', 'Thành Himeji'), photo('jp-753', 'Lễ Shichi-Go-San')],
  VN: [photo('vn-halong', 'Vịnh Hạ Long'), photo('vn-tet', 'Đèn lồng Hội An')],
};

export const SNAPSHOT = snapshot as unknown as Snapshot;

export interface Snapshot {
  generatedAt: string;
  sources: Record<string, { name: string; license: string; url: string; records?: number }>;
  countries: Record<string, {
    worldHeritage: { total: number; cultural: number; natural: number; items: { id: string; name: string; category: string; year: number; summary: string; url: string }[] };
    intangibleHeritage: { total: number; items: { ref: string; name: string; year: number; list: string; summary: string; url: string }[] };
    museumObjects: { title: string; unit: string; thumbnail: string; url: string; license: string }[];
    europeana: { title: string; provider: string; thumbnail: string; url: string; rights: string }[];
    scale: null | { cuisine: string[]; holidays_and_festivals: string[]; clothing_and_accessories: string[]; landmarks: string[]; counts: Record<string, number> };
  }>;
}
