<template>
  <v-container fluid class="pa-4">
    <div class="mb-6 animate-fade-in-up">
      <div class="d-flex flex-wrap align-center justify-space-between gap-4">
        <div>
          <h1 class="text-h4 font-weight-medium text-primary mb-1">Timeline</h1>
          <p class="text-body-1 text-secondary">Focus user events with baseline rule flags</p>
        </div>
        <div class="d-flex flex-wrap gap-3 align-center">
          <v-select
            v-model="selectedScenario"
            :items="scenarios"
            item-title="scenario_id"
            item-value="scenario_id"
            label="Scenario"
            variant="outlined"
            density="compact"
            hide-details
            min-width="300"
            @change="loadScenario"
            class="animate-fade-in-up"
            style="animation-delay: 60ms;">
          </v-select>
          <v-select
            v-model="focusUser"
            :items="users"
            item-title="user_id"
            item-value="user_id"
            label="Focus User"
            variant="outlined"
            density="compact"
            hide-details
            min-width="200"
            @change="loadTimeline"
            class="animate-fade-in-up"
            style="animation-delay: 100ms;">
          </v-select>
          <v-btn variant="tonal" color="primary" @click="refreshTimeline" :disabled="loading" class="animate-fade-in-up" style="animation-delay: 140ms;">
            <v-icon start>mdi-refresh</v-icon>
            Refresh
          </v-btn>
        </div>
      </div>
    </div>

    <v-card variant="tonal" class="mb-6 animate-fade-in-up" v-if="baseline" style="animation-delay: 60ms;">
      <v-card-text class="pb-0">
        <div class="d-flex flex-wrap gap-4">
          <div class="d-flex align-center gap-2"><v-icon color="primary">mdi-chart-line</v-icon><span class="text-body-1"><strong>Baseline Logins:</strong> {{ baseline.baseline_login_count }}</span></div>
          <div class="d-flex align-center gap-2"><v-icon :color="baseline.baseline_sufficient ? 'success' : 'warning'">mdi-checkbox-marked-circle-outline</v-icon><span class="text-body-1">Baseline Sufficient: {{ baseline.baseline_sufficient ? 'Yes' : 'No' }}</span></div>
          <div class="d-flex align-center gap-2"><v-icon color="info">mdi-device-outline</v-icon><span class="text-body-1"><strong>Known Devices:</strong> {{ baseline.known_devices.length }}</span></div>
          <div class="d-flex align-center gap-2"><v-icon color="warning">mdi-database-outline</v-icon><span class="text-body-1"><strong>Avg Events/Day:</strong> {{ baseline.avg_events_per_day }}</span></div>
        </div>
      </v-card-text>
    </v-card>

    <v-card variant="tonal" class="mb-6 animate-fade-in-up" style="animation-delay: 80ms;">
      <v-card-title class="d-flex justify-space-between align-center">
        <span class="text-h5 font-weight-medium">Events Timeline</span>
        <div class="d-flex gap-2 align-center">
          <v-checkbox v-model="showFlaggedOnly" label="Flagged Only" density="compact" hide-details></v-checkbox>
          <span class="text-caption">Show only flagged events</span>
        </div>
      </v-card-title>
      <v-card-text class="pt-0"><div ref="chartContainer" style="height: 500px;"></div></v-card-text>
    </v-card>

    <v-card variant="tonal" class="mb-6 animate-fade-in-up" style="animation-delay: 100ms;">
      <v-card-title class="text-h6 font-weight-medium">Legend</v-card-title>
      <v-card-text class="pt-0">
        <v-row dense>
          <v-col cols="12" sm="6" md="3" v-for="item in legendItems" :key="item.label">
            <div class="d-flex align-center gap-2 animate-fade-in-up" :style="{ animationDelay: (index * 40) + 'ms' }">
              <v-chip :color="item.color" size="x-small" variant="tonal" class="white--text">{{ item.label }}</v-chip>
              <span class="text-caption">{{ item.description }}</span>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-card variant="tonal" v-if="selectedEvent" class="animate-slide-in-right">
      <v-card-title class="d-flex justify-space-between align-center">
        <span class="text-h6 font-weight-medium">Evidence Panel</span>
        <v-btn variant="text" color="secondary" @click="selectedEvent = null" size="small"><v-icon start>mdi-close</v-icon> Close</v-btn>
      </v-card-title>
      <v-card-text class="pt-0">
        <v-sheet variant="tonal" class="pa-4" style="font-family: monospace; font-size: 0.85rem; max-height: 400px; overflow: auto;">
          <div class="mb-2"><strong>Event ID:</strong> {{ selectedEvent.event_id }}</div>
          <div class="mb-2"><strong>Timestamp:</strong> {{ selectedEvent.ts }}</div>
          <div class="mb-2"><strong>User:</strong> {{ selectedEvent.user_id }}</div>
          <div class="mb-2"><strong>Event Type:</strong> {{ selectedEvent.event_type }}</div>
          <div class="mb-2"><strong>Device:</strong> {{ selectedEvent.device_id || '\u2014' }}</div>
          <div class="mb-2"><strong>Resource:</strong> {{ selectedEvent.resource || '\u2014' }}</div>
          <div class="mb-2"><strong>Source IP:</strong> {{ selectedEvent.source_ip || '\u2014' }}</div>
          <div class="mb-2"><strong>Outcome:</strong> {{ selectedEvent.outcome }}</div>
          <div class="mb-2"><strong>Details:</strong> {{ selectedEvent.details_untrusted }}</div>
          <div class="mb-2" v-if="selectedEvent.flags && selectedEvent.flags.length > 0">
            <strong>Triggered Rules:</strong>
            <template v-for="flag in selectedEvent.flags" :key="flag.rule">
              <v-chip :color="getFlagColor(flag.rule)" size="small" variant="tonal" class="ms-1 mb-1">{{ flag.rule }}: {{ flag.detail }}</v-chip>
            </template>
          </div>
          <div v-else class="mb-2"><strong>Rules:</strong> None triggered</div>
        </v-sheet>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
import { ref, onMounted, nextTick } from 'vue'
import { useApi } from '@/composables/useApi'

export default {
  name: 'Timeline',
  setup() {
    const { api } = useApi()
    const scenarios = ref([])
    const selectedScenario = ref('')
    const focusUser = ref('')
    const users = ref([])
    const baseline = ref(null)
    const events = ref([])
    const selectedEvent = ref(null)
    const loading = ref(false)
    const showFlaggedOnly = ref(false)
    const chartContainer = ref(null)
    let plotlyLoaded = false

    const legendItems = [
      { label: 'Login', color: '#22D3EE', description: 'Successful login' },
      { label: 'Resource Access', color: '#2DD4BF', description: 'Resource access event' },
      { label: 'Password Reset', color: '#38BDF8', description: 'Password reset event' },
      { label: 'MFA Challenge', color: '#A78BFA', description: 'MFA challenge event' },
      { label: 'Flagged', color: '#F87171', description: 'Flagged by baseline rules' },
      { label: 'Failure', color: '#F87171', description: 'Failed outcome' },
    ]

    const loadScenarios = async () => {
      try {
        const res = await api.get('/api/scenarios')
        scenarios.value = res.data
        if (scenarios.value.length > 0) selectedScenario.value = scenarios.value[0].scenario_id
      } catch (error) { console.error('Failed to load scenarios:', error) }
    }

    const loadUsers = async () => {
      try {
        const res = await api.get('/api/scenarios/' + selectedScenario.value + '/result')
        const userIds = [...new Set(res.data.events.map(e => e.user_id))]
        users.value = userIds.map(u => ({ user_id: u }))
        if (users.value.length > 0) focusUser.value = users.value[0].user_id
      } catch (error) { console.error('Failed to load users:', error) }
    }

    const loadTimeline = async () => {
      if (!selectedScenario.value || !focusUser.value) return
      loading.value = true
      try {
        const res = await api.get('/api/scenarios/' + selectedScenario.value + '/result')
        const data = res.data
        const allEvents = res.data.events
        const focusEvents = allEvents.filter(e => e.user_id == focusUser.value)
        
        const cutoff = res.data.baseline_cutoff
        const baselineEvents = focusEvents.filter(e => e.ts < cutoff && e.event_type == 'login')
        const loginHours = {}
        const knownDevices = new Set()
        const resourceCounts = {}
        
        baselineEvents.forEach(e => {
          const hour = new Date(e.ts).getUTCHours()
          loginHours[hour] = (loginHours[hour] || 0) + 1
          if (e.device_id) knownDevices.add(e.device_id)
          if (e.resource) resourceCounts[e.resource] = (resourceCounts[e.resource] || 0) + 1
        })
        
        baseline.value = {
          baseline_login_count: baselineEvents.length,
          baseline_sufficient: baselineEvents.length >= 20,
          known_devices: Array.from(knownDevices).map(d => ({ device_id: d })),
          avg_events_per_day: focusEvents.length / 30,
          login_hour_histogram: Object.entries(loginHours).map(([hour, count]) => ({ hour: parseInt(hour), count })),
        }
        
        const windowEvents = focusEvents.filter(e => e.ts >= '2024-01-22T00:00:00Z' && e.ts <= '2024-01-31T23:59:59Z')
        const flaggedEventIds = new Set()
        
        const totalLogins = baselineEvents.length
        const hourHist = {}
        baselineEvents.forEach(e => { const hour = new Date(e.ts).getUTCHours(); hourHist[hour] = (hourHist[hour] || 0) + 1 })
        
        for (const e of windowEvents) {
          if (e.event_type == 'login') {
            const hour = new Date(e.ts).getUTCHours()
            const hourCount = hourHist[hour] || 0
            if (totalLogins > 0 && hourCount / totalLogins <= 0.02) {
              flaggedEventIds.add(e.event_id)
              if (!e.flags) e.flags = []
              e.flags.push({ 'rule': 'R1', detail: 'Login at hour ' + hour + ':00 UTC (only ' + hourCount + '/' + totalLogins + ' baseline logins in this hour)' })
            }
          }
        }
        
        const knownDeviceIds = new Set(baseline.value.known_devices.map(d => d.device_id))
        for (const e of windowEvents) {
          if (e.device_id && !knownDeviceIds.has(e.device_id)) {
            flaggedEventIds.add(e.event_id)
            if (!e.flags) e.flags = []
            e.flags.push({ 'rule': 'R2', detail: 'New device \'' + e.device_id + '\' not seen in baseline' })
          }
        }
        
        for (const e of windowEvents) {
          if (e.resource) {
            const count = resourceCounts[e.resource] || 0
            if (count <= 1) {
              flaggedEventIds.add(e.event_id)
              if (!e.flags) e.flags = []
              e.flags.push({ 'rule': 'R3', detail: 'Resource \'' + e.resource + '\' accessed ' + count + ' time(s) in baseline' })
            }
          }
        }
        
        const failedLogins = windowEvents.filter(e => e.event_type == 'login' && e.outcome == 'failure')
        failedLogins.sort((a, b) => new Date(a.ts) - new Date(b.ts))
        for (let i = 0; i < failedLogins.length; i++) {
          const windowStart = new Date(failedLogins[i].ts)
          const windowEnd = new Date(windowStart.getTime() + 10 * 60 * 1000)
          let count = 1
          for (let j = i + 1; j < failedLogins.length; j++) {
            const eventTime = new Date(failedLogins[j].ts)
            if (eventTime <= windowEnd) count += 1
            else break
          }
          if (count >= 3) {
            failedLogins.slice(i, i + count).forEach(e => {
              flaggedEventIds.add(e.event_id)
              if (!e.flags) e.flags = []
              e.flags.push({ 'rule': 'R4', detail: count + ' failed logins in 10 minutes' })
            })
            break
          }
        }
        
        events.value = focusEvents.map(e => ({ ...e, isFlagged: flaggedEventIds.has(e.event_id), flags: e.flags || [] }))
        
        const userIds = [...new Set(res.data.events.map(e => e.user_id))]
        users.value = userIds.map(u => ({ user_id: u }))
        
        if (!focusUser.value && users.value.length > 0) {
          focusUser.value = users.value[0].user_id
        }
        
        await nextTick()
        renderChart()
      } catch (error) { console.error('Failed to load timeline:', error) } finally { loading.value = false }
    }

    const loadScenario = async () => { await loadUsers(); await loadTimeline() }
    const refreshTimeline = async () => { await loadTimeline() }

    const renderChart = async () => {
      if (!chartContainer.value) return
      if (!plotlyLoaded) {
        const plotly = await import('plotly.js-dist')
        window.Plotly = plotly.default
        plotlyLoaded = true
      }
      
      const displayEvents = showFlaggedOnly.value ? events.value.filter(e => e.isFlagged) : events.value
      if (displayEvents.length == 0) {
        chartContainer.value.innerHTML = '<div class="d-flex align-center justify-center" style="height: 100%; color: var(--v-text-disabled);">No events to display</div>'
        return
      }
      
      const traces = {}
      for (const e of displayEvents) {
        const eventType = e.event_type
        if (!traces[eventType]) {
          traces[eventType] = { x: [], y: [], mode: 'markers', type: 'scatter', name: eventType, marker: { size: 12, color: getEventColor(eventType, e.isFlagged), symbol: e.isFlagged ? 'x' : 'circle', line: e.isFlagged ? { width: 2, color: '#F87171' } : undefined }, text: [], hoverinfo: 'text' }
        }
        const date = new Date(e.ts)
        traces[eventType].x.push(date)
        traces[eventType].y.push(eventType)
        traces[eventType].text.push(e.event_id + '<br>' + e.ts + '<br>Device: ' + (e.device_id || '\u2014') + '<br>Resource: ' + (e.resource || '\u2014') + '<br>Outcome: ' + e.outcome)
      }
      
      const data = Object.values(traces)
      const layout = { title: 'Events for ' + focusUser.value + ' (' + displayEvents.length + ' events)', xaxis: { title: 'Time (UTC)', type: 'date' }, yaxis: { title: 'Event Type', type: 'category', categoryorder: 'trace' }, height: 500, hovermode: 'closest', plot_bgcolor: '#0B1120', paper_bgcolor: '#0B1120', font: { color: '#F1F5F9' }, margin: { l: 80, r: 40, t: 60, b: 80 }, showlegend: true, legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 } }
      const config = { responsive: true, displayModeBar: true, modeBarButtonsToRemove: ['lasso2d', 'select2d'] }
      window.Plotly.newPlot(chartContainer.value, data, layout, config)
      
      chartContainer.value.on('plotly_click', (data) => {
        if (data.points && data.points.length > 0) {
          const point = data.points[0]
          const eventId = point.text.split('<br>')[0]
          const event = events.value.find(e => e.event_id == eventId)
          if (event) selectedEvent.value = event
        }
      })
    }

    const getEventColor = (eventType, isFlagged) => {
      if (isFlagged) return '#F87171'
      const colors = { 'login': '#22D3EE', 'resource_access': '#2DD4BF', 'password_reset': '#38BDF8', 'mfa_challenge': '#A78BFA' }
      return colors[eventType] || '#888888'
    }

    const getFlagColor = (rule) => {
      const colors = { 'R1': '#38BDF8', 'R2': '#A78BFA', 'R3': '#FBBF24', 'R4': '#F87171' }
      return colors[rule] || '#888888'
    }

    onMounted(async () => { await loadScenarios(); await loadUsers(); await loadTimeline() })

    return { scenarios, selectedScenario, focusUser, users, baseline, events, selectedEvent, loading, showFlaggedOnly, chartContainer, legendItems, loadScenario, refreshTimeline, getEventColor, getFlagColor }
  }
}
</script>