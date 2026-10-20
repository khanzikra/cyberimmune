<template>
  <v-container fluid class="pa-4">
    <!-- Header -->
    <div class="mb-6">
      <h1 class="text-h4 font-weight-medium text-primary">CyberImmune Overview</h1>
      <p class="text-body-1 text-secondary mt-1">
        AI Security Investigator with Deterministic Verification
      </p>
    </div>

    <!-- Stats Cards -->
    <v-row dense class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <v-card variant="tonal" class="pa-4">
          <div class="d-flex justify-space-between">
            <div>
              <div class="text-caption text-secondary">Total Scenarios</div>
              <div class="text-h4 font-weight-bold text-primary">{{ stats.totalScenarios }}</div>
            </div>
            <v-icon size="large" class="text-primary">mdi-database</v-icon>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card variant="tonal" class="pa-4">
          <div class="d-flex justify-space-between">
            <div>
              <div class="text-caption text-secondary">Dev Split</div>
              <div class="text-h4 font-weight-bold text-info">{{ stats.devScenarios }}</div>
            </div>
            <v-icon size="large" class="text-info">mdi-dev-to</v-icon>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card variant="tonal" class="pa-4">
          <div class="d-flex justify-space-between">
            <div>
              <div class="text-caption text-secondary">Test Split</div>
              <div class="text-h4 font-weight-bold text-warning">{{ stats.testScenarios }}</div>
            </div>
            <v-icon size="large" class="text-warning">mdi-shield-check</v-icon>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card variant="tonal" class="pa-4">
          <div class="d-flex justify-space-between">
            <div>
              <div class="text-caption text-secondary">Categories</div>
              <div class="text-h4 font-weight-bold text-success">{{ stats.categories }}</div>
            </div>
            <v-icon size="large" class="text-success">mdi-tag-multiple</v-icon>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- System Metrics -->
    <v-card variant="tonal" class="mb-6">
      <v-card-title class="text-h5 font-weight-medium">
        System Performance (Dev Split)
      </v-card-title>
      <v-card-text class="pt-0">
        <v-data-table
          :headers="metricsHeaders"
          :items="systemMetrics"
          hide-default-footer
          class="elevation-0"
        >
          <template #[`item.labelAccuracy`]="{ item }">
            <v-chip :color="getAccuracyColor(item.labelAccuracy)" size="small">
              {{ (item.labelAccuracy * 100).toFixed(1) }}%
            </v-chip>
          </template>
          <template #[`item.evidenceRecall`]="{ item }">
            <v-chip :color="getRecallColor(item.evidenceRecall)" size="small">
              {{ (item.evidenceRecall * 100).toFixed(1) }}%
            </v-chip>
          </template>
          <template #[`item.retrievalRecall`]="{ item }">
            <v-chip :color="getRecallColor(item.retrievalRecall)" size="small">
              {{ (item.retrievalRecall * 100).toFixed(1) }}%
            </v-chip>
          </template>
          <template #[`item.twinDiscrimination`]="{ item }">
            <v-chip :color="getTwinColor(item.twinDiscrimination)" size="small">
              {{ (item.twinDiscrimination * 100).toFixed(1) }}%
            </v-chip>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Category Breakdown -->
    <v-card variant="tonal">
      <v-card-title class="text-h5 font-weight-medium">
        Category Breakdown (S1 Rules Only)
      </v-card-title>
      <v-card-text class="pt-0">
        <v-data-table
          :headers="categoryHeaders"
          :items="categoryMetrics"
          hide-default-footer
          class="elevation-0"
        >
          <template #[`item.labelAccuracy`]="{ item }">
            <v-chip :color="getAccuracyColor(item.labelAccuracy)" size="small">
              {{ (item.labelAccuracy * 100).toFixed(1) }}%
            </v-chip>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Limits Notice -->
    <v-alert
      type="info"
      variant="tonal"
      class="mt-6"
      icon="mdi-information"
    >
      <strong>Evaluation Limits:</strong> This benchmark uses synthetic, template-generated data with small N (24 dev + 4 test scenarios). 
      Author-defined labels. Model nondeterminism applies. 
      <a href="#" class="text-decoration-none text-primary ms-2">View full limits</a>.
      No real-world detection performance is claimed.
    </v-alert>
  </v-container>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useApi } from '@/composables/useApi'

export default {
  name: 'Overview',
  setup() {
    const { api } = useApi()
    const stats = ref({
      totalScenarios: 0,
      devScenarios: 0,
      testScenarios: 0,
      categories: 0,
    })
    const systemMetrics = ref([])
    const categoryMetrics = ref([])
    const loading = ref(false)

    const metricsHeaders = [
      { title: 'System', key: 'system', sortable: false },
      { title: 'Label Accuracy', key: 'labelAccuracy', sortable: false },
      { title: 'Evidence Recall', key: 'evidenceRecall', sortable: false },
      { title: 'Retrieval Recall', key: 'retrievalRecall', sortable: false },
      { title: 'Twin Discrimination', key: 'twinDiscrimination', sortable: false },
    ]

    const categoryHeaders = [
      { title: 'Category', key: 'category', sortable: false },
      { title: 'Count', key: 'count', sortable: false },
      { title: 'Label Accuracy', key: 'labelAccuracy', sortable: false },
      { title: 'Evidence Recall', key: 'evidenceRecall', sortable: false },
    ]

    const fetchData = async () => {
      loading.value = true
      try {
        // Fetch scenarios
        const scenariosRes = await api.get('/api/scenarios')
        const scenarios = scenariosRes.data
        stats.value.totalScenarios = scenarios.length
        stats.value.devScenarios = scenarios.filter(s => s.split === 'dev').length
        stats.value.testScenarios = scenarios.filter(s => s.split === 'test').length
        const categories = new Set(scenarios.map(s => s.category))
        stats.value.categories = categories.size

        // Fetch evaluation report
        const reportRes = await api.get('/api/evaluation/report')
        const report = reportRes.data
        systemMetrics.value = Object.entries(report.overall || {}).map(([system, metrics]) => ({
          system: system.toUpperCase(),
          ...metrics,
        }))
        
        categoryMetrics.value = Object.entries(report.category_metrics?.s1 || {}).map(([category, data]) => ({
          category,
          count: data.count,
          labelAccuracy: data.avg_metrics?.label_accuracy || 0,
          evidenceRecall: data.avg_metrics?.evidence_recall || 0,
        }))
      } catch (error) {
        console.error('Failed to fetch overview data:', error)
      } finally {
        loading.value = false
      }
    }

    const getAccuracyColor = (val) => {
      if (val >= 0.8) return 'success'
      if (val >= 0.5) return 'warning'
      return 'error'
    }

    const getRecallColor = (val) => {
      if (val >= 0.8) return 'success'
      if (val >= 0.5) return 'warning'
      return 'error'
    }

    const getTwinColor = (val) => {
      if (val >= 0.8) return 'success'
      if (val >= 0.5) return 'warning'
      return 'error'
    }

    onMounted(() => {
      fetchData()
    })

    return {
      stats,
      systemMetrics,
      categoryMetrics,
      loading,
      metricsHeaders,
      categoryHeaders,
      getAccuracyColor,
      getRecallColor,
      getTwinColor,
    }
  },
}
</script>