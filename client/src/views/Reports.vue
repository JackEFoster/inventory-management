<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t('reports.title') }}</h2>
      <p>{{ t('reports.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ t('reports.loadError', { message: error }) }}</div>
    <div v-else-if="monthlyData.length === 0" class="card">
      <div class="no-data">{{ t('reports.noData') }}</div>
    </div>
    <div v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.quarterlyPerformance') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.table.quarter') }}</th>
                <th>{{ t('reports.table.totalOrders') }}</th>
                <th>{{ t('reports.table.totalRevenue') }}</th>
                <th>{{ t('reports.table.avgOrderValue') }}</th>
                <th>{{ t('reports.table.fulfillmentRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td>
                  <strong>{{ q.quarter }}</strong>
                </td>
                <td>{{ q.total_orders }}</td>
                <td>{{ money(q.total_revenue) }}</td>
                <td>{{ money(q.avg_order_value) }}</td>
                <td>
                  <span :class="['badge', fulfillmentClass(q.fulfillment_rate)]">{{ q.fulfillment_rate }}%</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Monthly Trends Chart -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.monthlyRevenueTrend') }}</h3>
        </div>
        <div class="chart-container">
          <div class="bar-chart">
            <div v-for="row in monthRows" :key="row.month" class="bar-wrapper">
              <div class="bar-container">
                <div
                  class="bar"
                  :style="{ height: row.barHeight + 'px' }"
                  :title="`${row.label}: ${money(row.revenue)}`"
                  :aria-label="`${row.label}: ${money(row.revenue)}`"
                  role="img"
                ></div>
              </div>
              <div class="bar-label">{{ row.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.monthOverMonth') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.table.month') }}</th>
                <th>{{ t('reports.table.orders') }}</th>
                <th>{{ t('reports.table.revenue') }}</th>
                <th>{{ t('reports.table.change') }}</th>
                <th>{{ t('reports.table.growthRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in monthRows" :key="row.month">
                <td>
                  <strong>{{ row.label }}</strong>
                </td>
                <td>{{ row.order_count }}</td>
                <td>{{ money(row.revenue) }}</td>
                <td>
                  <span :class="row.changeClass">{{ row.changeText }}</span>
                </td>
                <td>
                  <span :class="row.changeClass">{{ row.growthText }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats (scoped to the active filters) -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalRevenue') }}</div>
          <div class="stat-value">{{ money(summary.totalRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.avgMonthlyRevenue') }}</div>
          <div class="stat-value">{{ money(summary.avgMonthlyRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalOrders') }}</div>
          <div class="stat-value">{{ summary.totalOrders.toLocaleString() }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.bestQuarter') }}</div>
          <div class="stat-value">{{ summary.bestQuarter || t('reports.notApplicable') }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const MAX_BAR_HEIGHT = 200
const MONTH_KEYS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

export default {
  name: 'Reports',
  setup() {
    const { t, currentCurrency } = useI18n()
    const { selectedPeriod, selectedLocation, selectedCategory, selectedStatus, getCurrentFilters } = useFilters()

    const loading = ref(true)
    const error = ref(null)
    const quarterlyData = ref([])
    const monthlyData = ref([])

    // Currency-aware (USD/JPY) and rounds rather than truncating
    const money = (amount) => formatCurrencyWithDecimals(Number(amount) || 0, currentCurrency.value, 2)

    // 'YYYY-MM' -> localized 'Jan 2025' / '1月 2025'; unparseable input is shown as-is
    const formatMonth = (monthStr) => {
      const [year, month] = String(monthStr).split('-')
      const index = Number(month) - 1
      if (!year || !(index >= 0 && index < 12)) return monthStr
      return `${t(`months.${MONTH_KEYS[index]}`)} ${year}`
    }

    const fulfillmentClass = (rate) => {
      if (rate >= 90) return 'success'
      if (rate >= 75) return 'warning'
      return 'danger'
    }

    // All per-month display values are derived once here instead of being
    // recomputed by template method calls on every render (the old bar-height
    // helper rescanned every month for every bar: O(n^2) per render).
    const monthRows = computed(() => {
      const maxRevenue = Math.max(0, ...monthlyData.value.map((m) => m.revenue))
      return monthlyData.value.map((m, i) => {
        const prev = i > 0 ? monthlyData.value[i - 1].revenue : null
        const change = prev === null ? null : m.revenue - prev
        let changeText = '-'
        let growthText = '-'
        if (change !== null) {
          const sign = change > 0 ? '+' : change < 0 ? '-' : ''
          changeText = sign + money(Math.abs(change))
          growthText =
            prev === 0 ? t('reports.notApplicable') : `${change > 0 ? '+' : ''}${((change / prev) * 100).toFixed(1)}%`
        }
        return {
          ...m,
          label: formatMonth(m.month),
          barHeight: maxRevenue > 0 ? (m.revenue / maxRevenue) * MAX_BAR_HEIGHT : 0,
          changeText,
          growthText,
          changeClass: change > 0 ? 'positive-change' : change < 0 ? 'negative-change' : ''
        }
      })
    })

    const summary = computed(() => {
      const totalRevenue = monthlyData.value.reduce((sum, m) => sum + m.revenue, 0)
      const totalOrders = monthlyData.value.reduce((sum, m) => sum + m.order_count, 0)
      const best = quarterlyData.value.reduce((a, q) => (!a || q.total_revenue > a.total_revenue ? q : a), null)
      return {
        totalRevenue,
        totalOrders,
        avgMonthlyRevenue: monthlyData.value.length ? totalRevenue / monthlyData.value.length : 0,
        bestQuarter: best ? best.quarter : ''
      }
    })

    const loadData = async () => {
      try {
        loading.value = true
        error.value = null // clear a previous failure so a successful reload shows data
        const filters = getCurrentFilters()
        // Independent requests: fetch in parallel
        const [quarterly, monthly] = await Promise.all([
          api.getQuarterlyReports(filters),
          api.getMonthlyTrends(filters)
        ])
        quarterlyData.value = quarterly
        monthlyData.value = monthly
      } catch (err) {
        error.value = err.message
        console.error('Failed to load reports:', err)
      } finally {
        loading.value = false
      }
    }

    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], loadData)
    onMounted(loadData)

    return {
      t,
      loading,
      error,
      quarterlyData,
      monthlyData,
      monthRows,
      summary,
      money,
      fulfillmentClass
    }
  }
}
</script>

<style scoped>
/* .card, .card-header, .card-title, .stats-grid, .stat-*, .badge, .loading, .error, th/td and
   .table-container come from the shared styles in App.vue; only page-specific rules live here. */
.reports {
  padding: 0;
}

.chart-container {
  padding: var(--space-8) var(--space-4);
  min-height: 300px;
  /* rotated month labels can poke out on phones; scroll inside the card, not the page */
  overflow-x: auto;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 250px;
  gap: var(--space-2);
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

/* flat brand fill (the old gradient is retired); hover steps one shade darker */
.bar {
  width: 100%;
  background: var(--brand-500);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  transition: background-color var(--transition-base);
  cursor: pointer;
}

.bar:hover {
  background: var(--brand-700);
}

.bar-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
  margin-top: var(--space-6);
}

.positive-change {
  color: var(--success-600);
  font-weight: var(--weight-semibold);
}

.negative-change {
  color: var(--danger-600);
  font-weight: var(--weight-semibold);
}

.no-data {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-text-muted);
}
</style>
