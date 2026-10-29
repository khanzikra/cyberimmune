<template>
  <v-container fluid class="pa-4 timeline-page">
    <!-- Header with staggered entrance -->
    <div class="mb-6 page-header">
      <div class="d-flex flex-wrap align-center justify-space-between gap-4 header-content">
        <div class="header-text">
          <h1 class="text-h4 font-weight-medium text-primary mb-1">Timeline</h1>
          <p class="text-body-1 text-secondary">Focus user events with baseline rule flags</p>
        </div>
        <div class="d-flex flex-wrap gap-3 align-center header-controls">
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
            class="stagger-item">
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
            class="stagger-item">
          </v-select>
          <v-btn variant="tonal" color="primary" @click="refreshTimeline" :disabled="loading" class="stagger-item press-down">
            <v-icon start>mdi-refresh</v-icon>
            Refresh
          </v-btn>
        </div>
      </div>
    </div>

    <!-- KPI Cards Row - staggered entrance with hover lift -->
    <v-row dense class="mb-6 kpi-row" v-if="baseline">
      <v-col cols="12" sm="6" md="3" v-for="(kpi, index) in kpiCards" :key="kpi.key" :class="['kpi-col', `stagger-${index + 1}`]">
        <v-card variant="tonal" class="kpi-card hover-lift card-entrance">
          <v-card-text class="pb-3">
            <div class="d-flex align-center gap-3">
              <v-icon :size="28" :color="kpi.iconColor" class="status-dot kpi-icon">{{ kpi.icon }}</v-icon>
              <div>
                <div class="text-caption text-secondary">{{ kpi.label }}</div>
                <div class="text-h6 font-weight-medium kpi-value counter-up" :style="{ animationDelay: `${(index + 1) * 60}ms` }">{{ kpi.value }}</div>
              </div>
            </div>
            <div v-if="kpi.subtext" class="mt-1 text-caption text-secondary">{{ kpi.subtext }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Timeline Chart Card -->
    <v-card variant="tonal" class="mb-6 chart-card hover-lift">
      <v-card-title class="d-flex justify-space-between align-center pb-3">
        <div class="d-flex align-center gap-3">
          <v-icon size="28" color="primary" class="chart-title-icon">mdi-chart-timeline</v-icon>
          <span class="text-h5 font-weight-medium">Events Timeline</span>
        </div>
        <div class="d-flex gap-2 align-center">
          <v-chip
            :color="showFlaggedOnly ? 'primary' : 'surface-variant'"
            variant="outlined"
            size="small"
            @click="showFlaggedOnly = !showFlaggedOnly"
            class="cursor-pointer filter-chip press-down">
            <v-icon start size="16">mdi-filter-variant</v-icon>
            {{ showFlaggedOnly ? 'Flagged Only' : 'All Events' }}
          </v-chip>
          <span class="text-caption text-secondary event-count">{{ displayEvents.length }} events</span>
        </div>
      </v-card-title>
      <v-card-text class="pt-0">
        <div ref="chartContainer" class="chart-container" style="height: 500px;"></div>
        <div v-if="displayEvents.length === 0" class="empty-chart d-flex align-center justify-center">
          <div class="text-center">
            <v-icon size="64" color="text-disabled" class="mb-3 animate-float">mdi-calendar-clock</v-icon>
            <div class="text-h6 text-secondary">No events to display</div>
            <div class="text-caption text-disabled mt-1">Try adjusting filters or selecting a different user</div>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Legend with micro-interactions -->
    <v-card variant="tonal" class="mb-6 legend-card">
      <v-card-title class="d-flex align-center gap-2 pb-3">
        <v-icon color="primary">mdi-palette-outline</v-icon>
        <span class="text-h6 font-weight-medium">Event Types</span>
      </v-card-title>
      <v-card-text class="pt-0">
        <v-row dense>
          <v-col cols="12" sm="6" md="3" v-for="(item, index) in legendItems" :key="item.label" class="stagger-item">
            <div class="legend-item hover-scale badge-pop" :style="{ animationDelay: `${(index % 6) * 40 + 40}ms` }">
              <v-chip :color="item.color" size="x-small" variant="tonal" class="white--text legend-chip">{{ item.label }}</v-chip>
              <span class="text-caption legend-text">{{ item.description }}</span>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Evidence Panel - slides in from right with 3D depth -->
    <transition name="evidence-panel" mode="out-in">
      <v-card
        v-if="selectedEvent"
        key="evidence-panel"
        variant="tonal"
        class="evidence-panel hover-lift press-down"
        style="position: sticky; top: 24px; z-index: 10;">
        <v-card-title class="d-flex justify-space-between align-center pb-3">
          <div class="d-flex align-center gap-3">
            <v-icon :size="28" :color="getFlagColor(selectedEvent.flags?.[0]?.rule || 'R1')" class="status-dot">
              mdi-shield-alert
            </v-icon>
            <span class="text-h6 font-weight-medium">Evidence Panel</span>
          </div>
          <v-btn variant="text" color="secondary" @click="closeEvidencePanel" size="small" class="press-down">
            <v-icon start>mdi-close</v-icon> Close
          </v-btn>
        </v-card-title>
        <v-card-text class="pt-0">
          <v-sheet variant="tonal" class="pa-4 evidence-sheet" style="font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.8rem; max-height: 500px; overflow: auto;">
            <div class="evidence-grid">
              <div class="evidence-row">
                <span class="evidence-label">Event ID</span>
                <span class="evidence-value font-weight-medium">{{ selectedEvent.event_id }}</span>
              </div>
              <div class="evidence-row">
                <span class="evidence-label">Timestamp</span>
                <span class="evidence-value">{{ formatTimestamp(selectedEvent.ts) }}</span>
              </div>
              <div class="evidence-row">
                <span class="evidence-label">User</span>
                <span class="evidence-value">{{ selectedEvent.user_id }}</span>
              </div>
              <div class="evidence-row">
                <span class="evidence-label">Event Type</span>
                <span class="evidence-value">
                  <v-chip :color="getEventColor(selectedEvent.event_type, selectedEvent.isFlagged)" size="small" variant="tonal">
                    {{ formatEventType(selectedEvent.event_type) }}
                  </v-chip>
                </span>
              </div>
              <div class="evidence-row">
                <span class="evidence-label">Device</span>
                <span class="evidence-value">{{ selectedEvent.device_id || '—' }}</span>
              </div>
              <div class="evidence-row">
                <span class="evidence-label">Resource</span>
                <span class="evidence-value">{{ selectedEvent.resource || '—' }}</span>
              </div>
              <div class="evidence-row">
                <span class="evidence-label">Source IP</span>
                <span class="evidence-value">{{ selectedEvent.source_ip || '—' }}</span>
              </div>
              <div class="evidence-row">
                <span class="evidence-label">Outcome</span>
                <span class="evidence-value">
                  <v-chip
                    :color="selectedEvent.outcome === 'success' ? 'success' : 'error'"
                    size="small"
                    variant="tonal">
                    {{ selectedEvent.outcome }}
                  </v-chip>
                </span>
              </div>
              <div class="evidence-row full-width">
                <span class="evidence-label">Details</span>
                <span class="evidence-value evidence-details">{{ selectedEvent.details_untrusted }}</span>
              </div>
            </div>

            <div v-if="selectedEvent.flags && selectedEvent.flags.length > 0" class="mt-4 pt-4 border-top flagged-rules">
              <div class="d-flex align-center gap-2 mb-3">
                <v-icon color="warning" class="status-dot status-dot--pending">mdi-flag</v-icon>
                <span class="text-subtitle-1 font-weight-medium">Triggered Rules ({{ selectedEvent.flags.length }})</span>
              </div>
              <v-row dense>
                <v-col cols="12" sm="6" v-for="flag in selectedEvent.flags" :key="flag.rule" class="stagger-item">
                  <v-chip
                    :color="getFlagColor(flag.rule)"
                    size="small"
                    variant="tonal"
                    class="flag-chip hover-lift press-down"
                    :class="`flag-${flag.rule.toLowerCase()}`">
                    <v-icon start size="14" class="mr-1">{{ getFlagIcon(flag.rule) }}</v-icon>
                    <strong>{{ flag.rule }}</strong>: {{ flag.detail }}
                  </v-chip>
                </v-col>
              </v-row>
            </div>
            <div v-else class="mt-4 pt-4 border-top text-center">
              <v-icon color="success" size="32" class="mb-2 animate-scale-in">mdi-shield-check</v-icon>
              <div class="text-body-2 text-secondary">No rules triggered for this event</div>
            </div>
          </v-sheet>
        </v-card-text>
      </v-card>
    </transition>

    <!-- Scroll progress indicator -->
    <div class="scroll-progress" :style="{ width: scrollProgress + '%' }" aria-hidden="true"></div>
  </v-container>
</template>

<script>
import { ref, onMounted, nextTick, onUnmounted, computed } from 'vue'
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
    let scrollObserver = null
    const scrollProgress = ref(0)

    const legendItems = [
      { label: 'Login', color: '#22D3EE', description: 'Successful login' },
      { label: 'Resource Access', color: '#2DD4BF', description: 'Resource access event' },
      { label: 'Password Reset', color: '#38BDF8', description: 'Password reset event' },
      { label: 'MFA Challenge', color: '#A78BFA', description: 'MFA challenge event' },
      { label: 'Flagged', color: '#F87171', description: 'Flagged by baseline rules' },
      { label: 'Failure', color: '#F87171', description: 'Failed outcome' },
    ]

    const kpiCards = computed(() => {
      if (!baseline.value) return []
      return [
        {
          key: 'logins',
          label: 'Baseline Logins',
          value: baseline.value.baseline_login_count,
          icon: 'mdi-login',
          iconColor: 'primary',
          subtext: 'Total baseline period'
        },
        {
          key: 'sufficiency',
          label: 'Baseline Sufficient',
          value: baseline.value.baseline_sufficient ? 'Yes' : 'No',
          icon: baseline.value.baseline_sufficient ? 'mdi-check-circle' : 'mdi-alert-circle',
          iconColor: baseline.value.baseline_sufficient ? 'success' : 'warning',
          subtext: baseline.value.baseline_sufficient ? 'Meets threshold' : 'Below 20 logins'
        },
        {
          key: 'devices',
          label: 'Known Devices',
          value: baseline.value.known_devices.length,
          icon: 'mdi-device-outline',
          iconColor: 'info',
          subtext: 'Unique devices in baseline'
        },
        {
          key: 'avgEvents',
          label: 'Avg Events/Day',
          value: baseline.value.avg_events_per_day?.toFixed(1) || '0',
          icon: 'mdi-chart-line',
          iconColor: 'warning',
          subtext: 'Over 30-day window'
        }
      ]
    })

    const displayEvents = computed(() => {
      return showFlaggedOnly.value
        ? events.value.filter(e => e.isFlagged)
        : events.value
    })

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
        initScrollAnimations()
      } catch (error) { console.error('Failed to load timeline:', error) } finally { loading.value = false }
    }

    const loadScenario = async () => { await loadUsers(); await loadTimeline() }
    const refreshTimeline = async () => { await loadTimeline() }

    const closeEvidencePanel = () => {
      selectedEvent.value = null
    }

    const renderChart = async () => {
      if (!chartContainer.value) return
      if (!plotlyLoaded) {
        const plotly = await import('plotly.js-dist')
        window.Plotly = plotly.default
        plotlyLoaded = true
      }

      const eventsToShow = displayEvents.value
      if (eventsToShow.length == 0) {
        chartContainer.value.innerHTML = ''
        return
      }

      const traces = {}
      for (const e of eventsToShow) {
        const eventType = e.event_type
        if (!traces[eventType]) {
          traces[eventType] = { x: [], y: [], mode: 'markers', type: 'scatter', name: eventType, marker: { size: 14, color: getEventColor(eventType, e.isFlagged), symbol: e.isFlagged ? 'x' : 'circle', line: e.isFlagged ? { width: 2, color: '#F87171' } : undefined }, text: [], hoverinfo: 'text' }
        }
        const date = new Date(e.ts)
        traces[eventType].x.push(date)
        traces[eventType].y.push(eventType)
        traces[eventType].text.push(e.event_id + '<br>' + e.ts + '<br>Device: ' + (e.device_id || '\u2014') + '<br>Resource: ' + (e.resource || '\u2014') + '<br>Outcome: ' + e.outcome)
      }

      const data = Object.values(traces)
      const layout = {
        title: { text: 'Events for ' + focusUser.value + ' (' + eventsToShow.length + ' events)', font: { size: 16, color: '#F1F5F9' } },
        xaxis: { title: 'Time (UTC)', type: 'date', gridcolor: 'rgba(255,255,255,0.05)', zerolinecolor: 'rgba(255,255,255,0.1)' },
        yaxis: { title: 'Event Type', type: 'category', categoryorder: 'trace', gridcolor: 'rgba(255,255,255,0.05)' },
        height: 500,
        hovermode: 'closest',
        plot_bgcolor: '#0B1120',
        paper_bgcolor: '#0B1120',
        font: { color: '#F1F5F9', family: 'Inter, system-ui, sans-serif' },
        margin: { l: 80, r: 40, t: 60, b: 80 },
        showlegend: true,
        legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1, font: { size: 11 } },
        hoverlabel: { bgcolor: '#1E293B', bordercolor: '#334155', font: { size: 12, family: 'JetBrains Mono, monospace' } }
      }
      const config = { responsive: true, displayModeBar: true, modeBarButtonsToRemove: ['lasso2d', 'select2d'], displaylogo: false }
      window.Plotly.newPlot(chartContainer.value, data, layout, config)

      chartContainer.value.on('plotly_click', (data) => {
        if (data.points && data.points.length > 0) {
          const point = data.points[0]
          const eventId = point.text.split('<br>')[0]
          const event = events.value.find(e => e.event_id == eventId)
          if (event) selectedEvent.value = event
        }
      })

      chartContainer.value.on('plotly_hover', (data) => {
        if (data.points && data.points.length > 0) {
          chartContainer.value.style.cursor = 'pointer'
        }
      })

      chartContainer.value.on('plotly_unhover', () => {
        chartContainer.value.style.cursor = 'default'
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

    const getFlagIcon = (rule) => {
      const icons = { 'R1': 'mdi-clock-alert', 'R2': 'mdi-device-alert', 'R3': 'mdi-database-alert', 'R4': 'mdi-login-variant' }
      return icons[rule] || 'mdi-alert'
    }

    const formatTimestamp = (ts) => {
      const date = new Date(ts)
      return date.toLocaleString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        hour12: false, timeZone: 'UTC'
      }) + ' UTC'
    }

    const formatEventType = (type) => {
      const map = { 'login': 'Login', 'resource_access': 'Resource Access', 'password_reset': 'Password Reset', 'mfa_challenge': 'MFA Challenge' }
      return map[type] || type
    }

    const initScrollAnimations = () => {
      if (scrollObserver) scrollObserver.disconnect()

      const cards = document.querySelectorAll('.timeline-page .kpi-card, .timeline-page .chart-card, .timeline-page .legend-card')
      scrollObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('in-view')
            scrollObserver.unobserve(entry.target)
          }
        })
      }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' })

      cards.forEach(card => scrollObserver.observe(card))

      // Scroll progress indicator
      const handleScroll = () => {
        const scrollTop = window.scrollY
        const docHeight = document.documentElement.scrollHeight - window.innerHeight
        scrollProgress.value = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0
      }
      window.addEventListener('scroll', handleScroll, { passive: true })

      // Store cleanup
      window.__timelineCleanup = () => {
        window.removeEventListener('scroll', handleScroll)
        if (scrollObserver) scrollObserver.disconnect()
      }
    }

    onMounted(async () => {
      await loadScenarios()
      await loadUsers()
      await loadTimeline()
    })

    onUnmounted(() => {
      if (window.__timelineCleanup) window.__timelineCleanup()
      if (scrollObserver) scrollObserver.disconnect()
    })

    return {
      scenarios, selectedScenario, focusUser, users, baseline, events, selectedEvent, loading,
      showFlaggedOnly, chartContainer, legendItems, kpiCards, displayEvents,
      loadScenario, refreshTimeline, closeEvidencePanel,
      getEventColor, getFlagColor, getFlagIcon, formatTimestamp, formatEventType, scrollProgress
    }
  }
}
</script>

<style scoped>
.timeline-page {
  --primary-glow: rgba(34, 211, 238, 0.15);
  --surface-elevated: rgba(15, 23, 42, 0.8);
}

.page-header {
  opacity: 0;
  animation: fade-in-up 0.6s cubic-bezier(0.33, 1, 0.68, 1) forwards;
}

.header-content {
  backdrop-filter: blur(8px);
  background: linear-gradient(135deg, var(--v-surface-variant) 0%, transparent 100%);
  border-radius: 16px;
  padding: 16px 20px;
  border: 1px solid rgba(255,255,255,0.05);
}

.header-text h1 {
  background: linear-gradient(135deg, var(--v-primary-base), #22D3EE);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-controls .stagger-item {
  opacity: 0;
  animation: fade-in-up 0.5s cubic-bezier(0.33, 1, 0.68, 1) forwards;
}
.header-controls .stagger-item:nth-child(1) { animation-delay: 120ms; }
.header-controls .stagger-item:nth-child(2) { animation-delay: 160ms; }
.header-controls .stagger-item:nth-child(3) { animation-delay: 200ms; }

.kpi-row {
  opacity: 0;
  animation: fade-in-up 0.6s cubic-bezier(0.33, 1, 0.68, 1) 100ms forwards;
}

.kpi-col {
  padding: 4px;
}

.kpi-card {
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.7));
  border: 1px solid rgba(255,255,255,0.04);
  backdrop-filter: blur(12px);
  transition: all 0.3s cubic-bezier(0.33, 1, 0.68, 1);
  overflow: hidden;
}

.kpi-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--v-primary-base), #22D3EE, #A78BFA);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.kpi-card:hover::before {
  opacity: 1;
}

.kpi-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, currentColor 0%, color-mix(in srgb, currentColor 50%, transparent) 100%);
  border-radius: 12px;
  box-shadow: 0 4px 16px -4px currentColor;
}

.counter-up {
  opacity: 0;
  animation: count-up 0.8s cubic-bezier(0.33, 1, 0.68, 1) forwards;
}

.chart-card {
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.8));
  border: 1px solid rgba(255,255,255,0.04);
  backdrop-filter: blur(12px);
  overflow: hidden;
}

.chart-title-icon {
  animation: pulse-subtle 3s ease-in-out infinite;
}

.filter-chip {
  transition: all 0.2s cubic-bezier(0.33, 1, 0.68, 1);
}
.filter-chip:hover {
  transform: scale(1.02);
}

.event-count {
  font-variant-numeric: tabular-nums;
}

.chart-container {
  border-radius: 8px;
  overflow: hidden;
}

.empty-chart {
  padding: 40px;
  background: rgba(0,0,0,0.2);
}

.animate-float {
  animation: float 3s ease-in-out infinite;
}

.legend-card {
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.7));
  border: 1px solid rgba(255,255,255,0.04);
  backdrop-filter: blur(12px);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  transition: all 0.2s cubic-bezier(0.33, 1, 0.68, 1);
  background: rgba(255,255,255,0.02);
}

.legend-item:hover {
  background: rgba(255,255,255,0.05);
  transform: translateX(4px);
}

.legend-chip {
  flex-shrink: 0;
  box-shadow: 0 2px 8px -2px currentColor;
}

.legend-text {
  font-weight: 500;
}

/* Evidence Panel Animations */
.evidence-panel {
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.9));
  border: 1px solid rgba(255,255,255,0.06);
  backdrop-filter: blur(20px);
  box-shadow: 0 24px 48px -12px rgba(0,0,0,0.4);
}

.evidence-sheet {
  background: linear-gradient(180deg, #0B1120 0%, #111827 100%);
  border: 1px solid rgba(255,255,255,0.03);
  border-radius: 12px;
}

.evidence-grid {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 10px 16px;
  font-size: 0.8rem;
  line-height: 1.6;
}

.evidence-row {
  display: contents;
}

.evidence-label {
  color: var(--v-text-disabled);
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 500;
  padding-top: 2px;
}

.evidence-value {
  color: var(--v-text-primary);
  word-break: break-word;
}

.evidence-value .v-chip {
  font-weight: 600;
}

.evidence-details {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.75rem;
  background: rgba(0,0,0,0.3);
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.05);
  max-height: 100px;
  overflow: auto;
}

.evidence-row.full-width {
  grid-column: 1 / -1;
}

.flagged-rules {
  animation: fade-in-up 0.4s cubic-bezier(0.33, 1, 0.68, 1);
}

.flag-chip {
  font-weight: 500;
  letter-spacing: 0.01em;
  transition: all 0.2s cubic-bezier(0.33, 1, 0.68, 1);
}
.flag-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px -8px currentColor;
}

.flag-R1 { border-left: 3px solid #38BDF8; }
.flag-R2 { border-left: 3px solid #A78BFA; }
.flag-R3 { border-left: 3px solid #FBBF24; }
.flag-R4 { border-left: 3px solid #F87171; }

/* Scroll Progress Indicator */
.scroll-progress {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--v-primary-base), #22D3EE, #A78BFA);
  z-index: 9999;
  transform-origin: left;
  box-shadow: 0 0 20px var(--v-primary-base);
}

/* Stagger Animation Delays */
.stagger-1 { animation-delay: 60ms; }
.stagger-2 { animation-delay: 100ms; }
.stagger-3 { animation-delay: 140ms; }
.stagger-4 { animation-delay: 180ms; }
.stagger-5 { animation-delay: 220ms; }
.stagger-6 { animation-delay: 260ms; }
.stagger-7 { animation-delay: 300ms; }
.stagger-8 { animation-delay: 340ms; }

.stagger-item {
  opacity: 0;
  animation: fade-in-up 0.5s cubic-bezier(0.33, 1, 0.68, 1) forwards;
}

/* In-view state for scroll animations */
.kpi-card.in-view,
.chart-card.in-view,
.legend-card.in-view {
  animation: fade-in-up 0.6s cubic-bezier(0.33, 1, 0.68, 1) forwards;
}

/* 3D Tilt Effect */
.kpi-card,
.chart-card {
  transform-style: preserve-3d;
  transition: transform 0.1s cubic-bezier(0.33, 1, 0.68, 1);
}

/* Evidence Panel Transitions */
.evidence-panel-enter-active,
.evidence-panel-leave-active {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.evidence-panel-enter-from,
.evidence-panel-leave-to {
  opacity: 0;
  transform: translateX(40px) scale(0.96);
}

.evidence-panel-enter-to,
.evidence-panel-leave-from {
  opacity: 1;
  transform: translateX(0) scale(1);
}

/* Reduced Motion */
@media (prefers-reduced-motion: reduce) {
  .timeline-page *,
  .timeline-page *::before,
  .timeline-page *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .kpi-card,
  .chart-card {
    transform: none !important;
  }
}

/* Focus Styles */
:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--v-primary-base) 40%, transparent);
  border-radius: 8px;
}

/* Custom Scrollbar for Evidence Sheet */
.evidence-sheet::-webkit-scrollbar { width: 6px; }
.evidence-sheet::-webkit-scrollbar-track { background: transparent; }
.evidence-sheet::-webkit-scrollbar-thumb {
  background: var(--v-border-color);
  border-radius: 3px;
  border: 2px solid transparent;
  background-clip: content-box;
}
.evidence-sheet::-webkit-scrollbar-thumb:hover { background: var(--v-text-disabled); }

/* Selection */
::selection {
  background: color-mix(in srgb, var(--v-primary-base) 25%, transparent);
}
</style>