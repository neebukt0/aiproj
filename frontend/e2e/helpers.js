import { expect } from '@playwright/test'

export const API_URL = process.env.E2E_API_URL || 'http://127.0.0.1:8000'

export function uniqueEmail(prefix = 'e2e') {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1000)}@example.com`
}

export async function open(page, path) {
  await page.goto(path, { waitUntil: 'domcontentloaded' })
}

export async function login(page, email, password) {
  await open(page, '/login')
  await page.getByPlaceholder('Email').fill(email)
  await page.getByPlaceholder('Пароль').fill(password)
  await page.getByRole('button', { name: 'Войти' }).click()
  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByRole('link', { name: 'Каталог' })).toBeVisible()
}

export async function register(page, email, password = 'E2ePass123!') {
  await open(page, '/register')
  await page.getByPlaceholder('Email').fill(email)
  await page.getByPlaceholder('Пароль (минимум 8 символов)').fill(password)
  await page.getByRole('button', { name: 'Зарегистрироваться' }).click()
  await expect(page).toHaveURL(/\/$/)
}
