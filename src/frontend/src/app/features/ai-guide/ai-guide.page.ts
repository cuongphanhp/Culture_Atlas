/**
 * Trang AI Guide: chat streaming có trích dẫn, gợi ý câu hỏi theo quốc gia + mối quan tâm, giọng nói, ảnh nền theo quốc gia.
 */
import { Component, ElementRef, OnDestroy, computed, effect, inject, input, signal, viewChild } from '@angular/core';
import { CategoryCode, ChatAnswer, ChatLevel, ChatMessage, Citation, SuggestedQuestion } from '../../core/models/culture.models';
import { ApiError, ChatApi } from '../../core/services/chat-api.service';
import { CultureService } from '../../core/services/culture.service';
import { ConfidenceBadge } from '../../shared/components/badges';

type Seg = { kind: 'text' | 'bold' | 'cite'; value: string };

// Từ khoá nhận diện quốc gia (dùng cho hội thoại mẫu; hội thoại thật lấy `countries` từ API).
const KEYWORDS: Record<string, string[]> = {
  VN: ['việt nam', 'vietnam', 'lì xì', 'tết', 'hội an'], JP: ['nhật', 'japan', 'omiyage', 'kyoto'], IN: ['ấn độ', 'india', 'diwali', 'holi'],
  FR: ['pháp', 'france', 'la bise'], TH: ['thái lan', 'thailand', 'loy krathong'], KR: ['hàn quốc', 'korea', 'hanbok'],
  CN: ['trung quốc', 'china'], MX: ['mexico', 'muertos'], EG: ['ai cập', 'egypt'], KE: ['kenya', 'maasai'],
};

const WELCOME: ChatMessage = {
  role: 'assistant', confidence: 'none',
  text: 'Xin chào! Mình là **CultureAtlas Guide**. Bạn có thể hỏi mình về phong tục, phép lịch sự, tặng quà, lễ hội, ẩm thực hay di sản UNESCO của 10 quốc gia — mọi thông tin văn hoá mình đưa ra đều kèm nguồn để bạn kiểm tra.',
  followUps: ['Lần đầu đến Nhật Bản cần biết những phép lịch sự nào?', 'Tết ở Việt Nam có những phong tục gì?', 'Thủ đô của Kenya là gì?'],
};

const KIND_LABEL: Record<string, string> = { claim: 'Đã biên tập', reference: 'Tài liệu tham khảo', heritage: 'Dữ liệu UNESCO' };

/** Trang /guide (?country=JP&category=food_dining&session=0). */
@Component({
  selector: 'ca-ai-guide-page',
  imports: [ConfidenceBadge],
  templateUrl: './ai-guide.page.html',
  styleUrl: './ai-guide.page.css',
})
export class AiGuidePage implements OnDestroy {
  svc = inject(CultureService);
  private api = inject(ChatApi);
  private msgsEl = viewChild<ElementRef<HTMLElement>>('msgs');

  /** ?session=1 mở sẵn một hội thoại mẫu; ?country=JP đặt ngữ cảnh quốc gia; ?category=food_dining là mục người dùng đang xem. */
  session = input<string | undefined>(undefined);
  country = input<string | undefined>(undefined);
  category = input<CategoryCode | undefined>(undefined);

  /** -1 = hội thoại thật; ≥ 0 = đang xem hội thoại mẫu. */
  active = signal<number>(-1);
  live = signal<ChatMessage[]>([WELCOME]);
  sessionId = signal<string | null>(null);
  contextCountry = signal<string | null>(null);
  apiCountries = signal<string[]>([]);
  remaining = signal<number | null>(null);
  busy = signal(false);
  draft = signal('');
  activeCite = signal<string | null>('c1');
  level = signal<ChatLevel>('normal');
  speaking = signal<number | null>(null);
  recording = signal(false);
  notice = signal<string | null>(null);
  kindLabel = KIND_LABEL;
  /** Gợi ý từ API theo quốc gia + chủ đề quan tâm (AC10.3, AC10.4); rỗng → dùng gợi ý dự phòng `quick`. */
  suggested = signal<SuggestedQuestion[]>([]);
  /** Dự phòng khi API gợi ý không phản hồi. */
  quick: SuggestedQuestion[] = [
    { text: 'Día de Muertos ở Mexico diễn ra thế nào?', category: 'festivals', country: 'MX' },
    { text: 'Hanbok được mặc vào những dịp nào?', category: 'clothing', country: 'KR' },
    { text: 'Khi đến Ai Cập nên lưu ý gì về trang phục?', category: 'clothing', country: 'EG' },
  ];

  private audio: HTMLAudioElement | null = null;
  private recorder: MediaRecorder | null = null;

  constructor() {
    effect(() => {
      const s = this.session();
      if (s !== undefined && s !== null && s !== '') this.active.set((Number(s) || 0) % this.svc.sessions.length);
    });
    effect(() => {
      const c = this.country()?.toUpperCase();
      if (c && this.svc.country(c)) this.contextCountry.set(c);
    });
    effect(() => {                       // tải lại gợi ý khi đổi quốc gia / chủ đề / sau mỗi câu trả lời
      if (this.isDemo()) return;
      void this.loadSuggestions(this.focusCountry(), this.sessionId(), this.category() ?? null, this.answered());
    });
    effect(() => {                       // tự cuộn xuống khi có tin nhắn / token mới
      this.messages();
      queueMicrotask(() => {
        const el = this.msgsEl()?.nativeElement;
        if (el) el.scrollTop = el.scrollHeight;
      });
    });
  }

  /** Tin nhắn đang hiển thị. Lời chào của hội thoại thật lấy gợi ý theo quốc gia / chủ đề đang xem. */
  messages = computed(() => {
    if (this.active() >= 0) return this.svc.sessions[this.active()].messages;
    const list = this.live();
    const sug = this.suggested();
    return list[0] === WELCOME && sug.length ? [{ ...WELCOME, followUps: sug.slice(0, 3).map((s) => s.text) }, ...list.slice(1)] : list;
  });
  isDemo = computed(() => this.active() >= 0);

  /** Quốc gia đang được nói tới → ảnh nền. Hội thoại thật: theo API; hội thoại mẫu: theo từ khoá. */
  countries = computed(() => {
    if (!this.isDemo()) {
      const fromApi = this.apiCountries().slice(0, 2);
      return fromApi.length ? fromApi : this.contextCountry() ? [this.contextCountry()!] : [];
    }
    const msgs = this.messages();
    const lastUser = msgs.map((m) => m.role).lastIndexOf('user');
    const text = msgs.slice(Math.max(0, lastUser)).map((m) => m.text).join(' ').toLowerCase();
    return Object.entries(KEYWORDS)
      .map(([iso, kws]) => ({ iso, pos: Math.min(...kws.map((k) => { const i = text.indexOf(k); return i < 0 ? Infinity : i; })) }))
      .filter((x) => x.pos < Infinity).sort((a, b) => a.pos - b.pos).slice(0, 2).map((x) => x.iso);
  });
  /** Quốc gia mà gợi ý hướng tới: nước đang nói tới, không có thì nước của ngữ cảnh trang. */
  focusCountry = computed(() => (this.isDemo() ? null : this.countries()[0] ?? null));
  /** Số câu trả lời đã nhận — tăng sau mỗi lượt để làm mới gợi ý theo mối quan tâm mới. */
  answered = computed(() => this.live().filter((m) => m.role === 'assistant' && m.messageId).length);
  /** Danh sách "Thử hỏi" ở cột trái. */
  starters = computed(() => (this.suggested().length ? this.suggested() : this.quick));
  lastAnswer = computed(() => [...this.messages()].reverse().find((m) => m.role === 'assistant' && !m.streaming));

  private suggestKey = '';

  /** Gọi GET /api/ai/suggestions; bỏ qua nếu tham số không đổi, giữ gợi ý cũ nếu API lỗi. */
  private async loadSuggestions(country: string | null, sessionId: string | null, category: CategoryCode | null, turn: number) {
    const key = [country, sessionId, category, turn].join('|');
    if (key === this.suggestKey) return;
    this.suggestKey = key;
    try {
      const r = await this.api.suggestions({ country, sessionId, category, limit: 4 });
      if (key === this.suggestKey) this.suggested.set(r.questions);
    } catch { /* dùng gợi ý hiện có */ }
  }

  /** Cờ của quốc gia trong câu gợi ý (🌏 nếu là câu chung). */
  flag(s: SuggestedQuestion) { return (s.country && this.svc.country(s.country)?.flag) || '🌏'; }

  /** Mở hội thoại mẫu thứ i. */
  pick(i: number) { this.active.set(i); this.activeCite.set('c1'); }

  /** Bắt đầu hội thoại mới (xoá phiên). */
  newChat() {
    this.active.set(-1);
    this.live.set([WELCOME]);
    this.sessionId.set(null);
    this.apiCountries.set([]);
    this.notice.set(null);
  }

  /** Bỏ ngữ cảnh quốc gia của trang. */
  clearContext() { this.contextCountry.set(null); }

  /** Tách câu trả lời thành đoạn và mẩu (chữ thường / **đậm** / nhãn trích dẫn [c#]). */
  paragraphs(text: string): Seg[][] {
    return text.split(/\n{2,}/).map((p) =>
      p.split(/(\*\*[^*]+\*\*|\[c\d+\])/g).filter(Boolean).map((t): Seg =>
        t.startsWith('**') ? { kind: 'bold', value: t.slice(2, -2) }
        : /^\[c\d+\]$/.test(t) ? { kind: 'cite', value: t.slice(1, -1) }
        : { kind: 'text', value: t }));
  }

  /** Thay tin nhắn cuối (bong bóng AI đang stream) bằng bản cập nhật. */
  private patchLast(fn: (m: ChatMessage) => ChatMessage) {
    this.live.update((list) => [...list.slice(0, -1), fn(list[list.length - 1])]);
  }

  /** Gửi câu hỏi (ô nhập hoặc câu gợi ý), stream câu trả lời vào bong bóng cuối; lỗi API → thông báo thân thiện. */
  async ask(q?: string) {
    const text = (q ?? this.draft()).trim();
    if (!text || this.busy()) return;
    if (this.isDemo()) this.newChat();
    this.draft.set('');
    this.busy.set(true);
    this.live.update((m) => [...m, { role: 'user', text }, { role: 'assistant', text: '', streaming: true }]);
    try {
      const { answer, remaining } = await this.api.ask(
        { message: text, sessionId: this.sessionId(), level: this.level(),
          context: this.contextCountry() ? { country: this.contextCountry()!, category: this.category() } : undefined },
        (t) => this.patchLast((m) => ({ ...m, text: m.text + t })));
      this.applyAnswer(answer);
      if (remaining !== null) this.remaining.set(remaining);
    } catch (e) {
      const err = e as ApiError;
      const msg = err.status === 429 ? (err.detail ?? 'Bạn đã dùng hết lượt hỏi hôm nay.')
        : err.status === 503 ? 'AI Guide đang tạm gián đoạn. Bạn thử lại sau ít phút nhé.'
        : `Không gửi được câu hỏi (${err.title ?? 'lỗi kết nối'}). Bạn thử lại nhé.`;
      if (err.status === 429) this.remaining.set(0);
      this.patchLast(() => ({ role: 'assistant', text: msg, error: true, confidence: 'none' }));
    } finally {
      this.busy.set(false);
    }
  }

  private applyAnswer(a: ChatAnswer) {
    this.sessionId.set(a.sessionId);
    if (a.countries?.length) this.apiCountries.set(a.countries);
    this.patchLast(() => ({
      role: 'assistant', text: a.answer, citations: a.citations, confidence: a.confidence,
      followUps: a.followUpQuestions, unsupportedPoints: a.unsupportedPoints, messageId: a.messageId,
    }));
    this.activeCite.set(a.citations[0]?.id ?? null);
  }

  /** Đánh giá 👍/👎 một câu trả lời (một lần). */
  async rate(m: ChatMessage, rating: 1 | -1) {
    if (!m.messageId || m.rated) return;
    this.live.update((list) => list.map((x) => (x === m ? { ...x, rated: rating } : x)));
    try { await this.api.rate(m.messageId, rating); } catch { /* đã ghi nhận trên giao diện */ }
  }

  /** Sao chép câu trả lời (bỏ nhãn trích dẫn). */
  copy(m: ChatMessage) {
    navigator.clipboard?.writeText(m.text.replace(/\s*\[c\d+\]/g, '')).catch(() => undefined);
  }

  /** Đọc câu trả lời bằng giọng nói (TTS chạy local trên máy chủ). Bấm lại để dừng. */
  async speak(m: ChatMessage, index: number) {
    if (this.speaking() === index) { this.stopAudio(); return; }
    this.stopAudio();
    this.speaking.set(index);
    try {
      const blob = await this.api.speak(m.text);
      this.audio = new Audio(URL.createObjectURL(blob));
      this.audio.onended = () => this.speaking.set(null);
      await this.audio.play();
    } catch {
      this.notice.set('Chưa đọc được câu trả lời — tính năng giọng nói đang tạm gián đoạn.');
      this.speaking.set(null);
    }
  }

  private stopAudio() {
    this.audio?.pause();
    this.audio = null;
    this.speaking.set(null);
  }

  /** Ghi âm câu hỏi → nhận dạng trên máy chủ → điền vào ô nhập để người dùng sửa trước khi gửi (AC21.6). */
  async toggleMic() {
    if (this.recording()) { this.recorder?.stop(); return; }
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      this.notice.set('Trình duyệt chỉ cho dùng micro trên HTTPS hoặc localhost.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = [];
      this.recorder = new MediaRecorder(stream);
      this.recorder.ondataavailable = (e) => chunks.push(e.data);
      this.recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        this.recording.set(false);
        try {
          const text = await this.api.transcribe(new Blob(chunks, { type: this.recorder?.mimeType || 'audio/webm' }));
          this.draft.set(text);
          if (!text) this.notice.set('Mình chưa nghe rõ, bạn thử nói lại nhé.');
        } catch {
          this.notice.set('Chưa nhận dạng được giọng nói — tính năng đang tạm gián đoạn.');
        }
      };
      this.recorder.start();
      this.recording.set(true);
      this.notice.set(null);
    } catch {
      this.notice.set('Không truy cập được micro. Hãy cho phép trình duyệt dùng micro.');
    }
  }

  /** Nhãn loại nguồn của thẻ trích dẫn. */
  citationKind(c: Citation) { return c.kind ? this.kindLabel[c.kind] : this.svc.source(c.sourceId)?.reliabilityTier; }

  ngOnDestroy() { this.stopAudio(); this.recorder?.stop(); }
}
