<template>
  <div class="orders">
    <div class="page-header">
      <h2>{{ t('orders.title') }}</h2>
      <p>{{ t('orders.description') }}</p>
    </div>

    <!-- Submitted restocking orders: own loading/error state, independent of global filters -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('orders.submittedOrders') }} ({{ submittedOrders.length }})</h3>
      </div>
      <div v-if="submittedLoading" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="submittedError" class="error">{{ submittedError }}</div>
      <div v-else-if="submittedOrderRows.length === 0" class="empty-state">
        {{ t('orders.submittedOrdersEmpty') }}
      </div>
      <div v-else class="table-container">
        <table class="orders-table">
          <thead>
            <tr>
              <th class="col-order-number">{{ t('orders.table.orderNumber') }}</th>
              <th class="col-date">{{ t('orders.submittedDate') }}</th>
              <th class="col-items">{{ t('orders.table.items') }}</th>
              <th class="col-value">{{ t('orders.table.totalValue') }}</th>
              <th class="col-lead-time">{{ t('orders.leadTime') }}</th>
              <th class="col-date">{{ t('orders.table.expectedDelivery') }}</th>
              <th class="col-eta">{{ t('orders.eta') }}</th>
              <th class="col-status">{{ t('orders.table.status') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in submittedOrderRows" :key="row.id">
              <td class="col-order-number"><strong>{{ row.orderNumber }}</strong></td>
              <td class="col-date">{{ row.submittedDate }}</td>
              <td class="col-items">
                <details class="items-details">
                  <summary class="items-summary">
                    {{ t('orders.itemsCount', { count: row.items.length }) }}
                  </summary>
                  <div class="items-dropdown">
                    <div v-for="item in row.items" :key="item.sku" class="item-entry">
                      <span class="item-name">{{ translateProductName(item.name) }} &times; {{ item.quantity }}</span>
                    </div>
                  </div>
                </details>
              </td>
              <td class="col-value"><strong>{{ row.totalValue }}</strong></td>
              <td class="col-lead-time">{{ row.leadTime }}</td>
              <td class="col-date">{{ row.expectedDelivery }}</td>
              <td class="col-eta">
                <span v-if="row.eta" :class="['badge', row.eta.class]">{{ row.eta.label }}</span>
                <span v-else>-</span>
              </td>
              <td class="col-status">
                <span :class="['badge', getOrderStatusClass(row.status)]">
                  {{ t(`status.${row.status.toLowerCase()}`) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card success">
          <div class="stat-label">{{ t('status.delivered') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Delivered').length }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('status.shipped') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Shipped').length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('status.processing') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Processing').length }}</div>
        </div>
        <div class="stat-card danger">
          <div class="stat-label">{{ t('status.backordered') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Backordered').length }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('orders.allOrders') }} ({{ orders.length }})</h3>
        </div>
        <div class="table-container">
          <table class="orders-table">
            <thead>
              <tr>
                <th class="col-order-number">{{ t('orders.table.orderNumber') }}</th>
                <th class="col-customer">{{ t('orders.table.customer') }}</th>
                <th class="col-items">{{ t('orders.table.items') }}</th>
                <th class="col-status">{{ t('orders.table.status') }}</th>
                <th class="col-date">{{ t('orders.table.orderDate') }}</th>
                <th class="col-date">{{ t('orders.table.expectedDelivery') }}</th>
                <th class="col-value">{{ t('orders.table.totalValue') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in orders" :key="order.id">
                <td class="col-order-number"><strong>{{ order.order_number }}</strong></td>
                <td class="col-customer">{{ translateCustomerName(order.customer) }}</td>
                <td class="col-items">
                  <details class="items-details">
                    <summary class="items-summary">
                      {{ t('orders.itemsCount', { count: order.items.length }) }}
                    </summary>
                    <div class="items-dropdown">
                      <div v-for="(item, idx) in order.items" :key="idx" class="item-entry">
                        <span class="item-name">{{ translateProductName(item.name) }}</span>
                        <span class="item-meta">{{ t('orders.quantity') }}: {{ item.quantity }} @ {{ currencySymbol }}{{ item.unit_price }}</span>
                      </div>
                    </div>
                  </details>
                </td>
                <td class="col-status">
                  <span :class="['badge', getOrderStatusClass(order.status)]">
                    {{ t(`status.${order.status.toLowerCase()}`) }}
                  </span>
                </td>
                <td class="col-date">{{ formatDate(order.order_date) }}</td>
                <td class="col-date">{{ formatDate(order.expected_delivery) }}</td>
                <td class="col-value"><strong>{{ currencySymbol }}{{ order.total_value.toLocaleString() }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

// How often "today" is re-read so badges roll over at local midnight
const NOW_REFRESH_MS = 60 * 1000

export default {
  name: 'Orders',
  setup() {
    const { t, currentCurrency, currentLocale, translateProductName, translateCustomerName } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })
    const loading = ref(true)
    const error = ref(null)
    const orders = ref([])

    // Use shared filters
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    const loadOrders = async () => {
      try {
        loading.value = true
        const filters = getCurrentFilters()
        const fetchedOrders = await api.getOrders(filters)

        // Sort orders by order_date (earliest first)
        orders.value = fetchedOrders.sort((a, b) => {
          const dateA = new Date(a.order_date)
          const dateB = new Date(b.order_date)
          return dateA - dateB
        })
      } catch (err) {
        error.value = 'Failed to load orders: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Watch for filter changes and reload data
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadOrders()
    })

    const getOrdersByStatus = (status) => {
      return orders.value.filter(order => order.status === status)
    }

    const getOrderStatusClass = (status) => {
      const statusMap = {
        'Delivered': 'success',
        'Shipped': 'info',
        'Processing': 'warning',
        'Backordered': 'danger',
        'Submitted': 'info'
      }
      return statusMap[status] || 'info'
    }

    const formatDate = (dateString) => {
      const { currentLocale } = useI18n()
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return new Date(dateString).toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    // --- Submitted restocking orders ---
    // Restocking orders are purchase orders we placed with suppliers, not customer
    // orders, so the global filters (period, warehouse, category, status) do not
    // apply to them and the API endpoint accepts none. They get their own loader,
    // called once on mount and deliberately NOT from the filters watcher above,
    // so changing filters neither refetches nor hides this section.
    const submittedOrders = ref([])
    const submittedLoading = ref(true)
    const submittedError = ref(null)
    // Reference time for the days-remaining badge. Refreshed on an interval
    // (see onMounted) so a tab left open past midnight does not show stale badges.
    const now = ref(Date.now())
    let nowTimer = null

    const loadSubmittedOrders = async () => {
      try {
        submittedLoading.value = true
        submittedError.value = null
        const fetched = await api.getRestockingOrders()
        submittedOrders.value = Array.isArray(fetched) ? fetched : []
        now.value = Date.now()
      } catch (err) {
        submittedError.value = t('orders.submittedOrdersError')
        console.error('Failed to load submitted orders:', err)
      } finally {
        submittedLoading.value = false
      }
    }

    // Returns a valid Date or null
    const parseDate = (value) => {
      if (!value) return null
      const date = new Date(value)
      return isNaN(date.getTime()) ? null : date
    }

    const dateLocale = computed(() => (currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'))

    const formatValidDate = (date) => {
      if (!date) return '-'
      return date.toLocaleDateString(dateLocale.value, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    // Days from today to the expected date, by local calendar date, not elapsed
    // hours: both sides are taken at local midnight, so an order due at 14:00
    // shows "Due today" all day on that date, matching the Expected Delivery column.
    // Date.UTC on the local Y/M/D yields an exact day count even across DST changes.
    const calendarDaysBetween = (from, to) => {
      const fromDay = Date.UTC(from.getFullYear(), from.getMonth(), from.getDate())
      const toDay = Date.UTC(to.getFullYear(), to.getMonth(), to.getDate())
      return Math.round((toDay - fromDay) / (24 * 60 * 60 * 1000))
    }

    // < 0 overdue, 0 due today, > 0 days left. `expected` is already validated
    // by parseDate (null for missing/invalid dates).
    const getEta = (expected) => {
      if (!expected) return null
      const days = calendarDaysBetween(new Date(now.value), expected)
      if (days < 0) return { class: 'danger', label: t('orders.etaOverdue') }
      if (days === 0) return { class: 'warning', label: t('orders.etaToday') }
      if (days === 1) return { class: 'info', label: t('orders.etaRemainingOne') }
      return { class: 'info', label: t('orders.etaRemaining', { days }) }
    }

    const formatLeadTime = (days) => {
      return Number(days) === 1
        ? t('orders.leadTimeDayOne')
        : t('orders.leadTimeDays', { days })
    }

    // Display-ready rows; recomputes on data, locale, or currency change
    const submittedOrderRows = computed(() => {
      return submittedOrders.value.map(order => {
        const expected = parseDate(order.expected_delivery)
        return {
          id: order.id,
          orderNumber: order.order_number,
          status: order.status || 'Submitted',
          items: Array.isArray(order.items) ? order.items : [],
          submittedDate: formatValidDate(parseDate(order.created_date)),
          expectedDelivery: formatValidDate(expected),
          // Keep cents so this matches the Restocking page total
          totalValue: formatCurrencyWithDecimals(Number(order.total_value) || 0, currentCurrency.value, 2),
          leadTime: formatLeadTime(order.lead_time_days),
          eta: getEta(expected)
        }
      })
    })

    onMounted(() => {
      loadOrders()
      loadSubmittedOrders()
      nowTimer = setInterval(() => {
        now.value = Date.now()
      }, NOW_REFRESH_MS)
    })

    onUnmounted(() => {
      if (nowTimer) clearInterval(nowTimer)
      nowTimer = null
    })

    return {
      t,
      loading,
      error,
      orders,
      submittedOrders,
      submittedLoading,
      submittedError,
      submittedOrderRows,
      getOrdersByStatus,
      getOrderStatusClass,
      formatDate,
      currencySymbol,
      translateProductName,
      translateCustomerName
    }
  }
}
</script>

<style scoped>
/* Fixed table layout to prevent column shifting */
.orders-table {
  table-layout: fixed;
  width: 100%;
}

/* Column widths */
/* 150px + nowrap: with the sidebar layout's cell padding, 130px wrapped
   "ORD-2025-0004" onto two lines and doubled every row's height. */
.col-order-number {
  width: 150px;
  white-space: nowrap;
}

.col-customer {
  width: 180px;
}

.col-items {
  width: 200px;
}

.col-status {
  width: 130px;
}

.col-date {
  width: 140px;
}

.col-value {
  width: 120px;
}

.col-lead-time {
  width: 110px;
}

.col-eta {
  width: 140px;
}

/* Submitted orders empty state */
.empty-state {
  text-align: center;
  padding: 2rem 1rem;
  color: #64748b;
  font-size: 0.875rem;
}

/* Items details styling */
.items-details {
  position: relative;
}

.items-summary {
  cursor: pointer;
  color: var(--color-primary);
  font-weight: var(--weight-medium);
  list-style: none;
  user-select: none;
  display: inline-block;
}

.items-summary::-webkit-details-marker {
  display: none;
}

.items-summary::before {
  content: '\25B6';
  display: inline-block;
  margin-right: var(--space-1);
  font-size: var(--text-xs);
  transition: transform var(--transition-base);
}

.items-details[open] .items-summary::before {
  transform: rotate(90deg);
}

.items-summary:hover {
  color: var(--color-primary-hover);
  text-decoration: underline;
}

.items-summary:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
  border-radius: var(--radius-sm);
}

/* Dropdown container. Known pre-existing risk: it is absolutely positioned
   inside .table-container (overflow-x: auto), so it can be clipped at the
   container edge. Restyled only; structure intentionally unchanged. */
.items-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: var(--space-2);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--space-1);
  z-index: var(--z-dropdown);
  min-width: 300px;
  max-width: 400px;
}

.item-entry {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.item-entry:last-child {
  border-bottom: none;
}

.item-name {
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  color: var(--color-text);
}

.item-meta {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
</style>
