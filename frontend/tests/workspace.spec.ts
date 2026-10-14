import { expect, test } from '@playwright/test'

test('Digital Factory Workspace can submit inventory analysis through the Platform mock', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Digital Factory Workspace' })).toBeVisible()
  await expect(page.getByText('MSW Platform Mock 已连接')).toBeVisible()
  await expect(page.getByRole('heading', { name: '上下文' })).toBeVisible()
  await expect(page.getByRole('complementary').getByText('WH-001')).toBeVisible()

  await page.getByRole('button', { name: '库存分析' }).click()

  await expect(page.getByText('TASK-001').first()).toBeVisible()
  await expect(page.getByText('inventory.analyze').first()).toBeVisible()
  await expect(page.getByText('COMPLETED').first()).toBeVisible()
  await expect(page.getByText(/MAT-001 当前库存/)).toBeVisible()
})
