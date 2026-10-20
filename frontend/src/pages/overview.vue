<template>
  <v-container fluid class="pa-4">
    <!-- Header with subtle entrance -->
    <div class="mb-6 animate-fade-in-up stagger-1">
      <div class="d-flex flex-wrap align-center justify-space-between gap-4 mb-2">
        <div>
          <h1 class="text-h4 font-weight-medium text-primary mb-1">CyberImmune Overview</h1>
          <p class="text-body-1 text-secondary">AI Security Investigator with Deterministic Verification</p>
        </div>
        <v-chip variant="tonal" color="primary" class="text-caption font-weight-medium" size="small">
          <v-icon start size="small">mdi-shield-check</v-icon>
          Demo Mode
        </v-chip>
      </div>
    </div>

    <!-- Stats Cards with staggered entrance -->
    <v-row dense class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <v-card variant="tonal" class="pa-4 card-entrance hover-lift">
          <div class="d-flex justify-space-between align-start">
            <div>
              <div class="text-caption text-secondary mb-1">Total Scenarios</div>
              <div class="text-h3 font-weight-bold text-primary counter-up">{{ stats.totalScenarios }}</div>
            </div>
            <v-icon size="x-large" class="text-primary">mdi-database-outline</v-icon>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card variant="tonal" class="pa-4 card-entrance hover-lift" style="animation-delay: 80ms;">
          <div class="d-flex justify-space-between align-start">
            <div>
              <div class="text-caption text-secondary mb-1">Dev Split</div>
              <div class="text-h3 font-weight-bold text-info counter-up">{{ stats.devScenarios }}</div>
            </div>
            <v-icon size="x-large" class="text-info">mdi-source-branch</v-icon>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card variant="tonal" class="pa-4 card-entrance hover-lift" style="animation-delay: 120ms;">
          <div class="d-flex justify-space-between align-start">
            <div>
              <div class="text-caption text-secondary mb-1">Test Split</div>
              <div class="text-h3 font-weight-bold text-warning counter-up">{{ stats.testScenarios }}</div>
            </div>
            <v-icon size="x-large" class="text-warning">mdi-shield-check-outline</v-icon>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card variant="tonal" class="pa-4 card-entrance hover-lift" style="animation-delay: 160ms;">
          <div class="d-flex justify-space-between align-start">
            <div>
              <div class="text-caption text-secondary mb-1">Categories</div>
              <div class="text-h3 font-weight-bold text-success counter-up">{{ stats.categories }}</div>
            </div>
            <v-icon size="x-large" class="text-success">mdi-tag-multiple-outline</v-icon>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- System Metrics Table with entrance animations -->
    <v-card variant="tonal" class="mb-6 animate-fade-in-up stagger-2">
      <v-card-title class="d-flex justify-space-between align-center">
        <span class="text-h5 font-weight-medium">System Performance (Dev Split)</span>
        <v-chip variant="tonal" size="small" color="secondary">
          <v-icon start size="x-small">mdi-chart-line</v-icon>
          S1 Rules Only
        </v-chip>
      </v-card-title>
      <v-card-text class="pt-2">
        <v-data-table
          :headers="metricsHeaders"
          :items="systemMetrics"
          hide-default-footer
          class="elevation-0"
          :items-per-page="10"
        >
          <template #[`item.system`]="{ item }">
            <div class="d-flex align-center gap-2">
              <v-icon :color="getSystemIconColor(item.system)" size="small">mdi-cpu-64-bit</v-icon>
              <span class="font-weight-medium text-capitalize">{{ item.system }}</span>
            </div>
          </template>
          <template #[`item.labelAccuracy`]="{ item }">
            <v-chip :color="getAccuracyColor(item.labelAccuracy)" size="x-small" variant="tonal">
              {{ (item.labelAccuracy * 100).toFixed(1) }}%
            </v-chip>
          </template>
          <template #[`item.evidenceRecall`]="{ item }">
            <v-chip :color="getRecallColor(item.evidenceRecall)" size="x-small" variant="tonal">
              {{ (item.evidenceRecall * 100).toFixed(1) }}%
            </v-chip>
          </template>
          <template #[`item.retrievalRecall`]="{ item }">
            <v-chip :color="getRecallColor(item.retrievalRecall)" size="x-small" variant="tonal">
              {{ (item.retrievalRecall * 100).toFixed(1) }}%
            </v-chip>
          </template>
          <template #[`item.fp`]="{ item }">
            <v-chip :color="item.fp > 0 ? 'error' : 'success'" size="x-small" variant="tonal">
              {{ item.fp }}
            </v-chip>
          </template>
          <template #[`item.fn`]="{ item }">
            <v-chip :color="item.fn > 0 ? 'error' : 'success'" size="x-small" variant="tonal">
              {{ item.fn }}
            </v-chip>
          </template>
          <template #[`item.overHedgingRate`]="{ item }">
            <v-chip :color="item.overHedgingRate > 0 ? 'warning' : 'success'" size="x-small" variant="tonal">
              {{ (item.overHedgingRate * 100).toFixed(1) }}%
            </v-chip>
          </template>
          <template #[`item.insufficientRecall`]="{ item }">
            <v-chip :color="item.insufficientRecall > 0 ? 'success' : 'secondary'" size="x-small" variant="tonal">
              {{ (item.insufficientRecall * 100).toFixed(1) }}%
            </v-chip>
          </template>
          <template #[`item.injectionResisted`]="{ item }">
            <v-chip :color="item.injectionResisted === 1 ? 'success' : 'error'" size="x-small" variant="tonal">
              <v-icon start size="x-small">mdi-shield-alert</v-icon>
              {{ (item.injectionResisted * 100).toFixed(0) }}%
            </v-chip>
          </template>
          <template #[`item.twinDiscrimination`]="{ item }">
            <v-chip :color="getTwinColor(item.twinDiscrimination)" size="x-small" variant="tonal">
              {{ (item.twinDiscrimination * 100).toFixed(1) }}%
            </v-chip>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Twin Discrimination Card -->
    <v-card variant="tonal" class="mb-6 animate-fade-in-up" v-if="report?.twin_discrimination" style="animation-delay: 200ms;">
      <v-card-title class="d-flex justify-space-between align-center">
        <span class="text-h5 font-weight-medium">Twin Discrimination</span>
        <v-tooltip location="top">
          <template v-slot:activator="{ props }">
            <v-btn icon variant="tonal" size="small" v-bind="props">
              <v-icon>mdi-help-circle-outline</v-icon>
            </v-btn>
          </template>
          <span>Same anomaly, with vs without explaining context</span>
        </v-tooltip>
      </v-card-title>
      <v-card-text class="pt-0">
        <v-data-table :items="twinMetrics" hide-default-footer class="elevation-0">
          <template #[`item.system`]="{ item }">
            <span class="font-weight-medium">{{ item.system.toUpperCase() }}</span>
          </template>
          <template #[`item.pairs_correct`]="{ item }">
            <span class="font-weight-medium">{{ item.pairs_correct }} / {{ item.pairs_evaluated }}</span>
          </template>
          <template #[`item.twin_discrimination`]="{ item }">
            <v-chip :color="getTwinColor(item.twin_discrimination)" size="small" variant="tonal">
              {{ (item.twin_discrimination * 100).toFixed(1) }}%
            </v-chip>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Category Breakdown -->
    <v-card variant="tonal" class="mb-6 animate-fade-in-up" style="animation-delay: 240ms;">
      <v-card-title class="text-h5 font-weight-medium">Category Breakdown (S1 Rules Only)</v-card-title>
      <v-card-text class="pt-2">
        <v-tabs v-model="selectedSystem" class="mb-4" background-color="transparent" indicator-color="primary">
          <v-tab v-for="sys in ['s1', 's2', 's3']" :key="sys">{{ sys.toUpperCase() }}</v-tab>
        </v-tabs>
        <v-tab-items v-model="selectedSystem">
          <v-tab-item v-for="sys in ['s1', 's2', 's3']" :key="sys">
            <v-data-table
              :headers="categoryHeaders"
              :items="categoryMetrics[sys] || []"
              hide-default-footer
              class="elevation-0"
            >
              <template #[`item.labelAccuracy`]="{ item }">
                <v-chip :color="getAccuracyColor(item.labelAccuracy)" size="x-small" variant="tonal">
                  {{ (item.labelAccuracy * 100).toFixed(1) }}%
                </v-chip>
              </template>
              <template #[`item.evidenceRecall`]="{ item }">
                <v-chip :color="getRecallColor(item.evidenceRecall)" size="x-small" variant="tonal">
                  {{ (item.evidenceRecall * 100).toFixed(1) }}%
                </v-chip>
              </template>
              <template #[`item.injectionResisted`]="{ item }">
                <v-chip :color="item.injectionResisted === 1 ? 'success' : 'error'" size="x-small" variant="tonal">
                  {{ (item.injectionResisted * 100).toFixed(0) }}%
                </v-chip>
              </template>
            </v-data-table>
          </v-tab-item>
        </v-tab-items>
      </v-card-text>
    </v-card>

    <!-- Limits Notice - Humanized -->
    <v-expansion-panels v-model="limitsOpen" class="mb-6 animate-fade-in-up" style="animation-delay: 280ms;">
      <v-expansion-panel>
        <v-expansion-panel-title class="font-weight-medium">
          <v-icon start>mdi-information-outline</v-icon>
          <span class="ml-2">Evaluation Limits & Honest Caveats</span>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <div class="text-body-2 text-secondary space-y-3">
            <p><strong>Synthetic data only:</strong> Events and context records are generated from templates with seeded randomness. Patterns are author-designed, not drawn from real incidents.</p>
            <p><strong>Template-based scenarios:</strong> 8 categories × 3 variants + 4 hand-written; patterns are author-designed. Real attacks may not fit these categories.</p>
            <p><strong>Small N:</strong> 24 dev + 4 test scenarios; limited statistical significance.</p>
            <p><strong>Author-defined labels:</strong> Ground truth labels assigned by scenario author; different analysts might disagree.</            <p><strong>Model nondeterminism:</strong> Even at temperature=0, LLM outputs vary between runs.</p>
            <p><strong>No real-world claim:</strong> High benchmark scores ≠ real attack detection performance.</p>
            <p><strong>Single model tested:</strong> Nemotron 3 Ultra via Nebius; results may not generalize.</p>
            <p><strong>S2/S3 not fully evaluated:</strong> Live LLM calls incomplete; framework ready for S2/S3, needs working model.</p>
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Footer note -->
    <v-alert
      type="info"
      variant="tonal"
      class="animate-fade-in-up"
      style="animation-delay: 320ms;"
      icon="mdi-shield-account"
    >
      <strong>Honest AI:</strong> This system makes claims; Python code verifies them. 
      Green = verified, Red = failed check, Grey = interpretation. 
      Failed claims are never hidden. We never say "compromised" or "attack confirmed."
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
    const selectedSystem = ref('s1')
    const selectedSplit = ref('dev')
    const report = ref(null)
    const limitsOpen = ref(false)

    const metricsHeaders = [
      { title: 'System', key: 'system', sortable: false },
      { title: 'Label Accuracy', key: 'labelAccuracy', sortable: false },
      { title: 'Evidence Recall', key: 'evidenceRecall', sortable: false },
      { title: 'Retrieval Recall', key: 'retrievalRecall', sortable: false },
      { title: 'FP', key: 'fp', sortable: false },
      { title: 'FN', key: 'fn', sortable: false },
      { title: 'Over-Hedging', key: 'overHedgingRate', sortable: false },
      { title: 'Insuff. Recall', key: 'insufficientRecall', sortable: false },
      { title: 'Injection Resist', key: 'injectionResisted', sortable: false },
      { title: 'Twin Disc.', key: 'twinDiscrimination', sortable: false },
    ]

    const categoryHeaders = [
      { title: 'Category', key: 'category', sortable: false },
      { title: 'Count', key: 'count', sortable: false },
      { title: 'Label Acc', key: 'labelAccuracy', sortable: false },
      { title: 'Evid. Recall', key: 'evidenceRecall', sortable: false },
      { title: 'Inject Resist', key: 'injectionResisted', sortable: false },
    ]

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

    const getMetricColor = (val) => {
      if (val >= 0.8) return 'success'
      if (val >= 0.5) return 'warning'
      return 'error'
    }

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
        const reportRes = await api.get('/api/evaluation/report', { params: { split: 'dev' } })
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
          injectionResisted: data.avg_metrics?.injection_resisted || 0,
        }))
      } catch (error) {
        console.error('Failed to fetch overview data:', error)
      } finally {
        loading.value = false
      }
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
      selectedSystem: ref('s1'),
      selectedSplit: ref('dev'),
      limitsOpen: ref(false),
      getAccuracyColor,
      getRecallColor,
      getTwinColor,
      getMetricColor,
      fetchData,
    }
  },
}
</script>