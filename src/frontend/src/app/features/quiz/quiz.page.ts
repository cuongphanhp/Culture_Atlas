import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CultureService } from '../../core/services/culture.service';
import { CiteChips } from '../../shared/components/badges';

@Component({
  selector: 'ca-quiz-page',
  imports: [RouterLink, CiteChips],
  templateUrl: './quiz.page.html',
  styleUrl: './quiz.page.css',
})
export class QuizPage {
  svc = inject(CultureService);
  index = signal(0);
  picked = signal<number | null>(1); // trạng thái mẫu: đã chọn đáp án đúng
  q = computed(() => this.svc.quiz[this.index()]);
  correct = computed(() => this.picked() === this.q().answerIndex);
  letters = ['A', 'B', 'C', 'D'];

  next() { this.index.update((i) => (i + 1) % this.svc.quiz.length); this.picked.set(null); }
}
