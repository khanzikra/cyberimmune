<template>
  <v-container fluid class="pa-4">
    <div class="mb-6 d-flex flex-wrap align-center justify-space-between gap-4">
      <div>
        <h1 class="text-h4 font-weight-medium text-primary">Investigation</h1>
        <p class="text-body-1 text-secondary mt-1">Structured investigation with verified claims</p>
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
          @change="loadInvestigation"
        />
        <v-btn variant="tonal" color="primary" @click="refreshInvestigation" :disabled="loading">
          <v-icon start>mdi-refresh</v-icon>
          Refresh
        </v-btn>
      </div>
    </div>

    <v-card variant="tonal" class="mb-6" v-if="investigation">
      <v-card-title class="d-flex justify-space-between align-center">
        <div>
          <h2 class="text-h5 font-weight-medium mb-1">{{ investigation.question }}</h2>
          <div class="d-flex align-center gap-3">
            <v-chip
              :color="getConclusionColor(investigation.conclusion.label)"
              size="large"
              class="white--text"
            >
              {{ formatConclusionLabel(investigation.conclusion.label) }}
            </v-chip>
          </div>
        </div>
      </v-card-title>
      <v-card-text class="pt-0">
        <div class="text-body-2 text-secondary mb-4">{{ investigation.conclusion.rationale }}</div>

        <!-- What the verifier proves panel -->
        <v-expansion-panels v-model="verifierPanelOpen" class="mb-6">
          <v-expansion-panel>
            <v-expansion-panel-title class="font-weight-medium">
              <v-icon start>mdi-information-outline</v-icon>
              What the verifier proves / does not prove
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <div class="mb-4">
                <strong class="text-success">The verifier PROVES (machine-checkable):</strong>
                <ul class="mt-2 pl-4">
                  <li>An event ID exists in the database</li>
                  <li>A field value matches the database (timestamp, device, resource, etc.)</li>
                  <li>Event A happened strictly before Event B</li>
                  <li>A device was/was not seen in the baseline period</li>
                  <li>A context record exists with matching user/type</li>
                </ul>
              </div>
              <div>
                <strong class="text-error">The verifier does NOT prove (interpretive):</strong>
                <ul class="mt-2 pl-4">
                  <li>Whether an anomaly is an attack or benign</li>
                  <li>Whether a hypothesis is correct</li>
                  <li>Whether missing evidence would change the conclusion</li>
                  <li>Any claim of "compromised", "attacked", "breach", or "malicious"</li>
                </ul>
                <p class="mt-2 text-caption text-secondary">
                  <strong>Failed claims are never hidden</strong> — they remain visible with the failure reason.
                </p>
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- Claims -->
        <div class="mb-6" v-if="claims.length > 0">
          <h3 class="text-h6 font-weight-medium mb-4">Claims</h3>
          <v-card variant="tonal" class="mb-3" v-for="claim in claims" :key="claim.claim_id">
            <v-card-text class="pb-0">
              <div class="d-flex flex-wrap align-center justify-space-between mb-3">
                <span class="text-h6 font-weight-medium">{{ claim.claim_id }}: {{ claim.text }}</span>
                <v-chip
                  :color="getClaimStatusColor(claim.verification_status)"
                  size="large"
                  class="white--text"
                >
                  {{ claim.verification_status }}
                </v-chip>
              </div>
              <div class="text-caption text-secondary mb-3">Type: {{ claim.claim_type }}</div>
              <div class="mb-2" v-if="claim.cited_event_ids && claim.cited_event_ids.length > 0">
                <strong>Cited Events:</strong>
                <v-chip v-for="id in claim.cited_event_ids" :key="id" size="small" variant="tonal" class="ms-1 mb-1">{{ id }}</v-chip>
              </div>
              <div class="mb-2" v-if="claim.cited_record_ids && claim.cited_record_ids.length > 0">
                <strong>Cited Records:</strong>
                <v-chip v-for="id in claim.cited_record_ids" :key="id" size="small" variant="tonal" class="ms-1 mb-1">{{ id }}</v-chip>
              </div>
              <div class="mb-2" v-if="claim.structured && Object.keys(claim.structured).length > 0">
                <strong>Structured Fields:</strong>
                <pre class="mt-1 p-2 bg-grey-darken-4 rounded" style="font-size: 0.8rem; max-height: 200px; overflow: auto;">{{ JSON.stringify(claim.structured, null, 2) }}</pre>
              </div>
              <div class="mb-2" v-if="claim.limitations">
                <strong>Limitations:</strong> {{ claim.limitations }}
              </div>
              <div class="mb-2" v-if="claim.verification_reason">
                <strong class="text-error">Failed Reason:</strong> {{ claim.verification_reason }}
              </div>
              <div class="mb-2" v-if="claim.provenance_ok === false">
                <v-icon color="warning" size="small">mdi-alert-circle-outline</v-icon>
                <span class="text-warning ml-1">Provenance warning: Cited ID was never retrieved by tools</span>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- Hypotheses -->
        <div class="mb-6" v-if="investigation.hypotheses && investigation.hypotheses.length > 0">
          <h3 class="text-h6 font-weight-medium mb-4">Hypotheses</h3>
          <v-card variant="tonal" class="mb-3" v-for="hyp in investigation.hypotheses" :key="hyp.hypothesis_id">
            <v-card-text>
              <div class="text-h6 font-weight-medium mb-2">{{ hyp.hypothesis_id }}: {{ hyp.description }}</div>
              <div class="d-flex flex-wrap gap-2 mt-2" v-if="hyp.supporting_claim_ids && hyp.supporting_claim_ids.length > 0">
                <span class="text-caption text-secondary">Supporting:</span>
                <v-chip v-for="id in hyp.supporting_claim_ids" :key="id" size="small" variant="tonal" color="success" class="white--text">{{ id }}</v-chip>
              </div>
              <div class="d-flex flex-wrap gap-2 mt-2" v-if="hyp.contradicting_claim_ids && hyp.contradicting_claim_ids.length > 0">
                <span class="text-caption text-secondary">Contradicting:</span>
                <v-chip v-for="id in hyp.contradicting_claim_ids" :key="id" size="small" variant="tonal" color="error" class="white--text">{{ id }}</v-chip>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- Missing Evidence -->
        <div class="mb-6" v-if="investigation.missing_evidence && investigation.missing_evidence.length > 0">
          <h3 class="text-h6 font-weight-medium mb-4">Missing Evidence</h3>
          <v-list>
            <v-list-item v-for="item in investigation.missing_evidence" :key="item">
              <v-list-item-icon><v-icon color="warning">mdi-help-circle-outline</v-icon></v-list-item-icon>
              <v-list-item-title>{{ item }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </div>

        <!-- Next Steps -->
        <div class="mb-6" v-if="investigation.next_steps && investigation.next_steps.length > 0">
          <h3 class="text-h6 font-weight-medium mb-4">Next Steps (Human Actions Only)</h3>
          <v-list>
            <v-list-item v-for="(step, index) in investigation.next_steps" :key="index">
              <v-list-item-icon><v-icon color="primary">mdi-checkbox-blank-circle-outline</v-icon></v-list-item-icon>
              <v-list-item-title>{{ step }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </div>

        <!-- Tool Calls / Audit Trail -->
        <v-expansion-panels v-model="auditPanelOpen" class="mb-6" v-if="auditSteps && auditSteps.length > 0">
          <v-expansion-panel>
            <v-expansion-panel-title class="font-weight-medium">
              <v-icon start>mdi-cog-outline</v-icon>
              Tool Calls & Audit Trail ({{ auditSteps.length }} steps)
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <div v-for="(step, index) in auditSteps" :key="index" class="pb-3">
                <div v-if="index > 0" class="mb-3 border-top pt-3"></div>
                <div class="d-flex justify-space-between mb-1">
                  <span class="font-weight-medium">{{ formatStepType(step.step) }}</span>
                  <span class="text-caption text-secondary">{{ step.tool || '' }}</span>
                </div>
                <div class="text-caption text-secondary">
                  {{ formatStepDetail(step) }}
                </div>
                <v-divider v-if="index < auditSteps.length - 1" class="my-2" />
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>

    <v-card variant="tonal" v-else>
      <v-card-text class="text-center py-12">
        <v-icon size="x-large" color="secondary">mdi-magnify</v-icon>
        <p class="mt-4 text-secondary">No investigation found for this scenario. Run the investigation to see results.</p>
        <v-btn color="primary" @click="runInvestigation" :disabled="loading">
          <v-icon start>mdi-play-circle</v-icon> Run Investigation
        </v-btn>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useApi } from '@/composables/useApi'

export default {
  name: 'Investigation',
  setup() {
    const { api } = useApi()
    const scenarios = ref([])
    const selectedScenario = ref('')
    const investigation = ref(null)
    const loading = ref(false)
    const verifierPanelOpen = ref([0])
    const auditPanelOpen = ref([])
    const auditSteps = ref([])

    const loadScenarios = async () => {
      try {
        const res = await api.get('/api/scenarios')
        scenarios.value = res.data
        if (scenarios.value.length > 0) selectedScenario.value = scenarios.value[0].scenario_id
      } catch (error) { console.error('Failed to load scenarios:', error) }
    }

    const loadInvestigation = async () => {
      if (!selectedScenario.value) return
      loading.value = true
      try {
        const res = await api.get('/api/scenarios/' + selectedScenario.value + '/result')
        investigation.value = res.data.investigation
        auditSteps.value = res.data.audit_steps || []
      } catch (error) {
        console.error('Failed to load investigation:', error)
        investigation.value = null
        auditSteps.value = []
      } finally {
        loading.value = false
      }
    }

    const formatConclusionLabel = (label) => {
      const labels = {
        no_concern: 'No Concern',
        likely_benign: 'Likely Benign',
        unexplained: 'Needs Human Review',
        insufficient_evidence: 'Cannot Conclude',
      }
      return labels[label] || label
    }

    const getConclusionColor = (label) => {
      const colors = {
        no_concern: 'primary',
        likely_benign: 'success',
        unexplained: 'warning',
        insufficient_evidence: 'info',
      }
      return colors[label] || 'secondary'
    }

    const getClaimStatusColor = (status) => {
      const colors = { VERIFIED: 'success', FAILED: 'error', NOT_CHECKABLE: 'secondary' }
      return colors[status] || 'secondary'
    }

    const formatStepType = (step) => {
      const labels = {
        model_tool_call: 'Model Tool Call',
        tool_result: 'Tool Result',
        model_response: 'Model Response',
        validation_error: 'Validation Error',
        parse_error: 'Parse Error',
        tool_error: 'Tool Error',
        limit: 'Limit Reached',
        error: 'Error',
      }
      return labels[step] || step
    }

    const formatStepDetail = (step) => {
      if (step.args) return `Args: ${JSON.stringify(step.args)}`
      if (step.error) return `Error: ${step.error}`
      if (step.content_preview) return step.content_preview
      if (step.ok !== undefined) return step.ok ? 'OK' : 'Failed'
      return ''
    }

    onMounted(async () => {
      await loadScenarios()
      await loadInvestigation()
    })

    return {
      scenarios,
      selectedScenario,
      investigation,
      loading,
      verifierPanelOpen: ref([0]),
      auditPanelOpen: ref([]),
      auditSteps: ref([]),
      claims,
      formatConclusionLabel,
      getConclusionColor,
      getClaimStatusColor,
      formatStepType,
      formatStepDetail,
      loadInvestigation,
      refreshInvestigation,
    }
  },
}
</script>