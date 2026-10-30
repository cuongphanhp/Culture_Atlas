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

  photo(iso: string) { return COUNTRY_PHOTO[iso.toUpperCase()]; }
  gallery(iso: string) { return GALLERY[iso.toUpperCase()] ?? []; }
  data(iso: string) { return SNAPSHOT.countries[iso.toUpperCase()]; }

  country(iso: string) { return COUNTRIES.find((c) => c.iso2 === iso.toUpperCase()); }
  entries(iso: string, category?: CategoryCode) {
    return ENTRIES.filter((e) => e.countryIso === iso.toUpperCase() && (!category || e.category === category));
  }
  tips(iso: string) { return FIRST_TIME_TIPS[iso.toUpperCase()] ?? []; }
  heritage(iso: string) { return HERITAGE[iso.toUpperCase()] ?? []; }
  source(id: number) { return SOURCES.find((s) => s.id === id); }
  category(code: CategoryCode) { return CATEGORIES.find((c) => c.code === code); }
}
