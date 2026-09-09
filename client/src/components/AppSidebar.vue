<template>
  <div
    v-if="mobileOpen"
    class="sidebar-scrim"
    @click="closeMobile"
  ></div>
  <aside id="app-sidebar" class="app-sidebar" :class="{ collapsed: railCollapsed, 'mobile-open': mobileOpen }">
    <div class="sidebar-header">
      <div class="logo" v-if="!railCollapsed">
        <h1>{{ t('nav.companyName') }}</h1>
        <span class="subtitle">{{ t('nav.subtitle') }}</span>
      </div>
      <div class="logo-mark" v-else :title="t('nav.companyName')">CC</div>

      <button
        class="collapse-toggle"
        :class="{ centered: collapsed }"
        type="button"
        :aria-expanded="!collapsed"
        :aria-label="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        @click="toggleCollapsed"
      >
        <svg
          class="chevron-icon"
          :class="{ rotated: collapsed }"
          width="20"
          height="20"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path d="M15.707 15.707a1 1 0 01-1.414 0l-5-5a1 1 0 010-1.414l5-5a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 010 1.414zm-6 0a1 1 0 01-1.414 0l-5-5a1 1 0 010-1.414l5-5a1 1 0 111.414 1.414L5.414 10l4.293 4.293a1 1 0 010 1.414z" />
        </svg>
      </button>
    </div>

    <nav class="sidebar-nav" :aria-label="t('nav.mainNav')">
      <template v-for="(group, groupIndex) in groupedNavItems" :key="group.group">
        <div v-if="railCollapsed" class="group-divider" :class="{ first: groupIndex === 0 }"></div>
        <div v-else class="group-label" :class="{ first: groupIndex === 0 }">{{ t(`nav.${group.group}`) }}</div>

        <router-link
          v-for="item in group.items"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
          :aria-current="$route.path === item.path ? 'page' : undefined"
          :title="railCollapsed ? t(item.key) : undefined"
        >
          <span class="nav-icon" v-html="icons[item.path]"></span>
          <span v-if="!railCollapsed" class="nav-label">{{ t(item.key) }}</span>
        </router-link>
      </template>
    </nav>

    <div class="sidebar-footer">
      <LanguageSwitcher class="footer-language" />
      <ProfileMenu
        class="footer-profile"
        @show-profile-details="emit('show-profile-details')"
        @show-tasks="emit('show-tasks')"
      />
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useSidebar } from '../composables/useSidebar'
import { useI18n } from '../composables/useI18n'
import LanguageSwitcher from './LanguageSwitcher.vue'
import ProfileMenu from './ProfileMenu.vue'

const emit = defineEmits(['show-profile-details', 'show-tasks'])

const { collapsed, mobileOpen, navItems, toggleCollapsed, closeMobile } = useSidebar()
const { t } = useI18n()

// Below the 1024px breakpoint the drawer (mobileOpen) always wins over the
// desktop rail preference (collapsed) - a 64px icon rail plus a slide-in
// drawer would be two competing behaviours. Template v-if/v-else blocks for
// labels are gated on this instead of the raw `collapsed` ref so that
// opening the drawer always shows full labels regardless of the persisted
// desktop collapse state.
const railCollapsed = computed(() => collapsed.value && !mobileOpen.value)

// Group labels are resolved via t(`nav.${group.group}`) directly in the
// template (not here) so they stay reactive to locale changes -- a
// module/setup-scope lookup would freeze on the locale active at mount.
const groupedNavItems = computed(() => {
  const groups = []
  const byGroup = {}
  for (const item of navItems) {
    if (!byGroup[item.group]) {
      byGroup[item.group] = { group: item.group, items: [] }
      groups.push(byGroup[item.group])
    }
    byGroup[item.group].items.push(item)
  }
  return groups
})

// Heroicons v1 solid, 20px, fill=currentColor, keyed by route path.
const icons = {
  '/': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"/></svg>',
  '/inventory': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path d="M4 3a2 2 0 100 4h12a2 2 0 100-4H4z"/><path fill-rule="evenodd" clip-rule="evenodd" d="M3 8h14v7a2 2 0 01-2 2H5a2 2 0 01-2-2V8zm5 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z"/></svg>',
  '/orders': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/><path fill-rule="evenodd" clip-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z"/></svg>',
  '/restocking': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path d="M8 16.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM15 16.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z"/><path d="M3 4a1 1 0 00-1 1v10a1 1 0 001 1h1.05a2.5 2.5 0 014.9 0H10a1 1 0 001-1V5a1 1 0 00-1-1H3zM14 7a1 1 0 00-1 1v6.05A2.5 2.5 0 0115.95 16H17a1 1 0 001-1v-5a1 1 0 00-.293-.707l-2-2A1 1 0 0015 7h-1z"/></svg>',
  '/spending': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z"/><path fill-rule="evenodd" clip-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z"/></svg>',
  '/demand': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path fill-rule="evenodd" clip-rule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z"/></svg>',
  '/reports': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/></svg>'
}
</script>

<style scoped>
.app-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #0f172a;
  border-right: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  z-index: 100;
  height: 100vh;
  transition: width 160ms ease;
  font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.app-sidebar.collapsed {
  width: 64px;
}

/* Scrim sits below the drawer (z-index: 210) but above the desktop rail
   (z-index: 100) and the sticky topbar (z-index: 50). Hidden above the
   1024px breakpoint since the drawer/scrim only ever apply there. */
.sidebar-scrim {
  display: none;
}

@media (max-width: 1024px) {
  /* Overlay drawer: fixed + off-canvas by default, slides in via transform
     when mobileOpen is true. Safe to use transform here (unlike the rest of
     the app shell) because at this breakpoint the sidebar is out of flow. */
  .app-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    width: 240px;
    z-index: 210;
    transform: translateX(-100%);
    transition: transform 200ms ease;
  }

  /* Belt-and-braces: railCollapsed already keeps the .collapsed class off
     the root while the drawer is open, but force the rail width back to
     240px here too in case collapsed is ever applied at this breakpoint. */
  .app-sidebar.collapsed {
    width: 240px;
  }

  .app-sidebar.mobile-open {
    transform: translateX(0);
  }

  .sidebar-scrim {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.5);
    z-index: 200;
  }

  /* Collapse toggle is meaningless for a drawer that is always full-width. */
  .collapse-toggle {
    display: none;
  }

  /* The base rule's min-width (160px/280px) would beat a max-width cap
     here (max-width can't shrink a box below min-width), so open these
     upward inside the 240px panel instead of as a right-side fly-out -
     a right fly-out plus either min-width overflows past the viewport
     edge on any phone narrower than ~520px. */
  .footer-language :deep(.dropdown-menu),
  .footer-profile :deep(.dropdown-menu) {
    left: 0;
    right: auto;
    bottom: 100%;
    top: auto;
    margin-left: 0;
    margin-bottom: 8px;
    min-width: 0;
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-sidebar {
    transition: none;
  }
}

/* Header */
.sidebar-header {
  height: 64px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
  gap: 0.5rem;
}

.app-sidebar.collapsed .sidebar-header {
  height: auto;
  min-height: 64px;
  flex-direction: column;
  justify-content: center;
  padding: 0.5rem 0;
  gap: 0.375rem;
}

.logo {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.logo h1 {
  font-size: 1rem;
  font-weight: 600;
  color: #f8fafc;
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logo .subtitle {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: 400;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logo-mark {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #1e293b;
  color: #22d3ee;
  font-size: 0.75rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.collapse-toggle {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  flex-shrink: 0;
  transition: background 0.15s ease, color 0.15s ease;
}

.collapse-toggle:hover {
  background: rgba(255, 255, 255, 0.04);
  color: #e2e8f0;
}

.collapse-toggle.centered {
  margin: 0 auto;
}

.chevron-icon {
  transition: transform 160ms ease;
}

.chevron-icon.rotated {
  transform: rotate(180deg);
}

@media (prefers-reduced-motion: reduce) {
  .collapse-toggle,
  .chevron-icon {
    transition: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .chevron-icon {
    transition: none;
  }
}

/* Nav */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.group-label {
  font-size: 0.6875rem;
  font-weight: 500;
  color: #7c8da5;
  padding: 0.75rem 0.75rem 0.375rem;
  margin-top: 0.5rem;
}

.group-label.first {
  margin-top: 0;
}

.group-divider {
  height: 1px;
  background: #1e293b;
  margin: 0.5rem 0.25rem;
}

.group-divider.first {
  margin-top: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  height: 40px;
  padding: 0 0.75rem;
  border-radius: 6px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  position: relative;
  transition: background 0.15s ease, color 0.15s ease;
}

.app-sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0;
}

.nav-item:hover {
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.04);
}

.nav-item.active {
  color: #22d3ee;
  background: rgba(34, 211, 238, 0.08);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #22d3ee;
  border-radius: 0 3px 3px 0;
}

@media (prefers-reduced-motion: reduce) {
  .nav-item {
    transition: none;
  }
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-icon :deep(svg) {
  width: 20px;
  height: 20px;
}

.nav-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Footer */
.sidebar-footer {
  flex-shrink: 0;
  border-top: 1px solid #1e293b;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.app-sidebar.collapsed .sidebar-footer {
  align-items: center;
}

/* Reposition the two footer dropdowns as right-side fly-outs so they
   fit inside a 240px (or 64px collapsed) column instead of opening
   downward/rightward, which is how they behaved in the old horizontal
   header. */
.footer-language :deep(.dropdown-menu),
.footer-profile :deep(.dropdown-menu) {
  left: 100%;
  right: auto;
  bottom: 0;
  top: auto;
  margin-left: 8px;
}

/* At 64px collapsed, ProfileMenu's/LanguageSwitcher's trigger buttons
   (avatar/globe + label + chevron) are wider than the rail and cannot
   be edited directly, so shrink them to icon-only here, matching the
   collapsed nav items. */
.app-sidebar.collapsed .footer-profile :deep(.profile-name),
.app-sidebar.collapsed .footer-profile :deep(.chevron),
.app-sidebar.collapsed .footer-language :deep(.language-label),
.app-sidebar.collapsed .footer-language :deep(.chevron) {
  display: none;
}

/* Focus visibility */
.nav-item:focus-visible,
.collapse-toggle:focus-visible,
.footer-language :deep(.language-button):focus-visible,
.footer-profile :deep(.profile-button):focus-visible {
  outline: 2px solid #22d3ee;
  outline-offset: 2px;
}
</style>
