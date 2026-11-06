/**
 * Tiện ích test chung.
 * Quy ước tên test: bắt đầu bằng mã tiêu chí "[ACxx.y]" (docs/06-acceptance-criteria.md)
 * để test truy vết (src/backend/tests/test_traceability.py) đếm được.
 * Tiêu chí UI chưa làm: dùng `it.skip('[ACxx.y] PENDING …')` và bỏ `.skip` khi tính năng xong.
 */
import { Provider, Type } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

/** Dựng component trong TestBed, gán input, chờ ổn định. */
export async function render<T>(cmp: Type<T>, inputs: Record<string, unknown> = {}, providers: Provider[] = []): Promise<ComponentFixture<T>> {
  await TestBed.configureTestingModule({ imports: [cmp], providers: [provideRouter([]), ...providers] }).compileComponents();
  const f = TestBed.createComponent(cmp);
  for (const [k, v] of Object.entries(inputs)) f.componentRef.setInput(k, v);
  f.detectChanges();
  await f.whenStable();
  return f;
}

export const $ = (f: ComponentFixture<unknown>, sel: string) => (f.nativeElement as HTMLElement).querySelector(sel) as HTMLElement | null;
export const $$ = (f: ComponentFixture<unknown>, sel: string) => [...(f.nativeElement as HTMLElement).querySelectorAll(sel)] as HTMLElement[];
/** Toàn bộ chữ trong component. */
export const text = (f: ComponentFixture<unknown>) => (f.nativeElement as HTMLElement).textContent ?? '';
