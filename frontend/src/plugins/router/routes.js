export const routes = [
  { path: '/', redirect: '/overview' },
  {
    path: '/',
    component: () => import('@/layouts/default.vue'),
    children: [
      {
        path: 'overview',
        component: () => import('@/pages/overview.vue'),
        meta: { title: 'Overview' },
      },
      {
        path: 'timeline',
        component: () => import('@/pages/timeline.vue'),
        meta: { title: 'Timeline' },
      },
      {
        path: 'investigation',
        component: () => import('@/pages/investigation.vue'),
        meta: { title: 'Investigation' },
      },
      {
        path: 'evaluation',
        component: () => import('@/pages/evaluation.vue'),
        meta: { title: 'Evaluation Lab' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    component: () => import('@/pages/[...error].vue'),
  },
]