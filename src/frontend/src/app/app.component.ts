import { Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'ca-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header class="topbar">
      <a routerLink="/" class="brand"><span class="logo">◎</span> CultureAtlas <em>AI</em></a>
      <nav>
        <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">Khám phá</a>
        <a routerLink="/guide" routerLinkActive="active">AI Guide</a>
        <a routerLink="/compare" routerLinkActive="active">So sánh</a>
        <a routerLink="/quiz" routerLinkActive="active">Quiz</a>
        <a routerLink="/admin" routerLinkActive="active" class="admin">Quản trị</a>
      </nav>
      <div class="tools">
        <div class="lang" role="group" aria-label="Ngôn ngữ">
          <button [class.on]="lang() === 'vi'" (click)="lang.set('vi')">VI</button>
          <button [class.on]="lang() === 'en'" (click)="lang.set('en')">EN</button>
        </div>
        <span class="avatar" title="Khách">K</span>
      </div>
    </header>
    <main><router-outlet /></main>
    <footer class="foot">
      Prototype giao diện · dữ liệu mẫu chưa qua biên tập · Bản đồ: Natural Earth (public domain)
    </footer>
  `,
})
export class AppComponent {
  lang = signal<'vi' | 'en'>('vi');
}
