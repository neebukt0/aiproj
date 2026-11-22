import fs from 'node:fs'
import { defineConfig } from '@playwright/test'

// Локально используем установленный Edge/Chrome, чтобы не скачивать Chromium.
// При необходимости можно задать PLAYWRIGHT_CHANNEL=chrome|msedge|chromium.
function detectChannel() {
  if (process.env.PLAYWRIGHT_CHANNEL) return process.env.PLAYWRIGHT_CHANNEL
  if (process.platform !== 'win32') return undefined
  if (
    fs.existsSync(
      'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    )
  ) {
    return 'msedge'
  }
  if (
    fs.existsSync('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')
  ) {
    return 'chrome'
  }
  return undefined
}

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const reuseExistingServer = !process.env.CI

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  outputDir: 'test-results',
  use: {
    baseURL: BASE_URL,
    channel: detectChannel(),
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    locale: 'ru-RU',
  },
  webServer: [
    {
      command: '.venv\\Scripts\\python.exe scripts\\mock_server.py',
      cwd: '../backend',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer,
      timeout: 120_000,
      stdout: 'ignore',
      stderr: 'pipe',
    },
    {
      command: 'npm.cmd run dev -- --host 127.0.0.1 --port 5173',
      cwd: '.',
      url: BASE_URL,
      reuseExistingServer,
      timeout: 120_000,
      stdout: 'ignore',
      stderr: 'pipe',
    },
  ],
})
