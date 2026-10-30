<script setup>
import VerticalNavSectionTitle from '@/@layouts/components/VerticalNavSectionTitle.vue'
import VerticalNavGroup from '@layouts/components/VerticalNavGroup.vue'
import VerticalNavLink from '@layouts/components/VerticalNavLink.vue'
</script>

<template>
  <!-- 👉 CyberImmune -->
  <VerticalNavGroup
    :item="{ title: 'CyberImmune', icon: 'ri-shield-line', badgeContent: 'v1', badgeClass: 'bg-primary' }"
  >
    <VerticalNavLink
      :item="{ title: 'Overview', icon: 'ri-dashboard-line', to: '/overview' }"
    />
    <VerticalNavLink
      :item="{ title: 'Sample Logs', icon: 'ri-file-list-3-line', to: '/sample-logs' }"
    />
    <VerticalNavLink
      :item="{ title: 'Timeline', icon: 'ri-time-line', to: '/timeline' }"
    />
    <VerticalNavLink
      :item="{ title: 'Investigation', icon: 'ri-search-line', to: '/investigation' }"
    />
    <VerticalNavLink
      :item="{ title: 'Evaluation Lab', icon: 'ri-bar-chart-line', to: '/evaluation' }"
    />
  </VerticalNavGroup>
</template>