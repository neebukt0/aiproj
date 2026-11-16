import { useState } from 'react'
import { resourceImage } from '../utils/resourceImage.js'

// Картинка объекта с фолбэком на иконку, если внешний image API недоступен.
export default function ResourceMedia({ resource, icon = '🎫', className = 'card-media' }) {
  const [failed, setFailed] = useState(false)

  return (
    <div className={className}>
      {failed ? (
        <span aria-hidden="true">{icon}</span>
      ) : (
        <img
          src={resourceImage(resource)}
          alt={resource?.name || 'Объект'}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      )}
    </div>
  )
}
