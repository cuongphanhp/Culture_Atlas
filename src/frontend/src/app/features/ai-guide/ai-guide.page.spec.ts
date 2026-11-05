import { $, $$, render, text } from '../../../testing/render';
import { AiGuidePage } from './ai-guide.page';

describe('AI Cultural Guide UI (US06–US10)', () => {
  it('[AC07.3] bấm chip trích dẫn làm nổi bật thẻ nguồn tương ứng', async () => {
    const f = await render(AiGuidePage);
    const chips = $$(f, '.cite[class]').filter((b) => b.tagName === 'BUTTON');
    expect(chips.length).toBeGreaterThan(1);
    chips[1].click();
    f.detectChanges();
    const on = $(f, '.src.on .src-top .cite')!;
    expect(on.textContent).toBe(chips[1].textContent);
  });

  it('[AC10.1] bấm câu hỏi gợi ý gửi ngay câu hỏi đó', async () => {
    const f = await render(AiGuidePage);
    const follow = $(f, '.follow .chip')!;
    const q = follow.textContent!.trim();
    follow.click();
    f.detectChanges();
    const msgs = f.componentInstance.messages();
    expect(msgs.some((m) => m.role === 'user' && m.text === q)).toBe(true);
  });

  it('[AC08.1] câu trả lời thiếu nguồn hiện nhãn "Chưa đủ nguồn"', async () => {
    const f = await render(AiGuidePage);
    f.componentInstance.ask('Phong tục cưới hỏi của người Maasai?');
    f.detectChanges();
    expect(text(f)).toContain('Chưa đủ nguồn');
  });

  it.skip('[AC10.2] PENDING: nút 👍/👎 bị khoá sau khi đã đánh giá', async () => {
    const f = await render(AiGuidePage);
    ($(f, '[data-testid="rate-up"]') as HTMLButtonElement).click();
    f.detectChanges();
    expect(($(f, '[data-testid="rate-down"]') as HTMLButtonElement).disabled).toBe(true);
  });

  it.skip('[AC09.1] PENDING: chip ngữ cảnh hiển thị quốc gia đang xem', async () => {
    const f = await render(AiGuidePage);
    expect($(f, '[data-testid="context-chip"]')!.textContent).toContain('Nhật Bản');
  });
});

describe('AI Guide — giọng nói (US21)', () => {
  it.skip('[AC21.6] PENDING: nút micro ghi âm, văn bản nhận dạng hiện vào ô nhập để sửa trước khi gửi', async () => {
    const f = await render(AiGuidePage);
    expect($(f, '[data-testid="mic"]')).toBeTruthy();
  });

  it.skip('[AC21.6] PENDING: nút loa trên mỗi câu trả lời để nghe lại', async () => {
    const f = await render(AiGuidePage);
    expect($$(f, '[data-testid="speak"]').length).toBeGreaterThan(0);
  });
});
