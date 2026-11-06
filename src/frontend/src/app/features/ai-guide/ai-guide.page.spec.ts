import { ChatAnswer, SuggestedQuestion, Suggestions } from '../../core/models/culture.models';
import { ApiError, ChatApi, ChatRequest } from '../../core/services/chat-api.service';
import { $, $$, render, text } from '../../../testing/render';
import { AiGuidePage } from './ai-guide.page';

/** ChatApi giả: không gọi mạng, stream câu trả lời theo từng mẩu như SSE thật. */
class FakeChatApi {
  requests: ChatRequest[] = [];
  rated: [number, number][] = [];
  spoken: string[] = [];
  next: Partial<ChatAnswer> | ApiError = {};

  async ask(req: ChatRequest, onToken: (t: string) => void) {
    this.requests.push(req);
    if (this.next instanceof ApiError) throw this.next;
    const answer: ChatAnswer = {
      messageId: 7, sessionId: 'sess-1', confidence: 'supported', route: 'rag', unsupportedPoints: [], countries: ['JP'],
      answer: 'Ở Nhật Bản, quà thường được trao bằng hai tay [c1].',
      citations: [{ id: 'c1', sourceId: 1, chunkId: 3, kind: 'claim', verified: true, title: 'Tặng quà ở Nhật Bản',
                    publisher: 'JNTO', url: 'https://www.japan.travel', license: 'Excerpts only', excerpt: 'Gifts are presented with both hands.' }],
      followUpQuestions: ['Nên tránh món quà nào?', 'Gói quà thế nào?'],
      ...this.next,
    };
    for (const part of answer.answer.match(/\S+\s*/g) ?? []) onToken(part);
    return { answer, remaining: 9 };
  }
  suggestCalls: Record<string, unknown>[] = [];
  suggestFail = false;
  /** Gợi ý giả: câu theo quốc gia được yêu cầu, câu đầu theo chủ đề đang xem (nếu có). */
  async suggestions(q: Record<string, unknown>): Promise<Suggestions> {
    this.suggestCalls.push(q);
    if (this.suggestFail) throw new ApiError(503, 'down');
    const iso = (q['country'] as string | null) ?? null;
    const cat = (q['category'] as SuggestedQuestion['category']) ?? 'etiquette';
    const tag = iso ?? 'chung';
    return { country: iso, interests: q['category'] ? [cat!] : [], questions: [
      { text: `Gợi ý 1 về ${tag}`, category: cat, country: iso },
      { text: `Gợi ý 2 về ${tag}`, category: 'festivals', country: iso },
      { text: `Gợi ý 3 về ${tag}`, category: 'food_dining', country: iso },
      { text: `Gợi ý 4 về ${tag}`, category: 'heritage', country: iso },
    ] };
  }
  async rate(id: number, r: number) { this.rated.push([id, r]); }
  async speak(t: string) { this.spoken.push(t); return new Blob(['RIFF'], { type: 'audio/wav' }); }
  async transcribe() { return 'Ở nhật bản tặng quà cần lưu ý gì'; }
}

async function setup(inputs: Record<string, unknown> = {}) {
  const api = new FakeChatApi();
  const f = await render(AiGuidePage, inputs, [{ provide: ChatApi, useValue: api }]);
  return { f, api };
}

async function send(f: Awaited<ReturnType<typeof setup>>['f'], q: string) {
  await f.componentInstance.ask(q);
  f.detectChanges();
}

describe('AI Cultural Guide UI (US06–US10)', () => {
  it('[AC06.1] gửi câu hỏi → câu trả lời stream vào khung chat kèm trích dẫn, gửi đúng mức giải thích', async () => {
    const { f, api } = await setup();
    f.componentInstance.level.set('deep');
    await send(f, 'Tặng quà ở Nhật cần lưu ý gì?');
    expect(api.requests[0]).toMatchObject({ message: 'Tặng quà ở Nhật cần lưu ý gì?', level: 'deep', sessionId: null });
    expect(text(f)).toContain('trao bằng hai tay');
    expect($$(f, '.bubble.ai .cite').length).toBe(1);
    expect($(f, '[data-testid="limit"]')!.textContent).toContain('còn 9');
  });

  it('[AC06.5] câu hỏi tiếp theo gửi kèm sessionId của lượt trước', async () => {
    const { f, api } = await setup();
    await send(f, 'Tặng quà ở Nhật cần lưu ý gì?');
    await send(f, 'Còn hoa thì sao?');
    expect(api.requests[1].sessionId).toBe('sess-1');
  });

  it('[AC06.4] lời chào mở đầu không hiện nhãn độ tin cậy', async () => {
    const { f } = await setup();
    expect(text(f)).toContain('CultureAtlas Guide');
    expect($$(f, '.bubble.ai .conf').length).toBe(0);
  });

  it('[AC06.3] hết lượt → hiện thông báo thân thiện từ API', async () => {
    const { f, api } = await setup();
    api.next = new ApiError(429, 'Bạn đã dùng hết lượt hỏi hôm nay', 'Khách được hỏi AI 10 lượt mỗi ngày.');
    await send(f, 'Tặng quà ở Nhật?');
    expect(text(f)).toContain('10 lượt mỗi ngày');
    expect($(f, '[data-testid="limit"]')!.textContent).toContain('còn 0');
  });

  it('[AC07.3] bấm chip trích dẫn làm nổi bật thẻ nguồn tương ứng (hội thoại mẫu)', async () => {
    const { f } = await setup();
    f.componentInstance.pick(0);
    f.detectChanges();
    const chips = $$(f, '.cite[class]').filter((b) => b.tagName === 'BUTTON');
    expect(chips.length).toBeGreaterThan(1);
    chips[1].click();
    f.detectChanges();
    const on = $(f, '.src.on .src-top .cite')!;
    expect(on.textContent).toBe(chips[1].textContent);
  });

  it('[AC07.4] thẻ nguồn hiện loại nguồn, giấy phép và liên kết', async () => {
    const { f, api } = await setup();
    api.next = { citations: [{ id: 'c1', sourceId: 6, kind: 'reference', verified: false, title: 'Etiquette in Japan',
                               publisher: 'Wikimedia Foundation', license: 'CC BY-SA 4.0', url: 'https://en.wikipedia.org/wiki/x', excerpt: 'temiyage' }],
                 confidence: 'inferred' };
    await send(f, 'temiyage là gì?');
    const src = $(f, '.src')!;
    expect(src.textContent).toContain('Tài liệu tham khảo');
    expect(src.textContent).toContain('CC BY-SA 4.0');
    expect(src.querySelector('a')!.getAttribute('href')).toBe('https://en.wikipedia.org/wiki/x');
  });

  it('[AC10.1] bấm câu hỏi gợi ý gửi ngay câu hỏi đó', async () => {
    const { f, api } = await setup();
    const follow = $(f, '.follow .chip')!;
    const q = follow.textContent!.trim();
    follow.click();
    await new Promise((r) => setTimeout(r));
    f.detectChanges();
    expect(api.requests[0].message).toBe(q);
    expect(f.componentInstance.messages().some((m) => m.role === 'user' && m.text === q)).toBe(true);
  });

  it('[AC08.1] câu trả lời thiếu nguồn hiện nhãn "Chưa đủ nguồn"', async () => {
    const { f, api } = await setup();
    api.next = { confidence: 'insufficient', route: 'refused', citations: [],
                 answer: 'Kho dữ liệu của mình hiện **chưa có đủ nguồn** để trả lời.' };
    await send(f, 'Phong tục cưới hỏi của người Maasai?');
    expect(text(f)).toContain('Chưa đủ nguồn');
  });

  it('[AC10.2] nút 👍/👎 bị khoá sau khi đã đánh giá và gửi đánh giá lên API', async () => {
    const { f, api } = await setup();
    await send(f, 'Tặng quà ở Nhật?');
    ($$(f, '[data-testid="rate-up"]').at(-1) as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r));
    f.detectChanges();
    expect(api.rated).toEqual([[7, 1]]);
    expect(($$(f, '[data-testid="rate-down"]').at(-1) as HTMLButtonElement).disabled).toBe(true);
  });

  it('[AC09.1] chip ngữ cảnh hiển thị quốc gia đang xem và được gửi kèm câu hỏi', async () => {
    const { f, api } = await setup({ country: 'JP' });
    expect($(f, '[data-testid="context-chip"]')!.textContent).toContain('Nhật Bản');
    await send(f, 'Có nên tặng hoa cúc không?');
    expect(api.requests[0].context).toEqual({ country: 'JP' });
  });
});

describe('AI Guide — giọng nói (US21)', () => {
  it('[AC21.6] nút micro ghi âm, văn bản nhận dạng hiện vào ô nhập để sửa trước khi gửi', async () => {
    const { f } = await setup();
    class FakeRecorder {
      mimeType = 'audio/webm';
      ondataavailable: ((e: { data: Blob }) => void) | null = null;
      onstop: (() => void) | null = null;
      start() {}
      stop() { this.ondataavailable?.({ data: new Blob(['x']) }); this.onstop?.(); }
    }
    vi.stubGlobal('MediaRecorder', FakeRecorder);
    Object.defineProperty(window, 'isSecureContext', { value: true, configurable: true });
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: async () => ({ getTracks: () => [{ stop() {} }] }) }, configurable: true });

    await f.componentInstance.toggleMic();            // bắt đầu ghi
    expect(f.componentInstance.recording()).toBe(true);
    await f.componentInstance.toggleMic();            // dừng → nhận dạng
    await new Promise((r) => setTimeout(r));
    f.detectChanges();
    expect(f.componentInstance.draft()).toBe('Ở nhật bản tặng quà cần lưu ý gì');
    expect(($(f, '.composer input') as HTMLInputElement).value).toBe('Ở nhật bản tặng quà cần lưu ý gì');
    vi.unstubAllGlobals();
  });

  it('[AC21.6] nút loa trên mỗi câu trả lời để nghe lại', async () => {
    const { f, api } = await setup();
    vi.stubGlobal('Audio', class { onended = null; play = async () => undefined; pause() {} });
    vi.stubGlobal('URL', { ...URL, createObjectURL: () => 'blob:x' });
    await send(f, 'Tặng quà ở Nhật?');
    ($$(f, '[data-testid="speak"]').at(-1) as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r));
    expect(api.spoken[0]).toContain('trao bằng hai tay');
    vi.unstubAllGlobals();
  });
});

describe('AI Guide — ảnh nền theo quốc gia đang nói tới (AC01.4)', () => {
  const bgs = (f: Awaited<ReturnType<typeof setup>>['f']) =>
    $$(f, '.backdrop .bg').map((el) => el.style.backgroundImage);
  const css = (src: string) => 'url("' + src + '")';

  it('[AC01.4] câu trả lời nói về Hàn Quốc → ảnh nền đổi sang Hàn Quốc', async () => {
    const { f, api } = await setup();
    const svc = f.componentInstance.svc;
    api.next = { countries: ['KR'] };
    await send(f, 'Hanbok mặc khi nào?');
    expect(bgs(f)).toEqual([css(svc.photo('KR').src)]);
  });

  it('[AC01.4] so sánh hai nước → ảnh nền chia đôi theo đúng hai nước', async () => {
    const { f, api } = await setup();
    const svc = f.componentInstance.svc;
    api.next = { countries: ['FR', 'JP'] };
    await send(f, 'So sánh phép lịch sự khi ăn ở Pháp và Nhật');
    expect($(f, '.backdrop')!.classList).toContain('split');
    expect(bgs(f)).toEqual([css(svc.photo('FR').src), css(svc.photo('JP').src)]);
  });

  it('[AC01.4] mở AI Guide từ trang một nước (?country=EG) → ảnh nền là nước đó ngay từ đầu', async () => {
    const { f } = await setup({ country: 'EG' });
    expect(bgs(f)).toEqual([css(f.componentInstance.svc.photo('EG').src)]);
  });
  it('[AC10.3] mở AI Guide với ?country=JP → lời chào và cột “Thử hỏi” gợi ý câu về Nhật Bản', async () => {
    const { f, api } = await setup({ country: 'JP' });
    await f.whenStable();
    f.detectChanges();
    expect(api.suggestCalls.at(-1)).toMatchObject({ country: 'JP' });
    const starters = $$(f, '[data-testid="starter"]').map((b) => b.textContent!.trim());
    expect(starters).toHaveLength(4);
    expect(starters.every((t) => t.startsWith('🇯🇵') && t.includes('về JP'))).toBe(true);
    expect(text(f)).toContain('Thử hỏi về Nhật Bản');
    const chips = $$(f, '.bubble.ai .follow .chip').map((b) => b.textContent!.trim());
    expect(chips).toEqual(['Gợi ý 1 về JP', 'Gợi ý 2 về JP', 'Gợi ý 3 về JP']);
  });

  it('[AC10.4] mục đang xem (?category) được gửi kèm khi lấy gợi ý và khi hỏi', async () => {
    const { f, api } = await setup({ country: 'VN', category: 'food_dining' });
    await f.whenStable();
    expect(api.suggestCalls.at(-1)).toMatchObject({ country: 'VN', category: 'food_dining' });
    await send(f, 'Người Việt ăn gì ngày Tết?');
    expect(api.requests[0].context).toEqual({ country: 'VN', category: 'food_dining' });
  });

  it('[AC10.4] sau mỗi câu trả lời, gợi ý được làm mới theo phiên và quốc gia vừa nói tới', async () => {
    const { f, api } = await setup();
    await f.whenStable();
    expect(api.suggestCalls.at(-1)).toMatchObject({ country: null, sessionId: null });
    await send(f, 'Tặng quà ở Nhật cần lưu ý gì?');
    await f.whenStable();
    f.detectChanges();
    expect(api.suggestCalls.at(-1)).toMatchObject({ country: 'JP', sessionId: 'sess-1' });
    expect($$(f, '[data-testid="starter"]')[0].textContent).toContain('Gợi ý 1 về JP');
  });

  it('[AC10.3] API gợi ý lỗi → vẫn có câu hỏi gợi ý dự phòng', async () => {
    const api = new FakeChatApi();
    api.suggestFail = true;
    const f = await render(AiGuidePage, {}, [{ provide: ChatApi, useValue: api }]);
    await f.whenStable();
    f.detectChanges();
    expect($$(f, '[data-testid="starter"]').length).toBe(3);
    expect($$(f, '.bubble.ai .follow .chip').length).toBe(3);
  });
});
