import { expect, test } from '@playwright/test'
import { login, open, register, uniqueEmail } from './helpers.js'

test('клиент входит и видит каталог с личным кабинетом', async ({ page }) => {
  await login(page, 'client@example.com', 'ClientPass123!')

  await expect(
    page.getByRole('heading', { name: 'Найдите место для мероприятия' }),
  ).toBeVisible()
  await expect(page.getByRole('link', { name: 'Мои брони' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Выйти' })).toBeVisible()
})

test('неверный пароль показывает ошибку входа', async ({ page }) => {
  await open(page, '/login')
  await page.getByPlaceholder('Email').fill('client@example.com')
  await page.getByPlaceholder('Пароль').fill('WrongPassword123!')
  await page.getByRole('button', { name: 'Войти' }).click()

  await expect(page.getByText('Invalid credentials')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Мои брони' })).toHaveCount(0)
})

test('регистрация создаёт клиента и пускает в каталог', async ({ page }) => {
  const email = uniqueEmail('register')

  await register(page, email)

  await expect(page.getByRole('link', { name: 'Мои брони' })).toBeVisible()
  await expect(page.getByText('client', { exact: true })).toBeVisible()
})

test('администратор открывает панель администратора', async ({ page }) => {
  await login(page, 'admin@example.com', 'AdminPass123!')

  await expect(page.getByRole('link', { name: 'Админ' })).toBeVisible()
  await page.getByRole('link', { name: 'Админ' }).click()

  await expect(
    page.getByRole('heading', { name: 'Панель администратора' }),
  ).toBeVisible()
  await expect(page.getByText('client@example.com')).toBeVisible()
  await expect(page.getByText('admin@example.com')).toBeVisible()
})
