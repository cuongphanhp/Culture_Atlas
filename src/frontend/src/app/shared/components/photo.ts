import { Component, input } from '@angular/core';
import { Photo } from '../../core/mock/media';

/** Ảnh luôn kèm ghi công tác giả + giấy phép (BR08). */
@Component({
  selector: 'ca-photo',
  template: `
    <img [src]="photo().src" [alt]="photo().caption ?? ''" />
    <ng-content />
    @if (credit()) {
      <a class="credit" [href]="photo().sourceUrl" target="_blank" rel="noopener">© {{ photo().author || 'Wikimedia Commons' }} · {{ photo().license }}</a>
    }`,
  styles: `
    :host { position: relative; display: block; overflow: hidden; background: #2a2a2a; }
    img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .6s ease; }
    :host(:hover) img { transform: scale(1.04); }
    .credit { position: absolute; right: 6px; bottom: 6px; font-size: .62rem; color: rgb(255 255 255 / .85); background: rgb(0 0 0 / .45);
      padding: 1px 6px; border-radius: 4px; max-width: 70%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; z-index: 2; }`,
})
export class PhotoComponent {
  photo = input.required<Photo>();
  credit = input(true);
}
