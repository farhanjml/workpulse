const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  // Config
  getConfig:    ()       => ipcRenderer.invoke('config:get-all'),
  saveConfig:   (data)   => ipcRenderer.invoke('config:save', data),

  // Projects
  getProjects:  ()       => ipcRenderer.invoke('projects:load'),
  syncProjects: ()       => ipcRenderer.invoke('projects:sync'),

  // Database
  getActive:    ()       => ipcRenderer.invoke('db:get-active'),
  logEntry:     (data)   => ipcRenderer.invoke('db:log-entry', data),
  extendActive: ()       => ipcRenderer.invoke('db:extend-active'),
  endCurrent:   (t)      => ipcRenderer.invoke('db:end-current', t),
  logInterrupt: (data)   => ipcRenderer.invoke('db:log-interrupt', data),
  getEntries:   (date)   => ipcRenderer.invoke('db:get-entries', date),
  countToday:   ()       => ipcRenderer.invoke('db:count-today'),
  totalMinutes: (date)   => ipcRenderer.invoke('db:total-minutes', date),
  deleteEntry:  (id)     => ipcRenderer.invoke('db:delete-entry', id),

  // Events from main → renderer
  on: (channel, cb) => {
    ipcRenderer.on(channel, (_e, ...args) => cb(...args))
    return () => ipcRenderer.removeAllListeners(channel)
  },
  once: (channel, cb) => ipcRenderer.once(channel, (_e, ...args) => cb(...args)),
})
