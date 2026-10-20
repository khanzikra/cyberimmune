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
      :item="{ title: 'Timeline', icon: 'ri-time-line', to: '/timeline' }"
    />
    <VerticalNavLink
      :item="{ title: 'Investigation', icon: 'ri-search-line', to: '/investigation' }"
    />
    <VerticalNavLink
      :item="{ title: 'Evaluation Lab', icon: 'ri-bar-chart-line', to: '/evaluation' }"
    />
  </VerticalNavGroup>

  <!-- 👉 Resources -->
  <VerticalNavSectionTitle :item="{ heading: 'Resources' }" />
  <VerticalNavLink
    :item="{ title: 'GitHub Repository', icon: 'ri-github-line', href: 'https://github.com/khanzikra/cyberimmune', target: '_blank' }"
  />
  <VerticalNavLink
    :item="{ title: 'Documentation', icon: 'ri-file-text-line', href: 'https://github.com/khanzikra/cyberimmune/blob/main/README.md', target: '_blank' }"
  />
  <VerticalNavLink
    :item="{ title: 'API Documentation', icon: 'ri-code-s-slash-line', to: '/api/docs', target: '_blank' }"
  />
</template>