<template>
  <div class="app-shell" :class="{ 'is-nav-open': navOpen }">
    <aside id="app-sidebar" class="sidebar" aria-label="Main navigation">
      <div class="sidebar-brand">
        <h1>{{ t('nav.companyName') }}</h1>
        <span class="subtitle">{{ t('nav.subtitle') }}</span>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
          <NavIcon name="overview" class="nav-icon" />
          <span class="nav-label">{{ t('nav.overview') }}</span>
        </router-link>
        <router-link to="/inventory" class="nav-item" :class="{ active: $route.path === '/inventory' }">
          <NavIcon name="inventory" class="nav-icon" />
          <span class="nav-label">{{ t('nav.inventory') }}</span>
        </router-link>
        <router-link to="/orders" class="nav-item" :class="{ active: $route.path === '/orders' }">
          <NavIcon name="orders" class="nav-icon" />
          <span class="nav-label">{{ t('nav.orders') }}</span>
        </router-link>
        <router-link to="/spending" class="nav-item" :class="{ active: $route.path === '/spending' }">
          <NavIcon name="finance" class="nav-icon" />
          <span class="nav-label">{{ t('nav.finance') }}</span>
        </router-link>
        <router-link to="/demand" class="nav-item" :class="{ active: $route.path === '/demand' }">
          <NavIcon name="forecast" class="nav-icon" />
          <span class="nav-label">{{ t('nav.demandForecast') }}</span>
        </router-link>
        <router-link to="/restocking" class="nav-item" :class="{ active: $route.path === '/restocking' }">
          <NavIcon name="restock" class="nav-icon" />
          <span class="nav-label">{{ t('nav.restocking') }}</span>
        </router-link>
        <router-link to="/reports" class="nav-item" :class="{ active: $route.path === '/reports' }">
          <NavIcon name="reports" class="nav-icon" />
          <span class="nav-label">{{ t('nav.reports') }}</span>
        </router-link>
      </nav>
    </aside>

    <div v-if="navOpen" class="sidebar-backdrop" @click="closeNav" />

    <div class="app-main">
      <header class="topbar">
        <button
          ref="navToggle"
          type="button"
          class="nav-toggle"
          aria-controls="app-sidebar"
          :aria-expanded="navOpen ? 'true' : 'false'"
          aria-label="Toggle navigation"
          @click="navOpen = !navOpen"
        >
          <NavIcon name="menu" />
        </button>
        <div class="topbar-actions">
          <LanguageSwitcher />
          <ProfileMenu
            @show-profile-details="showProfileDetails = true"
            @show-tasks="showTasks = true"
          />
        </div>
      </header>

      <!-- Global filters: sticky toolbar directly under the topbar (stickiness lives on FilterBar's root) -->
      <FilterBar />

      <main class="content">
        <div class="content-inner">
          <router-view />
        </div>
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import NavIcon from './components/NavIcon.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher,
    NavIcon
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Responsive drawer: below 1024px the sidebar is off-canvas and toggled from the topbar.
    const route = useRoute()
    const navOpen = ref(false)
    const navToggle = ref(null)
    const closeNav = () => {
      navOpen.value = false
    }
    // Close the drawer after navigating so the new page is visible on phones.
    watch(() => route.fullPath, closeNav)
    // Escape closes the drawer and returns focus to the toggle for keyboard users.
    const onKeydown = (e) => {
      if (e.key === 'Escape' && navOpen.value) {
        closeNav()
        navToggle.value?.focus()
      }
    }
    onMounted(() => document.addEventListener('keydown', onKeydown))
    onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      navOpen,
      navToggle,
      closeNav,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ---------- App shell ---------- */
.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-5) var(--space-3);
  background: var(--sidebar-bg);
  border-right: 1px solid var(--sidebar-border);
  z-index: var(--z-sidebar);
}

.sidebar-brand {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: 0 var(--space-3);
  color: var(--sidebar-brand-text);
}

.sidebar-brand h1 {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  letter-spacing: -0.02em;
  line-height: var(--leading-tight);
}

/* Longest string in the sidebar: allowed to wrap onto two lines rather than widening the sidebar. */
.sidebar-brand .subtitle {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: var(--leading-normal);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-0-5);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 36px;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  color: var(--sidebar-text);
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  text-decoration: none;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.nav-item:hover {
  background: var(--sidebar-item-hover-bg);
  color: var(--sidebar-text-hover);
}

.nav-item.active {
  background: var(--sidebar-item-active-bg);
  color: var(--sidebar-item-active-text);
}

.nav-item:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex: none;
  color: var(--sidebar-icon);
}

.nav-item.active .nav-icon {
  color: var(--sidebar-icon-active);
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: var(--z-topbar);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  height: var(--topbar-height);
  padding: 0 var(--content-padding-x);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-left: auto;
}

.content {
  flex: 1;
  padding: var(--content-padding-y) var(--content-padding-x) var(--space-12);
}

.content-inner {
  max-width: var(--content-max-width);
  margin: 0 auto;
}

.nav-toggle {
  display: none;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.nav-toggle svg {
  width: 20px;
  height: 20px;
}

.nav-toggle:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

@media (max-width: 1023px) {
  :root {
    --content-padding-x: var(--space-4);
  }

  .app-shell {
    grid-template-columns: minmax(0, 1fr);
  }

  .sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    width: var(--sidebar-width);
    transform: translateX(-100%);
    transition: transform var(--transition-base);
    box-shadow: var(--shadow-lg);
  }

  .is-nav-open .sidebar {
    transform: none;
  }

  .sidebar-backdrop {
    position: fixed;
    inset: 0;
    z-index: calc(var(--z-sidebar) - 1);
    background: var(--color-overlay);
  }

  .nav-toggle {
    display: inline-flex;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .nav-item {
    transition: none;
  }
}

/* ---------- Shared page classes (used by views) ---------- */
.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  letter-spacing: -0.01em;
  color: var(--color-text);
  margin-bottom: var(--space-1);
}

.page-header p {
  font-size: var(--text-base);
  color: var(--color-text-muted);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--color-surface);
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-xs);
}

.stat-label {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: var(--text-2xl);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  letter-spacing: -0.01em;
  font-variant-numeric: tabular-nums;
}

.stat-card.warning .stat-value {
  color: var(--warning-600);
}

.stat-card.success .stat-value {
  color: var(--success-600);
}

.stat-card.danger .stat-value {
  color: var(--danger-600);
}

.stat-card.info .stat-value {
  color: var(--info-600);
}

.card {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-xs);
  margin-bottom: var(--space-6);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.card-title {
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  letter-spacing: -0.01em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--color-surface-muted);
}

th {
  text-align: left;
  padding: var(--space-3) var(--space-4);
  font-weight: var(--weight-semibold);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

td {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--color-border);
  color: var(--gray-700);
  font-size: var(--text-base);
  height: 46px;
}

tbody tr {
  transition: background-color var(--transition-fast);
}

tbody tr:hover {
  background: var(--color-bg);
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-0-5) var(--space-2);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  /* keep the app's existing uppercase badge casing */
  text-transform: uppercase;
  letter-spacing: 0.025em;
  white-space: nowrap;
}

.badge.success,
.badge.increasing {
  background: var(--success-50);
  color: var(--success-700);
}

.badge.warning,
.badge.medium {
  background: var(--warning-50);
  color: var(--warning-700);
}

.badge.danger,
.badge.decreasing,
.badge.high {
  background: var(--danger-50);
  color: var(--danger-700);
}

.badge.info,
.badge.low {
  background: var(--info-50);
  color: var(--info-700);
}

/* "stable" is neutral: it was indigo before, which is not a status colour in the token set */
.badge.stable {
  background: var(--color-surface-muted);
  color: var(--color-text-secondary);
}

.loading {
  text-align: center;
  padding: var(--space-12) var(--space-6);
  color: var(--color-text-muted);
  font-size: var(--text-base);
}

.error {
  background: var(--danger-50);
  border: 1px solid var(--danger-500);
  color: var(--danger-700);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  margin: var(--space-4) 0;
  font-size: var(--text-base);
}
</style>
