/** Nguồn dữ liệu của giao diện (hiện là dữ liệu mẫu + snapshot nguồn mở; sẽ thay bằng Content API ở P2). */
import { Injectable } from '@angular/core';
import {
  CATEGORIES, COMPARISON_VN_JP, COUNTRIES, ENTRIES, FESTIVALS_THIS_MONTH, FIRST_TIME_TIPS, HERITAGE,
  QUIZ, REVIEW_QUEUE, SAMPLE_CHAT, SOURCES, THEMES, CHAT_SESSIONS,
} from '../mock/mock-data';
import { COUNTRY_PHOTO, GALLERY, SNAPSHOT, photo } from '../mock/media';
import { CategoryCode } from '../models/culture.models';

/**
 * Prototype: đọc dữ liệu mẫu đồng bộ.
 * Bản thật sẽ gọi Content API / AI API (xem docs/api/openapi.yaml) qua HttpClient.
 */
@Injectable({ providedIn: 'root' })
export class CultureService {
  readonly categories = CATEGORIES;
  readonly countries = COUNTRIES;
  readonly themes = THEMES;
  readonly festivals = FESTIVALS_THIS_MONTH;
  readonly sampleChat = SAMPLE_CHAT;
  readonly comparison = COMPARISON_VN_JP;
  readonly quiz = QUIZ;
  readonly reviewQueue = REVIEW_QUEUE;
  readonly sessions = CHAT_SESSIONS;
  readonly snapshotInfo = SNAPSHOT;
  readonly img = photo;

  /** Ảnh đại diện của quốc gia. */
  photo(iso: string) { return COUNTRY_PHOTO[iso.toUpperCase()]; }
  /** Bộ ảnh của trang quốc gia. */
  gallery(iso: string) { return GALLERY[iso.toUpperCase()] ?? []; }
  /** Số liệu thật từ snapshot nguồn mở (UNESCO, SCALE…). */
  data(iso: string) { return SNAPSHOT.countries[iso.toUpperCase()]; }

  /** Quốc gia theo mã ISO2. */
  country(iso: string) { return COUNTRIES.find((c) => c.iso2 === iso.toUpperCase()); }
  /** Bài viết của quốc gia, lọc theo danh mục nếu có. */
  entries(iso: string, category?: CategoryCode) {
    return ENTRIES.filter((e) => e.countryIso === iso.toUpperCase() && (!category || e.category === category));
  }
  /** Mẹo cho người lần đầu đến. */
  tips(iso: string) { return FIRST_TIME_TIPS[iso.toUpperCase()] ?? []; }
  /** Di sản tiêu biểu. */
  heritage(iso: string) { return HERITAGE[iso.toUpperCase()] ?? []; }
  /** Nguồn theo id. */
  source(id: number) { return SOURCES.find((s) => s.id === id); }
  /** Danh mục theo mã. */
  category(code: CategoryCode) { return CATEGORIES.find((c) => c.code === code); }
}
