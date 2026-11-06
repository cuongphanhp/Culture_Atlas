/** Client HTTP của AI API (chat SSE, gợi ý câu hỏi, đánh giá, giọng nói). */
import { Injectable } from '@angular/core';
import { CategoryCode, ChatAnswer, ChatLevel, Suggestions } from '../models/culture.models';

/** Body của POST /api/ai/chat. */
export interface ChatRequest {
  message: string;
  sessionId?: string | null;
  level?: ChatLevel;
  lang?: 'vi' | 'en';
  context?: { country?: string; category?: CategoryCode };
}

/** Lỗi theo RFC 7807 trả về từ API (429 hết lượt, 503 AI gián đoạn…). */
export class ApiError extends Error {
  constructor(public status: number, public title: string, public detail?: string) {
    super(detail || title);
  }
}

const CLIENT_KEY = 'ca.clientId';

/**
 * Gọi AI API của backend (docs/api/openapi.yaml):
 * - POST /api/ai/chat — stream SSE: sự kiện `token` (từng mẩu văn bản) rồi `final` (ChatAnswer)
 * - POST /api/ai/chat/messages/{id}/rating
 * - GET /api/ai/suggestions — câu hỏi gợi ý theo quốc gia + chủ đề quan tâm
 * - POST /api/ai/speech, POST /api/ai/transcribe — giọng nói (AI local)
 */
@Injectable({ providedIn: 'root' })
export class ChatApi {
  private base = '/api/ai';

  /** Mã khách ẩn danh lưu trên trình duyệt — backend dùng để giới hạn lượt và giữ lịch sử hội thoại. */
  clientId(): string {
    try {
      let id = localStorage.getItem(CLIENT_KEY);
      if (!id) {
        id = crypto.randomUUID().replaceAll('-', '');
        localStorage.setItem(CLIENT_KEY, id);
      }
      return id;
    } catch {
      return 'anon' + Math.random().toString(36).slice(2, 12);
    }
  }

  private headers(extra: Record<string, string> = {}): Record<string, string> {
    return { 'X-Client-Id': this.clientId(), ...extra };
  }

  private async problem(r: Response): Promise<ApiError> {
    try {
      const p = await r.json();
      return new ApiError(r.status, p.title ?? r.statusText, p.detail);
    } catch {
      return new ApiError(r.status, r.statusText || 'Lỗi kết nối');
    }
  }

  /** Hỏi AI, gọi onToken cho từng mẩu chữ khi đang stream. Trả về câu trả lời đầy đủ + số lượt còn lại. */
  async ask(req: ChatRequest, onToken: (text: string) => void): Promise<{ answer: ChatAnswer; remaining: number | null }> {
    const r = await fetch(`${this.base}/chat`, {
      method: 'POST',
      headers: this.headers({ 'Content-Type': 'application/json', Accept: 'text/event-stream' }),
      body: JSON.stringify(req),
    });
    if (!r.ok || !r.body) throw await this.problem(r);
    const remainingHeader = r.headers.get('X-RateLimit-Remaining');
    const remaining = remainingHeader === null ? null : Number(remainingHeader);

    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    let answer: ChatAnswer | null = null;
    for (;;) {
      const { done, value } = await reader.read();
      buf += decoder.decode(value ?? new Uint8Array(), { stream: !done });
      let sep: number;
      while ((sep = buf.indexOf('\n\n')) !== -1) {
        const block = buf.slice(0, sep);
        buf = buf.slice(sep + 2);
        const event = /^event: (.+)$/m.exec(block)?.[1] ?? 'message';
        const data = block.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trim()).join('\n');
        if (!data) continue;
        const payload = JSON.parse(data);
        if (event === 'token') onToken(payload.text);
        else if (event === 'final') answer = payload as ChatAnswer;
        else if (event === 'error') throw new ApiError(payload.status ?? 503, payload.title ?? 'AI Guide bị gián đoạn');
      }
      if (done) break;
    }
    if (!answer) throw new ApiError(503, 'Kết nối bị ngắt trước khi có câu trả lời');
    return { answer, remaining };
  }

  /** Câu hỏi gợi ý theo quốc gia và chủ đề người dùng quan tâm (suy ra từ phiên `sessionId` và mục đang xem). */
  async suggestions(q: { country?: string | null; sessionId?: string | null; category?: CategoryCode | null; limit?: number }): Promise<Suggestions> {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(q)) if (v !== null && v !== undefined && v !== '') params.set(k, String(v));
    const r = await fetch(`${this.base}/suggestions?${params}`, { headers: this.headers() });
    if (!r.ok) throw await this.problem(r);
    return r.json();
  }

  /** Đánh giá 👍/👎 một câu trả lời (409 = đã đánh giá → bỏ qua). */
  async rate(messageId: number, rating: 1 | -1): Promise<void> {
    const r = await fetch(`${this.base}/chat/messages/${messageId}/rating`, {
      method: 'POST', headers: this.headers({ 'Content-Type': 'application/json' }), body: JSON.stringify({ rating }),
    });
    if (!r.ok && r.status !== 409) throw await this.problem(r);
  }

  /** Đọc văn bản bằng TTS local → file WAV. */
  async speak(text: string, voice?: string): Promise<Blob> {
    const r = await fetch(`${this.base}/speech`, {
      method: 'POST', headers: this.headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ text: text.slice(0, 1500), voice }),
    });
    if (!r.ok) throw await this.problem(r);
    return r.blob();
  }

  /** Nhận dạng giọng nói (STT local) → văn bản để người dùng sửa trước khi gửi. */
  async transcribe(audio: Blob): Promise<string> {
    const form = new FormData();
    form.append('file', audio, 'question.webm');
    const r = await fetch(`${this.base}/transcribe`, { method: 'POST', headers: this.headers(), body: form });
    if (!r.ok) throw await this.problem(r);
    return (await r.json()).text as string;
  }
}
