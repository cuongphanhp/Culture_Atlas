import { Component, computed, inject, input, signal } from '@angular/core';
import { ChatMessage } from '../../core/models/culture.models';
import { CultureService } from '../../core/services/culture.service';
import { ConfidenceBadge } from '../../shared/components/badges';

type Seg = { kind: 'text' | 'bold' | 'cite'; value: string };

// Từ khoá nhận diện quốc gia trong hội thoại (bản thật: Router của Agent trả về `countries[]`).
const KEYWORDS: Record<string, string[]> = {
  VN: ['việt nam', 'vietnam', 'lì xì', 'tết', 'hội an'], JP: ['nhật', 'japan', 'omiyage', 'kyoto'], IN: ['ấn độ', 'india', 'diwali', 'holi'],
  FR: ['pháp', 'france', 'la bise'], TH: ['thái lan', 'thailand', 'loy krathong'], KR: ['hàn quốc', 'korea', 'hanbok'],
  CN: ['trung quốc', 'china'], MX: ['mexico', 'muertos'], EG: ['ai cập', 'egypt'], KE: ['kenya', 'maasai'],
};

@Component({
  selector: 'ca-ai-guide-page',
  imports: [ConfidenceBadge],
  templateUrl: './ai-guide.page.html',
  styleUrl: './ai-guide.page.css',
})
export class AiGuidePage {
  svc = inject(CultureService);
  session = input<string | undefined>('0'); // ?session=1 để mở sẵn một phiên mẫu
  active = signal<number | null>(null);
  current = computed(() => this.active() ?? ((Number(this.session() ?? 0) || 0) % this.svc.sessions.length));
  extra = signal<ChatMessage[]>([]);
  messages = computed(() => [...this.svc.sessions[this.current()].messages, ...this.extra()]);
  draft = signal('');
  activeCite = signal<string | null>('c1');
  level = signal<'simple' | 'normal' | 'deep'>('normal');
  quick = [
    { flag: '🇲🇽', q: 'Día de Muertos ở Mexico diễn ra thế nào?' },
    { flag: '🇰🇷', q: 'Mặc hanbok khi thăm cung điện ở Hàn Quốc có ý nghĩa gì?' },
    { flag: '🇪🇬', q: 'Khi đến Ai Cập nên lưu ý gì về trang phục?' },
  ];

  /** Quốc gia được nhắc tới trong lượt hỏi–đáp gần nhất → quyết định ảnh nền. */
  countries = computed(() => {
    const msgs = this.messages();
    const lastUser = msgs.map((m) => m.role).lastIndexOf('user');
    const text = msgs.slice(Math.max(0, lastUser)).map((m) => m.text).join(' ').toLowerCase();
    return Object.entries(KEYWORDS)
      .map(([iso, kws]) => ({ iso, pos: Math.min(...kws.map((k) => { const i = text.indexOf(k); return i < 0 ? Infinity : i; })) }))
      .filter((x) => x.pos < Infinity).sort((a, b) => a.pos - b.pos).slice(0, 2).map((x) => x.iso);
  });
  lastAnswer = computed(() => [...this.messages()].reverse().find((m) => m.role === 'assistant'));

  pick(i: number) { this.active.set(i); this.extra.set([]); this.activeCite.set('c1'); }

  paragraphs(text: string): Seg[][] {
    return text.split('\n\n').map((p) =>
      p.split(/(\*\*[^*]+\*\*|\[c\d+\])/g).filter(Boolean).map((t): Seg =>
        t.startsWith('**') ? { kind: 'bold', value: t.slice(2, -2) }
        : /^\[c\d+\]$/.test(t) ? { kind: 'cite', value: t.slice(1, -1) }
        : { kind: 'text', value: t }));
  }

  ask(q?: string) {
    const text = (q ?? this.draft()).trim();
    if (!text) return;
    this.extra.update((m) => [...m, { role: 'user', text }, {
      role: 'assistant', confidence: 'insufficient',
      text: 'Kho dữ liệu hiện **chưa có đủ nguồn** đã duyệt để trả lời câu hỏi này. Bạn có thể tham khảo trang du lịch chính thức của quốc gia hoặc tài liệu của bảo tàng quốc gia. Câu hỏi đã được gửi tới hàng đợi biên tập.',
      followUps: ['Gợi ý nguồn chính thức nên đọc?'],
    }]);
    this.draft.set('');
  }
}
