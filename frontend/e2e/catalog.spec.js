import { expect, test } from '@playwright/test'
import { open } from './helpers.js'

test.beforeEach(async ({ page }) => {
  await open(page, '/')
})

test('каталог показывает площадки с вместимостью', async ({ page }) => {
  await expect(
    page.getByRole('heading', { name: 'Найдите место для мероприятия' }),
  ).toBeVisible()
  await expect(page.getByRole('link', { name: /Зал «Альфа»/ })).toBeVisible()
  await expect(page.getByText(/Зал · вмещает 80/).first()).toBeVisible()
})

test('поиск по названию оставляет только подходящую площадку', async ({ page }) => {
  await page.getByPlaceholder('Поиск по названию').fill('Инвестор')

  await expect(
    page.getByRole('link', { name: /Переговорная «Инвестор»/ }),
  ).toBeVisible()
  await expect(page.getByRole('link', { name: /Зал «Альфа»/ })).toHaveCount(0)
})

test('фильтр по типу скрывает залы', async ({ page }) => {
  await page.getByRole('combobox').selectOption('private_room')

  await expect(
    page.getByRole('link', { name: /Переговорная «Инвестор»/ }),
  ).toBeVisible()
  await expect(page.getByRole('link', { name: /Зал «Альфа»/ })).toHaveCount(0)
})

test('несуществующий запрос показывает пустое состояние', async ({ page }) => {
  await page.getByPlaceholder('Поиск по названию').fill('НесуществующийЗаг123')

  await expect(
    page.getByText(/По вашему запросу ничего не найдено/),
  ).toBeVisible()
})
