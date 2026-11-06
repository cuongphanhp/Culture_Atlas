// Ảnh văn hoá từ Wikimedia Commons (giấy phép mở) — ghi công trong photo-credits.json (bản sao của src/media-seed/culture/credits.json).
// File ảnh nằm ở object storage (MinIO): nạp bằng `worker.cli seed-media`, phục vụ qua /media/* (nginx → MinIO).
import credits from './photo-credits.json';
import snapshot from './sources-snapshot.json';

/** Ảnh kèm ghi công (BR08); `src` trỏ tới /media/* trên object storage. */
export interface Photo { src: string; author: string; license: string; sourceUrl: string; caption?: string }

const C = credits as Record<string, { file: string; author: string; license: string; sourceUrl: string }>;
/** Ảnh theo khoá trong photo-credits.json. */
export function photo(key: string, caption?: string): Photo {
  const c = C[key];
  return { src: `/media/photos/${c?.file ?? key + '.jpg'}`, author: c?.author ?? '', license: c?.license ?? '', sourceUrl: c?.sourceUrl ?? '', caption };
}

/** Ảnh nền / ảnh đại diện của từng quốc gia. */
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

/** Bộ ảnh của trang quốc gia. */
export const GALLERY: Record<string, Photo[]> = {
  JP: [photo('jp-fuji', 'Chùa Chureito và núi Phú Sĩ'), photo('jp-tea', 'Trà đạo'), photo('jp-kaiseki', 'Ẩm thực kaiseki'),
       photo('jp-seijin', 'Lễ trưởng thành Seijin-shiki'), photo('jp-himeji', 'Thành Himeji'), photo('jp-753', 'Lễ Shichi-Go-San')],
  VN: [photo('vn-halong', 'Vịnh Hạ Long'), photo('vn-tet', 'Đèn lồng Hội An')],
};

/** Snapshot số liệu thật từ các nguồn mở (sinh bởi worker). */
export const SNAPSHOT = snapshot as unknown as Snapshot;

/** Cấu trúc sources-snapshot.json. */
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
