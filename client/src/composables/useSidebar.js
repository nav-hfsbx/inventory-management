import { ref } from 'vue'

// Shared sidebar state (singleton pattern, mirrors useFilters.js)
const collapsed = ref(localStorage.getItem('app-sidebar-collapsed') === 'true')
const mobileOpen = ref(false)

// Nav items hold i18n KEYS, never resolved labels - resolve with t(item.key)
// inside the template's v-for so locale switches stay reactive.
const navItems = [
  { path: '/',            key: 'nav.overview',       group: 'operations' },
  { path: '/inventory',   key: 'nav.inventory',      group: 'operations' },
  { path: '/orders',      key: 'nav.orders',         group: 'operations' },
  { path: '/restocking',  key: 'nav.restocking',     group: 'operations' },
  { path: '/spending',    key: 'nav.finance',        group: 'analytics'  },
  { path: '/demand',      key: 'nav.demandForecast', group: 'analytics'  },
  { path: '/reports',     key: 'nav.reports',        group: 'analytics'  }
]

export function useSidebar() {
  const toggleCollapsed = () => {
    collapsed.value = !collapsed.value
    localStorage.setItem('app-sidebar-collapsed', String(collapsed.value))
  }

  const openMobile = () => {
    mobileOpen.value = true
  }

  const closeMobile = () => {
    mobileOpen.value = false
  }

  return {
    collapsed,
    mobileOpen,
    navItems,
    toggleCollapsed,
    openMobile,
    closeMobile
  }
}
