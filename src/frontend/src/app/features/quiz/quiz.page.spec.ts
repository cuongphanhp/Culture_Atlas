import { $, $$, render, text } from '../../../testing/render';
import { QuizPage } from './quiz.page';

describe('Culture quiz (US12, US13)', () => {
  async function fresh() {
    const f = await render(QuizPage);
    f.componentInstance.picked.set(null);
    f.detectChanges();
    return f;
  }

  it('[AC13.1] chọn sai: đáp án đúng tô xanh, đáp án đã chọn tô đỏ, có giải thích + nguồn + link bài gốc', async () => {
    const f = await fresh();
    const q = f.componentInstance.q();
    const wrong = q.answerIndex === 0 ? 1 : 0;
    $$(f, '.opt')[wrong].click();
    f.detectChanges();
    const opts = $$(f, '.opt');
    expect(opts[q.answerIndex].classList).toContain('right');
    expect(opts[wrong].classList).toContain('wrong');
    expect(text(f)).toContain(q.explanation);
    expect($$(f, '.explain .cite').length).toBeGreaterThan(0);
    expect($(f, '.explain a[href]:not(.cite)')!.getAttribute('href')).toMatch(/\/countries\//);
  });

  it('[AC13.1] chọn đúng: không có đáp án nào tô đỏ, các nút bị khoá', async () => {
    const f = await fresh();
    const q = f.componentInstance.q();
    $$(f, '.opt')[q.answerIndex].click();
    f.detectChanges();
    expect($$(f, '.opt.wrong').length).toBe(0);
    expect($$(f, '.opt').every((b) => (b as HTMLButtonElement).disabled)).toBe(true);
  });

  it('[AC12.1] mỗi câu hỏi có 2–4 lựa chọn', async () => {
    const f = await fresh();
    expect($$(f, '.opt').length).toBeGreaterThanOrEqual(2);
    expect($$(f, '.opt').length).toBeLessThanOrEqual(4);
  });

  it.skip('[AC13.2] PENDING: tổng kết phiên liệt kê chủ đề có câu sai (tính từ phiên thật)', async () => {
    const f = await fresh();
    const q = f.componentInstance.q();
    $$(f, '.opt')[q.answerIndex === 0 ? 1 : 0].click();
    f.detectChanges();
    expect($(f, '[data-testid="review-topics"]')!.textContent).toContain('Tặng quà');
  });
});
