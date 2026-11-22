import { describe, expect, it } from 'vitest'
import { resourceImage } from './resourceImage.js'

describe('resourceImage', () => {
  it('возвращает явную картинку объекта', () => {
    expect(resourceImage({ id: 'r1', image: 'https://cdn.example/a.jpg' })).toBe(
      'https://cdn.example/a.jpg',
    )
  })

  it('строит ссылку Picsum по id', () => {
    expect(resourceImage({ id: 'abc-123' })).toBe(
      'https://picsum.photos/seed/abc-123/640/360',
    )
  })

  it('использует название, если id отсутствует', () => {
    expect(resourceImage({ name: 'Зал «Альфа»' })).toBe(
      'https://picsum.photos/seed/%D0%97%D0%B0%D0%BB%20%C2%AB%D0%90%D0%BB%D1%8C%D1%84%D0%B0%C2%BB/640/360',
    )
  })

  it('подставляет запасной seed для пустого объекта', () => {
    expect(resourceImage()).toBe(
      'https://picsum.photos/seed/meropriyatie/640/360',
    )
    expect(resourceImage({})).toBe(
      'https://picsum.photos/seed/meropriyatie/640/360',
    )
  })
})
