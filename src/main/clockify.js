import axios from 'axios'
import path from 'path'
import fs from 'fs'
import { app } from 'electron'
import { get, set } from './config.js'
import { markClockifySynced, getUnsyncedEntries } from './database.js'

const BASE = 'https://api.clockify.me/api/v1'

function headers() {
  return { 'X-Api-Key': get('CLOCKIFY_API_KEY'), 'Content-Type': 'application/json' }
}

export function isConfigured() {
  return !!(get('CLOCKIFY_API_KEY') && get('CLOCKIFY_WORKSPACE_ID'))
}

function toUTC(dateStr, timeStr) {
  // MYT = UTC+8
  const [h, m] = timeStr.split(':').map(Number)
  const local = new Date(`${dateStr}T${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:00+08:00`)
  return local.toISOString()
}

export async function pushEntry(entry) {
  if (!isConfigured()) return false
  const wsId = get('CLOCKIFY_WORKSPACE_ID')
  // Find clockify project id from projects.json
  const projects = loadProjects()
  const proj = projects.find(p => p.id === entry.project_id)
  if (!proj?.clockify_project_id) return false
  try {
    await axios.post(
      `${BASE}/workspaces/${wsId}/time-entries`,
      {
        start: toUTC(entry.date, entry.start_time),
        end: toUTC(entry.date, entry.end_time),
        description: entry.task,
        projectId: proj.clockify_project_id,
        billable: false,
      },
      { headers: headers() }
    )
    markClockifySynced(entry.id)
    return true
  } catch {
    return false
  }
}

export async function pushAllUnsynced() {
  if (!isConfigured()) return
  const entries = getUnsyncedEntries()
  for (const e of entries) {
    await pushEntry(e)
  }
}

export async function fetchProjects(wsId) {
  const res = await axios.get(`${BASE}/workspaces/${wsId}/projects`, {
    headers: headers(),
    params: { archived: false, 'page-size': 500 }
  })
  return (res.data || []).filter(p => !p.archived)
}

export async function fetchTasks(wsId, projectId) {
  const res = await axios.get(`${BASE}/workspaces/${wsId}/projects/${projectId}/tasks`, {
    headers: headers(),
    params: { status: 'ACTIVE' }
  })
  return (res.data || []).map(t => t.name)
}

function slugify(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '')
}

function projectsFilePath() {
  // Always use userData so we have write access in both dev and packaged
  return path.join(app.getPath('userData'), 'projects.json')
}

export function loadProjects() {
  try {
    return JSON.parse(fs.readFileSync(projectsFilePath(), 'utf8'))
  } catch {
    return []
  }
}

export function saveProjects(projects) {
  const fp = projectsFilePath()
  fs.mkdirSync(path.dirname(fp), { recursive: true })
  fs.writeFileSync(fp, JSON.stringify(projects, null, 2), 'utf8')
}

export async function syncProjectsToCache() {
  if (!isConfigured()) return false
  const wsId = get('CLOCKIFY_WORKSPACE_ID')
  try {
    const remote = await fetchProjects(wsId)
    const existing = loadProjects()
    // Build lookup: clockify_project_id → local id
    const idByClockify = {}
    for (const p of existing) {
      if (p.clockify_project_id) idByClockify[p.clockify_project_id] = p.id
    }
    const merged = []
    for (const rp of remote) {
      const localId = idByClockify[rp.id] || slugify(rp.name)
      let tasks = []
      try { tasks = await fetchTasks(wsId, rp.id) } catch {}
      merged.push({
        id: localId,
        name: rp.name,
        clockify_project_id: rp.id,
        tasks,
      })
    }
    saveProjects(merged)
    set('LAST_CLOCKIFY_SYNC', new Date().toLocaleString())
    return true
  } catch {
    return false
  }
}
