<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="loadError" class="error">{{ t('restocking.errors.load') }}</div>
    <div v-else>
      <div v-if="orderPlaced" class="success-banner" role="status">
        <span>{{ t('restocking.orderPlaced', { orderNumber: orderPlaced.orderNumber, days: orderPlaced.days }) }}</span>
        <router-link to="/orders" class="success-link">{{ t('restocking.viewOrders') }}</router-link>
      </div>

      <div class="card budget-card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budget') }}</h3>
        </div>
        <div class="budget-control">
          <input
            type="range"
            class="budget-slider"
            min="0"
            :max="maxBudget"
            step="500"
            :value="budget"
            :disabled="submitting"
            :aria-label="t('restocking.budget')"
            @input="onBudgetInput"
          >
          <span class="budget-value">{{ money(budget) }}</span>
        </div>
        <p class="help-text">{{ t('restocking.budgetHint') }}</p>
      </div>

      <div class="summary-bar" :class="{ 'over-budget': overBudget }">
        <div class="summary-item">
          <span class="summary-label">{{ t('restocking.selected') }}</span>
          <span class="summary-value">{{ selectedRows.length }}</span>
        </div>

        <div class="summary-item">
          <span class="summary-label">{{ t('restocking.selectedTotal') }}</span>
          <span class="summary-value">{{ moneyExact(selectedTotal) }}</span>
        </div>

        <div class="summary-item">
          <span v-if="overBudget" class="summary-value">
            {{ t('restocking.overBudget', { amount: moneyExact(overAmount) }) }}
          </span>
          <span v-else class="summary-value">
            {{ t('restocking.remaining', { amount: moneyExact(remaining) }) }}
          </span>
        </div>

        <template v-if="longestLeadDays !== null">
          <div class="summary-item">
            <span class="summary-label">{{ t('restocking.longestLead') }}</span>
            <span class="summary-value">{{ t('orders.leadTimeDays', { days: longestLeadDays }) }}</span>
          </div>

          <div v-if="expectedDelivery" class="summary-item">
            <span class="summary-label">{{ t('restocking.expectedDelivery') }}</span>
            <span class="summary-value">{{ expectedDelivery }}</span>
          </div>
        </template>

        <button
          type="button"
          class="place-order-btn"
          :disabled="!canPlace"
          @click="placeOrder"
        >
          {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
        </button>
      </div>

      <div v-if="submitError" class="error">
        <div>{{ t('restocking.errors.submit') }}</div>
        <div v-if="submitError.detail" class="error-detail">{{ submitError.detail }}</div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }}</h3>
        </div>

        <div v-if="rows.length === 0" class="empty">
          {{ t('restocking.noRecommendations') }}
        </div>

        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th class="col-select">
                  <input
                    type="checkbox"
                    :checked="allSelected"
                    :disabled="submitting"
                    :aria-label="t('restocking.selectAll')"
                    :title="t('restocking.selectAll')"
                    @change="toggleAll($event.target.checked)"
                  >
                </th>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.lineTotal') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.sku">
                <td>
                  <input
                    type="checkbox"
                    v-model="row.selected"
                    :disabled="submitting"
                    :aria-label="row.name"
                  >
                </td>
                <td><strong>{{ row.sku }}</strong></td>
                <td>{{ row.name }}</td>
                <td>
                  <span :class="['badge', row.trend]">{{ t(`trends.${row.trend}`) }}</span>
                </td>
                <td class="num">{{ moneyExact(row.unitCost) }}</td>
                <td class="num">
                  <input
                    v-model.number="row.qty"
                    type="number"
                    min="1"
                    step="1"
                    class="qty-input"
                    :class="{ invalid: row.selected && !isValidQty(row.qty) }"
                    :disabled="submitting"
                    :aria-label="t('restocking.table.quantity')"
                  >
                </td>
                <td class="num line-total" :class="{ dim: !row.selected }">{{ lineTotalText(row) }}</td>
                <td class="nowrap">{{ t('orders.leadTimeDays', { days: row.leadTimeDays }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { buildRecommendations, fullForecastCost } from '../utils/restocking'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

const { t, currentLocale, currentCurrency } = useI18n()

const loading = ref(true)
const loadError = ref(false)
const forecasts = ref([])
const budget = ref(0)
const rows = ref([])
const submitting = ref(false)
// { detail } where detail is the server message string, or null
const submitError = ref(null)
// { orderNumber, days } from the last successful submit
const orderPlaced = ref(null)

const money = (amount) => formatCurrency(amount, currentCurrency.value)
const moneyExact = (amount) => formatCurrencyWithDecimals(amount, currentCurrency.value, 2)

const dateLocale = computed(() => (currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'))

// Slider max: the cost of buying every forecast item, rounded up to $1,000.
const maxBudget = computed(() => Math.ceil(fullForecastCost(forecasts.value) / 1000) * 1000)

const isValidQty = (qty) => Number.isInteger(qty) && qty >= 1

// Start at about half the full forecast cost, snapped to the 500 slider step.
const initialBudget = () => Math.round((maxBudget.value * 0.5) / 500) * 500

// Rows are rebuilt only when the slider moves (or after an order is placed).
// Checkbox and quantity edits change local row state and only the totals below,
// so a manual tweak stays in place until the user deliberately changes the budget.
const rebuildRows = () => {
  rows.value = buildRecommendations(forecasts.value, budget.value).map(item => ({
    sku: item.item_sku,
    name: item.item_name,
    trend: item.trend,
    unitCost: item.unit_cost,
    leadTimeDays: item.lead_time_days,
    qty: item.suggestedQty,
    selected: item.selected
  }))
}

const onBudgetInput = (event) => {
  // Inputs are disabled while an order is in flight; this guard backs that up.
  // A budget change mid-submit would be overwritten by the success handler's
  // rebuildRows(), and a server error would quote the old budget.
  if (submitting.value) return
  budget.value = Number(event.target.value)
  // A new budget starts a fresh recommendation, so drop stale status messages.
  orderPlaced.value = null
  submitError.value = null
  rebuildRows()
}

const toggleAll = (checked) => {
  rows.value.forEach(row => {
    row.selected = checked
  })
}

const selectedRows = computed(() => rows.value.filter(row => row.selected))
const allSelected = computed(() => rows.value.length > 0 && rows.value.every(row => row.selected))
const allSelectedQtyValid = computed(() => selectedRows.value.every(row => isValidQty(row.qty)))

// Totals are compared in cents so float drift from unit costs does not flip the over-budget state.
const selectedTotal = computed(() =>
  selectedRows.value.reduce((sum, row) => (isValidQty(row.qty) ? sum + row.qty * row.unitCost : sum), 0)
)
// overBudget, remaining and overAmount all derive from the same integer cents,
// so they can never disagree. Math.max clamps to 0, which also avoids "$-0.00".
const selectedCents = computed(() => Math.round(selectedTotal.value * 100))
const budgetCents = computed(() => Math.round(budget.value * 100))
const overBudget = computed(() => selectedCents.value > budgetCents.value)
const remaining = computed(() => Math.max(0, budgetCents.value - selectedCents.value) / 100)
const overAmount = computed(() => Math.max(0, selectedCents.value - budgetCents.value) / 100)

// The order is one shipment, so it is due when its slowest item arrives.
// The longest lead time among selected rows is therefore the one that matters.
const longestLeadDays = computed(() => {
  const days = selectedRows.value.map(row => row.leadTimeDays).filter(d => Number.isFinite(d))
  return days.length ? Math.max(...days) : null
})

const expectedDelivery = computed(() => {
  if (longestLeadDays.value === null) return null
  const date = new Date()
  date.setDate(date.getDate() + longestLeadDays.value)
  if (isNaN(date.getTime())) return null
  return date.toLocaleDateString(dateLocale.value, { year: 'numeric', month: 'short', day: 'numeric' })
})

const canPlace = computed(() =>
  selectedRows.value.length > 0 &&
  allSelectedQtyValid.value &&
  !overBudget.value &&
  !submitting.value
)

// Unselected rows still show their potential cost, dimmed, so the user can see
// what selecting them would add.
const lineTotalText = (row) => (isValidQty(row.qty) ? moneyExact(row.qty * row.unitCost) : '—')

const placeOrder = async () => {
  if (!canPlace.value) return

  submitting.value = true
  submitError.value = null
  orderPlaced.value = null
  try {
    const order = await api.createRestockingOrder({
      items: selectedRows.value.map(row => ({ sku: row.sku, quantity: row.qty })),
      budget: budget.value
    })
    orderPlaced.value = { orderNumber: order.order_number, days: order.lead_time_days }
    // The order is in; reset the table to the recommendations for the current budget.
    rebuildRows()
  } catch (err) {
    console.error('Failed to place restocking order:', err)
    const detail = err.response?.data?.detail
    submitError.value = { detail: typeof detail === 'string' ? detail : null }
  } finally {
    submitting.value = false
  }
}

const loadForecasts = async () => {
  loading.value = true
  loadError.value = false
  try {
    forecasts.value = await api.getDemandForecasts()
    budget.value = initialBudget()
    rebuildRows()
  } catch (err) {
    console.error('Failed to load forecasts:', err)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadForecasts)
</script>

<style scoped>
.restocking {
  min-width: 0;
  max-width: 100%;
}

.help-text {
  font-size: 0.813rem;
  color: #64748b;
  margin-top: 0.5rem;
}

.success-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.938rem;
}

.success-link {
  color: #065f46;
  font-weight: 600;
  text-decoration: underline;
}

.error-detail {
  margin-top: 0.25rem;
  font-size: 0.875rem;
}

/* Budget slider */
.budget-control {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.budget-slider {
  flex: 1;
  min-width: 0;
  accent-color: #0f172a;
  cursor: pointer;
}

.budget-value {
  flex-shrink: 0;
  min-width: 6rem;
  text-align: right;
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

/* Summary bar */
.summary-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem 1.75rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.summary-bar.over-budget {
  background: #fef2f2;
  border-color: #fecaca;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.summary-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.summary-value {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.over-budget .summary-label,
.over-budget .summary-value {
  color: #991b1b;
}

.place-order-btn {
  margin-left: auto;
  background: #0f172a;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.625rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #1e293b;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

/* Recommendations table */
.col-select {
  width: 2.5rem;
}

th.num,
td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.nowrap {
  white-space: nowrap;
}

input[type='checkbox'] {
  width: 1rem;
  height: 1rem;
  accent-color: #0f172a;
  cursor: pointer;
}

.qty-input {
  width: 5.5rem;
  padding: 0.375rem 0.5rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #0f172a;
  text-align: right;
  background: white;
}

.qty-input:focus {
  outline: 2px solid #94a3b8;
  outline-offset: 0;
}

.qty-input.invalid {
  border-color: #ef4444;
  background: #fef2f2;
}

.line-total.dim {
  color: #94a3b8;
}

.empty {
  text-align: center;
  padding: 2rem 1rem;
  color: #64748b;
  font-size: 0.938rem;
}

/* Phone width: stack the budget control and summary items, keep the table scrolling inside its container */
@media (max-width: 640px) {
  /* App.vue's .main-content pads 2rem on every side and has no mobile override.
     Pull the view back out by 1rem so the visible gutter is 16px. */
  .restocking {
    margin: 0 -1rem;
  }

  .budget-control {
    flex-wrap: wrap;
  }

  .budget-slider {
    flex-basis: 100%;
  }

  .budget-value {
    min-width: 0;
    text-align: left;
  }

  .summary-bar {
    padding: 1rem;
  }

  .place-order-btn {
    width: 100%;
    margin-left: 0;
  }
}
</style>
