import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', title: 'CultureAtlas AI — Khám phá', loadComponent: () => import('./features/explorer/explorer.page').then((m) => m.ExplorerPage) },
  { path: 'countries/:iso', title: 'Hồ sơ quốc gia', loadComponent: () => import('./features/country/country.page').then((m) => m.CountryPage) },
  { path: 'guide', title: 'AI Cultural Guide', loadComponent: () => import('./features/ai-guide/ai-guide.page').then((m) => m.AiGuidePage) },
  { path: 'compare', title: 'So sánh văn hoá', loadComponent: () => import('./features/compare/compare.page').then((m) => m.ComparePage) },
  { path: 'quiz', title: 'Culture Quiz', loadComponent: () => import('./features/quiz/quiz.page').then((m) => m.QuizPage) },
  { path: 'admin', title: 'Quản trị nội dung', loadComponent: () => import('./features/admin/admin.page').then((m) => m.AdminPage) },
  { path: '**', redirectTo: '' },
];
