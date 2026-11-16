// Внешний image API без ключа и регистрации — Lorem Picsum.
// Seed детерминированный: один и тот же объект всегда получает одну картинку.
const PICSUM = 'https://picsum.photos/seed'

export function resourceImage(resource) {
  if (resource?.image) return resource.image
  const seed = resource?.id || resource?.name || 'meropriyatie'
  return `${PICSUM}/${encodeURIComponent(seed)}/640/360`
}
