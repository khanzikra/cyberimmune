<template>
  <v-container fluid class="pa-4">
    <div class="mb-6 d-flex flex-wrap align-center justify-space-between gap-4">
      <div>
        <h1 class="text-h4 font-weight-medium text-primary">Evaluation Lab</h1>
        <p class="text-body-1 text-secondary mt-1">Compare S1 (Rules), S2 (Plain LLM), S3 (CyberImmune) systems</p>
      </div>
      <div class="d-flex gap-3">
        <v-select v-model="selectedSplit" :items="['dev', 'test']" label="Split" variant="outlined" density="compact" hide-details min-width="150" @change="loadReport" />
        <v-btn variant="tonal" color="primary" @click="loadReport" :disabled="loading"><v-icon start>mdi-refresh</v-icon> Refresh</v-btn>
      </div>
    </div>

    <v-card variant="tonal" class="mb-6" v-if="report">
      <v-card-title class="d-flex justify-space-between align-center">
        <span class="text-h5 font-weight-medium">Overall Metrics ({{ selectedSplit.toUpperCase() }} Split)</span>
        <span class="text-caption text-secondary">Model: {{ report.model }} | Prompt: {{ report.prompt_version }}</span>
      </v-card-title>
      <v-card-text class="pt-0">
        <v-data-table :headers="metricsHeaders" :items="overallMetrics" hide-default-footer class="elevation-0">
          <template #[`item.labelAccuracy`]="{ item }"><v-chip :color="getAccuracyColor(item.labelAccuracy)" size="small">{{ (item.labelAccuracy * 100).toFixed(1) }}%</v-chip></template>
          <template #[`item.evidenceRecall`]="{ item }"><v-chip :color="getRecallColor(item.evidenceRecall)" size="small">{{ (item.evidenceRecall * 100).toFixed(1) }}%</v-chip></template>
          <template #[`item.retrievalRecall`]="{ item }"><v-chip :color="getRecallColor(item.retrievalRecall)" size="small">{{ (item.retrievalRecall * 100).toFixed(1) }}%</v-chip></template>
          <template #[`item.fp`]="{ item }"><v-chip :color="item.fp > 0 ? 'error' : 'success'" size="small">{{ item.fp }}</v-chip></template>
          <template #[`item.fn`]="{ item }"><v-chip :color="item.fn > 0 ? 'error' : 'success'" size="small">{{ item.fn }}</v-chip></template>
          <template #[`item.overHedgingRate`]="{ item }"><v-chip :color="item.overHedgingRate > 0 ? 'warning' : 'success'" size="small">{{ (item.overHedgingRate * 100).toFixed(1) }}%</v-chip></template>
          <template #[`item.insufficientRecall`]="{ item }"><v-chip :color="item.insufficientRecall > 0 ? 'success' : 'secondary'" size="small">{{ (item.insufficientRecall * 100).toFixed(1) }}%</v-chip></template>
          <template #[`item.injectionResisted`]="{ item }"><v-chip :color="item.injectionResisted === 1 ? 'success' : 'error'" size="small">{{ (item.injectionResisted * 100).toFixed(0) }}%</v-chip></template>
          <template #[`item.twinDiscrimination`]="{ item }"><v-chip :color="getTwinColor(item.twinDiscrimination)" size="small">{{ (item.twinDiscrimination * 100).toFixed(1) }}%</v-chip></template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <v-card variant="tonal" class="mb-6" v-if="report.twin_discrimination">
      <v-card-title class="text-h5 font-weight-medium">Twin Discrimination</v-card-title>
      <v-card-text class="pt-0">
        <v-data-table :items="twinMetrics" hide-default-footer class="elevation-0">
          <template #[`item.system`]="{ item }"><span class="font-weight-medium">{{ item.system.toUpperCase() }}</span></template>
          <template #[`item.pairs_correct`]="{ item }">{{ item.pairs_correct }} / {{ item.pairs_evaluated }}</template>
          <template #[`item.twin_discrimination`]="{ item }"><v-chip :color="getTwinColor(item.twin_discrimination)" size="small">{{ (item.twin_discrimination * 100).toFixed(1) }}%</v-chip></template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <v-card variant="tonal" class="mb-6" v-if="report.category_metrics">
      <v-card-title class="text-h5 font-weight-medium">Per-Category Metrics</v-card-title>
      <v-card-text class="pt-0">
        <v-tabs v-model="selectedSystem">
          <v-tab v-for="sys in ['s1', 's2', 's3']" :key="sys">{{ sys.toUpperCase() }}</v-tab>
        </v-tabs>
        <v-tab-items v-model="selectedSystem">
          <v-tab-item v-for="sys in ['s1', 's2', 's3']" :key="sys">
            <v-data-table :headers="categoryHeaders" :items="categoryMetrics[sys] || []" hide-default-footer class="elevation-0">
              <template #[`item.labelAccuracy`]="{ item }"><v-chip :color="getAccuracyColor(item.labelAccuracy)" size="small">{{ (item.labelAccuracy * 100).toFixed(1) }}%</v-chip></template>
              <template #[`item.evidenceRecall`]="{ item }"><v-chip :color="getRecallColor(item.evidenceRecall)" size="small">{{ (item.evidenceRecall * 100).toFixed(1) }}%</v-chip></template>
              <template #[`item.injectionResisted`]="{ item }"><v-chip :color="item.injectionResisted === 1 ? 'success' : 'error'" size="small">{{ (item.injectionResisted * 100).toFixed(0) }}%</v-chip></template>
            </v-data-table>
          </v-tab-item>
        </v-tab-items>
      </v-card-text>
    </v-card>

    <v-expansion-panels v-model="limitsOpen" class="mb-6">
      <v-expansion-panel>
        <v-expansion-panel-title class="font-weight-medium"><v-icon start>mdi-information-outline</v-icon> Evaluation Limits</v-expansion-panel-title>
        <v-expansion-panel-text>
          <div class="text-body-2 text-secondary">
            <p><strong>Synthetic data only:</strong> Events and context records are generated from templates with seeded randomness. Patterns are author-designed, not drawn from real incidents.</p>
            <p><strong>Template-based scenarios:</strong> 8 categories × 3 variants + 4 hand-written; patterns are author-designed. Real attacks may not fit these categories.</p>
            <p><strong>Small N:</strong> 24 dev + 4 test scenarios; limited statistical significance.</p>
            <p><strong>Author-defined labels:</strong> Ground truth labels assigned by scenario author; different analysts might disagree.</p>
            <p><strong>Model nondeterminism:</strong> Even at temperature=0, LLM outputs vary between runs.</p>
            <p><strong>No real-world claim:</strong> High benchmark scores ≠ real attack detection performance.</p>
            <p><strong>Single model:</strong> Nemotron 3 Ultra via Nebius; results may not generalize.</p>
            <p><strong>S2/S3 not fully evaluated:</strong> Live LLM calls incomplete; framework ready for S2/S3, needs working model.</p>
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <v-card variant="tonal">
      <v-card-title class="text-h5 font-weight-medium">Scenario Detail</v-card-title>
      <v-card-text class="pt-0">
        <v-select v-model="selectedDetailScenario" :items="detailScenarios" item-title="scenario_id" item-value="scenario_id" label="Select Scenario" variant="outlined" density="compact" hide-details class="mb-4" @change="loadDetail" />
        
        <div v-if="detailScenario">
          <div class="mb-4"><strong>Question:</strong> {{ detailScenario.question }}</div>
          <div class="mb-4"><strong>Category:</strong> {{ detailScenario.category }} | <strong>Split:</strong> {{ detailScenario.split }} | <strong>Focus User:</strong> {{ detailScenario.focus_user }}</div>
          <div class="mb-4"><strong>Ground Truth:</strong> <code>{{ detailScenario.ground_truth?.expected_label }}</code> — {{ detailScenario.ground_truth?.notes }}</div>
          
          <v-card variant="tonal" class="mb-4" v-for="sys in ['s1', 's2', 's3']" :key="sys">
            <v-card-title class="d-flex justify-space-between align-center"><span>{{ sys.toUpperCase() }}</span>
              <v-chip :color="getPredictionColor(detailScenario[sys]?.investigation?.conclusion?.label)" size="small">{{ detailScenario[sys]?.investigation?.conclusion?.label || 'N/A' }}</v-chip>
            </v-card-title>
            <v-card-text class="pt-0">
              <div class="d-flex flex-wrap gap-4 mb-3">
                <div class="d-flex align-center gap-2"><v-icon :color="getMetricColor(detailScenario[sys]?.metrics?.labelAccuracy)">mdi-target</v-icon><span>Label Acc: <strong>{{ (detailScenario[sys]?.metrics?.labelAccuracy * 100 || 0).toFixed(1) }}%</strong></span></div>
                <div class="d-flex align-center gap-2"><v-icon :color="getMetricColor(detailScenario[sys]?.metrics?.evidenceRecall)">mdi-database-search</v-icon><span>Evidence Recall: <strong>{{ (detailScenario[sys]?.metrics?.evidenceRecall * 100 || 0).toFixed(1) }}%</strong></span></div>
                <div class="d-flex align-center gap-2"><v-icon :color="getMetricColor(detailScenario[sys]?.metrics?.retrievalRecall)">mdi-download</v-icon><span>Retrieval Recall: <strong>{{ (detailScenario[sys]?.metrics?.retrievalRecall * 100 || 0).toFixed(1) }}%</strong></span></div>
                <div class="d-flex align-center gap-2"><v-icon color="warning">mdi-alert-circle-outline</v-icon><span>FP: <strong>{{ detailScenario[sys]?.metrics?.fp || 0 }}</strong> | FN: <strong>{{ detailScenario[sys]?.metrics?.fn || 0 }}</strong></span></div>
              </div>
            </v-card-text>
          </v-card>
        </div>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useApi } from '@/composables/useApi'

export default {
  name: 'EvaluationLab',
  setup() {
    const { api } = useApi()
    const report = ref(null)
    const loading = ref(false)
    const selectedSplit = ref('dev')
    const selectedSystem = ref('s1')
    const limitsOpen = ref(false)
    const twinOpen = ref(false)
    const selectedDetailScenario = ref('')
    const detailScenario = ref(null)
    const detailScenarios = ref([])

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

    const getAccuracyColor = (val) => { if (val >= 0.8) return 'success'; if (val >= 0.5) return 'warning'; return 'error' }
    const getRecallColor = (val) => { if (val >= 0.8) return 'success'; if (val >= 0.5) return 'warning'; return 'error' }
    const getTwinColor = (val) => { if (val >= 0.8) return 'success'; if (val >= 0.5) return 'warning'; return 'error' }
    const getMetricColor = (val) => { if (val >= 0.8) return 'success'; if (val >= 0.5) return 'warning'; return 'error' }
    const getPredictionColor = (label) => { const colors = { no_concern: 'primary', likely_benign: 'success', unexplained: 'warning', insufficient_evidence: 'info' }; return colors[label] || 'secondary' }

    const loadReport = async () => {
      loading.value = true
      try {
        const res = await api.get('/api/evaluation/report', { params: { split: selectedSplit.value } })
        report.value = res.data
        // Extract detail scenarios
        detailScenarios.value = res.data.results.map(r => r.scenario).filter(Boolean)
        if (detailScenarios.value.length > 0 && !selectedDetailScenario.value) {
          selectedDetailScenario.value = detailScenarios.value[0].scenario_id
        }
      } catch (error) { console.error('Failed to load report:', error) } finally { loading.value = false }
    }

    const loadDetail = async () => {
      if (!selectedDetailScenario.value) { detailScenario.value = null; return }
      const scenario = report.value?.results.find(r => r.scenario.scenario_id === selectedDetailScenario.value)
      detailScenario.value = scenario ? { ...scenario.scenario, ...{ s1: scenario.s1, s2: scenario.s2, s3: scenario.s3 } } : null
    }

    const loadReportAndDetails = async () => {
      await loadReport()
      if (selectedDetailScenario.value) await loadDetail()
    }

    onMounted(() => { loadReportAndDetails() })

    return {
      report,
      loading,
      selectedSplit,
      selectedSystem: ref('s1'),
      limitsOpen: ref(false),
      twinOpen: ref(false),
      selectedDetailScenario,
      detailScenario,
      detailScenarios,
      selectedSplit,
      selectedSystem: ref('s1'),
      getAccuracyColor: (val) => { if (val >= 0.8) return 'success'; if (val >= 0.5) return 'warning'; return 'error' },
      getRecallColor: (val) => { if (val >= 0.8) return 'success'; if (val >= 0.5) return 'warning'; return 'error' },
      getTwinColor: (val) => { if (val >= 0.8) return 'success'; if (val >= 0.5) return 'warning'; return 'error' },
      getMetricColor: (val) => { if (val >= 0.8) return 'success'; if (val >= 0.5) return 'warning'; return 'error' },
      getPredictionColor: (label) => { const colors = { no_concern: 'primary', likely_benign: 'success', unexplained: 'warning', insufficient_evidence: 'info' }; return colors[label] || 'secondary' },
      loadReport: loadReportAndDetails,
      selectedSplit,
      selectedDetailScenario,
      detailScenario,
      detailScenarios,
    }
  }
}
</script>