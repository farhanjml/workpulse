import Store from 'electron-store'

const DEFAULTS = {
  USER_NAME:            'Farhan Jamaludin',
  PING_INTERVAL:        15,
  IDLE_THRESHOLD:       10,
  OVERDUE_WARNING:      45,
  WORK_START:           '09:00',
  END_OF_DAY:           '18:00',
  HOTKEY:               'Alt+L',
  INTERRUPT_HOTKEY:     'Alt+Shift+L',
  SOUND_THEME:          'soft_chime',
  VOLUME:               60,
  PLAY_ON:              'all',
  START_ON_BOOT:        true,
  DARK_MODE:            true,
  WINDOW_TRACKING:      false,
  CLIPBOARD_HINTS:      true,
  STATUS_BAR_DURATION:  10,
  CLOCKIFY_API_KEY:     '',
  CLOCKIFY_WORKSPACE_ID:'',
  LAST_CLOCKIFY_SYNC:   '',
}

const store = new Store({
  name: 'config',
  defaults: DEFAULTS,
  cwd: 'WorkPulse',
})

export function get(key) {
  return store.get(key, DEFAULTS[key])
}

export function set(key, value) {
  store.set(key, value)
}

export function getAll() {
  const out = {}
  for (const key of Object.keys(DEFAULTS)) {
    out[key] = store.get(key, DEFAULTS[key])
  }
  return out
}

export function saveAll(updates) {
  for (const [key, value] of Object.entries(updates)) {
    store.set(key, value)
  }
}
