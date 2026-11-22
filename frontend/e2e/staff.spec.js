import { expect, test } from '@playwright/test'
import { API_URL, login, open, uniqueEmail } from './helpers.js'

test('сотрудник подтверждает и завершает бронь в панели', async ({
  page,
  request,
}) => {
  const clientLogin = await request.post(`${API_URL}/api/auth/login`, {
    data: { email: 'client@example.com', password: 'ClientPass123!' },
  })
  const { access } = await clientLogin.json()
  const resources = await (
    await request.get(`${API_URL}/api/resources`)
  ).json()
  const date = '2031-05-12'

  const created = await request.post(`${API_URL}/api/bookings`, {
    headers: { Authorization: `Bearer ${access}` },
    data: {
      resource_id: resources[0].id,
      start_at: `${date}T09:00:00Z`,
      end_at: `${date}T11:00:00Z`,
    },
  })
  expect(created.ok()).toBeTruthy()
  const booking = await created.json()

  await login(page, 'employee@example.com', 'EmpPass123!')
  await open(page, '/panel')
  await page.getByLabel('Дата').fill(date)

  const card = page.locator('.booking', {
    hasText: `#${booking.id.slice(0, 8)}`,
  })
  await expect(card).toBeVisible()
  await card.getByRole('button', { name: 'Подтвердить' }).click()
  await expect(card.getByText('Подтверждено')).toBeVisible()

  await card.getByRole('button', { name: 'Завершить' }).click()
  await expect(card.getByText('Завершено')).toBeVisible()
})

test('администратор создаёт пользователя', async ({ page }) => {
  await login(page, 'admin@example.com', 'AdminPass123!')
  await open(page, '/admin')

  const email = uniqueEmail('admin')
  await page.getByPlaceholder('Email').fill(email)
  await page
    .getByPlaceholder('Пароль (минимум 8 символов)')
    .fill('E2ePass123!')
  await page.getByRole('button', { name: 'Создать' }).click()

  await expect(page.getByText(`Пользователь ${email} создан`)).toBeVisible()
  await expect(page.getByRole('cell', { name: email })).toBeVisible()
})

test('сотрудник строит отчёт и смотрит журнал', async ({ page }) => {
  await login(page, 'employee@example.com', 'EmpPass123!')

  await open(page, '/reports')
  await page.getByRole('button', { name: 'Построить' }).click()
  await expect(page.getByRole('columnheader', { name: 'Всего' })).toBeVisible()

  await open(page, '/logs')
  await expect(
    page.getByRole('heading', { name: 'Журнал действий' }),
  ).toBeVisible()
  await expect(page.locator('table tbody tr').first()).toBeVisible()
})
