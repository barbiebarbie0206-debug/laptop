const DATA_CHANGED = 'app:data-changed'

export function notifyDataChanged() {
  window.dispatchEvent(new CustomEvent(DATA_CHANGED))
}

export function subscribeDataChanged(handler) {
  window.addEventListener(DATA_CHANGED, handler)
  return () => window.removeEventListener(DATA_CHANGED, handler)
}
