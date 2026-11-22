import { expect, test } from '@playwright/test'
import { open, register, uniqueEmail } from './helpers.js'

test('клиент бронирует площадку, видит бронь и отменяет её', async ({ page }) => {
  const email = uniqueEmail('booking')
  await register(page, email)

  await page.getByPlaceholder('Поиск по названию').fill('Альфа')
  await page.getByRole('link', { name: /Зал «Альфа»/ }).click()

  await expect(
    page.getByRole('heading', { name: 'Зал «Альфа»' }),
  ).toBeVisible()

  await page.getByLabel('Начало').fill('2031-03-10T10:00')
  await page.getByLabel('Окончание').fill('2031-03-10T12:00')
  await page.getByRole('button', { name: 'Забронировать' }).click()

  await expect(page).toHaveURL(/\/my$/)
  await expect(page.getByRole('heading', { name: 'Мои брони' })).toBeVisible()

  const card = page.locator('.booking', { hasText: 'Зал «Альфа»' })
  await expect(card.getByText('Ожидает подтверждения')).toBeVisible()

  await card.getByRole('button', { name: 'Отменить' }).click()

  await expect(page.getByText('Актуальных броней нет.')).toBeVisible()
  await page.getByRole('button', { name: 'История' }).click()

  const archived = page.locator('.booking', { hasText: 'Зал «Альфа»' })
  await expect(archived.getByText('Отменено')).toBeVisible()
})

test('гость не попадает в «Мои брони»', async ({ page }) => {
  await open(page, '/my')

  await expect(page).toHaveURL(/\/login$/)
  await expect(
    page.getByRole('heading', { name: 'Вход в аккаунт' }),
  ).toBeVisible()
})
