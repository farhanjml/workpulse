import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/globals.css'

import PingPopup   from './windows/PingPopup'
import QuickLog    from './windows/QuickLog'
import Interrupt   from './windows/Interrupt'
import Summary     from './windows/Summary'
import Settings    from './windows/Settings'
import StatusBar   from './windows/StatusBar'

const WINDOWS = { ping: PingPopup, quick: QuickLog, interrupt: Interrupt, summary: Summary, settings: Settings, statusbar: StatusBar }

function App() {
  useEffect(() => {
    window.api.getConfig().then(cfg => {
      document.documentElement.setAttribute('data-theme', cfg.DARK_MODE ? 'dark' : 'light')
    })
    const off = window.api.on('theme', (isDark) => {
      document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
    })
    return () => off?.()
  }, [])

  const params = new URLSearchParams(window.location.search)
  const windowName = params.get('window') || 'ping'
  const Window = WINDOWS[windowName] || PingPopup

  return <Window />
}

createRoot(document.getElementById('root')).render(<App />)
