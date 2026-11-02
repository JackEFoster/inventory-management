<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div
          ref="dialogRef"
          class="modal-container"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
          @click.stop
          @keydown="onKeydown"
        >
          <div class="modal-header">
            <h3 :id="titleId" class="modal-title">
              {{ mode === 'view' ? t('purchaseOrder.viewTitle') : t('purchaseOrder.createTitle') }}
            </h3>
            <button ref="closeButtonRef" type="button" class="close-button" :aria-label="t('purchaseOrder.close')" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <!-- Backlog item context, shown in both modes -->
            <div class="item-summary">
              <div class="item-summary-main">
                <div class="item-name">{{ translateProductName(backlogItem.item_name) }}</div>
                <div class="item-meta">
                  <span class="mono">{{ backlogItem.item_sku }}</span>
                  <span aria-hidden="true">&middot;</span>
                  <span class="mono">{{ backlogItem.order_id }}</span>
                </div>
              </div>
              <div class="shortage-pill">
                <span class="shortage-label">{{ t('purchaseOrder.shortage') }}</span>
                <span class="shortage-value">{{ shortage }} {{ t('purchaseOrder.units') }}</span>
              </div>
            </div>

            <!-- Create mode -->
            <form v-if="mode === 'create'" :id="formId" class="po-form" novalidate @submit.prevent="submit">
              <div class="form-group full">
                <label :for="fieldId('supplier')">{{ t('purchaseOrder.supplierName') }}</label>
                <input
                  :id="fieldId('supplier')"
                  ref="firstFieldRef"
                  v-model="form.supplier_name"
                  type="text"
                  class="form-input"
                  autocomplete="organization"
                  :placeholder="t('purchaseOrder.supplierPlaceholder')"
                  :aria-invalid="!!errors.supplier_name"
                  :aria-describedby="errors.supplier_name ? fieldId('supplier-error') : undefined"
                  required
                />
                <p v-if="errors.supplier_name" :id="fieldId('supplier-error')" class="field-error">
                  {{ errors.supplier_name }}
                </p>
              </div>

              <div class="form-group">
                <label :for="fieldId('quantity')">{{ t('purchaseOrder.quantity') }}</label>
                <input
                  :id="fieldId('quantity')"
                  v-model.number="form.quantity"
                  type="number"
                  min="1"
                  step="1"
                  inputmode="numeric"
                  class="form-input"
                  :aria-invalid="!!errors.quantity"
                  :aria-describedby="errors.quantity ? fieldId('quantity-error') : undefined"
                  required
                />
                <p v-if="errors.quantity" :id="fieldId('quantity-error')" class="field-error">{{ errors.quantity }}</p>
              </div>

              <div class="form-group">
                <label :for="fieldId('unit-cost')">{{ t('purchaseOrder.unitCost') }}</label>
                <input
                  :id="fieldId('unit-cost')"
                  v-model.number="form.unit_cost"
                  type="number"
                  min="0"
                  step="0.01"
                  inputmode="decimal"
                  class="form-input"
                  :aria-invalid="!!errors.unit_cost"
                  :aria-describedby="errors.unit_cost ? fieldId('unit-cost-error') : undefined"
                  required
                />
                <p v-if="errors.unit_cost" :id="fieldId('unit-cost-error')" class="field-error">
                  {{ errors.unit_cost }}
                </p>
              </div>

              <div class="form-group">
                <label :for="fieldId('delivery')">{{ t('purchaseOrder.expectedDeliveryDate') }}</label>
                <input
                  :id="fieldId('delivery')"
                  v-model="form.expected_delivery_date"
                  type="date"
                  :min="today"
                  class="form-input"
                  :aria-invalid="!!errors.expected_delivery_date"
                  :aria-describedby="errors.expected_delivery_date ? fieldId('delivery-error') : undefined"
                  required
                />
                <p v-if="errors.expected_delivery_date" :id="fieldId('delivery-error')" class="field-error">
                  {{ errors.expected_delivery_date }}
                </p>
              </div>

              <div class="form-group total-group">
                <span class="total-label">{{ t('purchaseOrder.total') }}</span>
                <span class="total-value" aria-live="polite">{{ formattedFormTotal }}</span>
              </div>

              <div class="form-group full">
                <label :for="fieldId('notes')">
                  {{ t('purchaseOrder.notes') }}
                  <span class="optional">({{ t('purchaseOrder.optional') }})</span>
                </label>
                <textarea :id="fieldId('notes')" v-model="form.notes" class="form-input form-textarea" rows="3" />
              </div>

              <p v-if="submitError" class="form-error" role="alert">{{ submitError }}</p>
            </form>

            <!-- View mode -->
            <template v-else>
              <div v-if="loading" class="state-message" role="status">{{ t('purchaseOrder.loading') }}</div>
              <div v-else-if="loadError" class="form-error" role="alert">{{ loadError }}</div>
              <dl v-else-if="purchaseOrder" class="info-grid">
                <div class="info-item">
                  <dt class="info-label">{{ t('purchaseOrder.poNumber') }}</dt>
                  <dd class="info-value mono accent">{{ purchaseOrder.id.toUpperCase() }}</dd>
                </div>
                <div class="info-item">
                  <dt class="info-label">{{ t('purchaseOrder.status') }}</dt>
                  <dd class="info-value">
                    <span class="badge info">{{ translateStatus(purchaseOrder.status) }}</span>
                  </dd>
                </div>
                <div class="info-item">
                  <dt class="info-label">{{ t('purchaseOrder.supplierName') }}</dt>
                  <dd class="info-value">{{ purchaseOrder.supplier_name }}</dd>
                </div>
                <div class="info-item">
                  <dt class="info-label">{{ t('purchaseOrder.quantity') }}</dt>
                  <dd class="info-value">{{ purchaseOrder.quantity.toLocaleString() }} {{ t('purchaseOrder.units') }}</dd>
                </div>
                <div class="info-item">
                  <dt class="info-label">{{ t('purchaseOrder.unitCost') }}</dt>
                  <dd class="info-value">{{ formatMoney(purchaseOrder.unit_cost) }}</dd>
                </div>
                <div class="info-item">
                  <dt class="info-label">{{ t('purchaseOrder.total') }}</dt>
                  <dd class="info-value strong">{{ formatMoney(purchaseOrder.quantity * purchaseOrder.unit_cost) }}</dd>
                </div>
                <div class="info-item">
                  <dt class="info-label">{{ t('purchaseOrder.expectedDeliveryDate') }}</dt>
                  <dd class="info-value">{{ formatDate(purchaseOrder.expected_delivery_date) }}</dd>
                </div>
                <div class="info-item">
                  <dt class="info-label">{{ t('purchaseOrder.createdDate') }}</dt>
                  <dd class="info-value">{{ formatDate(purchaseOrder.created_date) }}</dd>
                </div>
                <div class="info-item full">
                  <dt class="info-label">{{ t('purchaseOrder.notes') }}</dt>
                  <dd class="info-value notes">{{ purchaseOrder.notes || t('purchaseOrder.noNotes') }}</dd>
                </div>
              </dl>
            </template>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="close">
              {{ mode === 'create' ? t('common.cancel') : t('common.close') }}
            </button>
            <button v-if="mode === 'create'" type="submit" :form="formId" class="btn-primary" :disabled="submitting">
              {{ submitting ? t('purchaseOrder.submitting') : t('purchaseOrder.submit') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  backlogItem: {
    type: Object,
    default: null
  },
  mode: {
    type: String,
    default: 'create',
    validator: (value) => ['create', 'view'].includes(value)
  }
})

const emit = defineEmits(['close', 'po-created'])

const { t, currentLocale, currentCurrency, translateProductName } = useI18n()

// Unique ids so labels/aria references stay valid even if two instances exist
const uid = `po-${Math.random().toString(36).slice(2, 8)}`
const titleId = `${uid}-title`
const formId = `${uid}-form`
const fieldId = (name) => `${uid}-${name}`

const dialogRef = ref(null)
const closeButtonRef = ref(null)
const firstFieldRef = ref(null)
let previouslyFocused = null

const toIsoDate = (date) => {
  // Local calendar date (toISOString would shift to UTC and can be off by a day)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}
const today = toIsoDate(new Date())

const shortage = computed(() => {
  if (!props.backlogItem) return 0
  return Math.max(0, props.backlogItem.quantity_needed - props.backlogItem.quantity_available)
})

// Create-mode state
const form = reactive({
  supplier_name: '',
  quantity: 1,
  unit_cost: null,
  expected_delivery_date: '',
  notes: ''
})
const errors = reactive({})
const submitting = ref(false)
const submitError = ref(null)

// View-mode state
const purchaseOrder = ref(null)
const loading = ref(false)
const loadError = ref(null)

const formatMoney = (amount) => formatCurrencyWithDecimals(Number(amount) || 0, currentCurrency.value, 2)

const formattedFormTotal = computed(() => {
  const qty = Number(form.quantity)
  const cost = Number(form.unit_cost)
  if (!Number.isFinite(qty) || !Number.isFinite(cost) || qty <= 0 || cost < 0) return '-'
  return formatMoney(qty * cost)
})

const formatDate = (value) => {
  if (!value) return '-'
  // Bare YYYY-MM-DD strings parse as UTC midnight; anchor them to local time instead
  const date = new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00:00` : value)
  if (isNaN(date.getTime())) return value
  return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const translateStatus = (status) => {
  const key = `purchaseOrder.statuses.${status}`
  const translated = t(key)
  return translated === key ? status : translated
}

const clearErrors = () => {
  Object.keys(errors).forEach((key) => delete errors[key])
}

const resetForm = () => {
  const deliveryDefault = new Date()
  deliveryDefault.setDate(deliveryDefault.getDate() + 14)
  form.supplier_name = ''
  // Prefill with the shortage so the PO covers the backlog by default
  form.quantity = Math.max(1, shortage.value)
  form.unit_cost = null
  form.expected_delivery_date = toIsoDate(deliveryDefault)
  form.notes = ''
  clearErrors()
  submitError.value = null
  submitting.value = false
}

const validate = () => {
  clearErrors()
  if (!form.supplier_name || !form.supplier_name.trim()) {
    errors.supplier_name = t('purchaseOrder.validation.supplierRequired')
  }
  const qty = form.quantity
  if (typeof qty !== 'number' || !Number.isInteger(qty) || qty <= 0) {
    errors.quantity = t('purchaseOrder.validation.quantityInvalid')
  }
  const cost = form.unit_cost
  if (typeof cost !== 'number' || !Number.isFinite(cost) || cost < 0) {
    errors.unit_cost = t('purchaseOrder.validation.unitCostInvalid')
  }
  if (!form.expected_delivery_date) {
    errors.expected_delivery_date = t('purchaseOrder.validation.dateRequired')
  }
  return Object.keys(errors).length === 0
}

const focusFirstInvalid = () => {
  const order = [
    ['supplier_name', 'supplier'],
    ['quantity', 'quantity'],
    ['unit_cost', 'unit-cost'],
    ['expected_delivery_date', 'delivery']
  ]
  const match = order.find(([key]) => errors[key])
  if (match) document.getElementById(fieldId(match[1]))?.focus()
}

const submit = async () => {
  if (submitting.value) return
  submitError.value = null
  if (!validate()) {
    await nextTick()
    focusFirstInvalid()
    return
  }
  try {
    submitting.value = true
    const created = await api.createPurchaseOrder({
      backlog_item_id: props.backlogItem.id,
      supplier_name: form.supplier_name.trim(),
      quantity: form.quantity,
      unit_cost: form.unit_cost,
      expected_delivery_date: form.expected_delivery_date,
      notes: form.notes.trim() || null
    })
    emit('po-created', created)
  } catch (err) {
    // Map status codes to localized messages; the server's detail text is English-only
    const status = err?.response?.status
    if (status === 409) {
      submitError.value = t('purchaseOrder.errors.duplicate')
    } else if (status === 404) {
      submitError.value = t('purchaseOrder.errors.notFound')
    } else {
      submitError.value = t('purchaseOrder.errors.submit')
    }
    console.error('Create purchase order error:', err)
  } finally {
    submitting.value = false
  }
}

const loadPurchaseOrder = async () => {
  purchaseOrder.value = null
  loadError.value = null
  try {
    loading.value = true
    purchaseOrder.value = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
  } catch (err) {
    loadError.value = t('purchaseOrder.errors.load')
    console.error('Load purchase order error:', err)
  } finally {
    loading.value = false
  }
}

const close = () => {
  emit('close')
}

const getFocusable = () => {
  if (!dialogRef.value) return []
  return Array.from(
    dialogRef.value.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
    )
  )
}

// Escape closes; Tab is kept inside the dialog while it is open
const onKeydown = (event) => {
  if (event.key === 'Escape') {
    event.stopPropagation()
    close()
    return
  }
  if (event.key !== 'Tab') return
  const focusable = getFocusable()
  if (focusable.length === 0) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(
  () => props.isOpen,
  async (open) => {
    if (open) {
      previouslyFocused = document.activeElement
      if (props.mode === 'create') {
        resetForm()
      } else if (props.backlogItem) {
        loadPurchaseOrder()
      }
      await nextTick()
      const target = props.mode === 'create' ? firstFieldRef.value : closeButtonRef.value
      target?.focus()
    } else if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
      // Return focus to the button that opened the dialog
      previouslyFocused.focus()
      previouslyFocused = null
    }
  }
)

onBeforeUnmount(() => {
  previouslyFocused = null
})
</script>

<style scoped>
/* Teleported to body, so it must sit on the shared modal layer */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
  padding: var(--space-4);
}

/* tabindex="-1" keeps focus (and the Escape handler) in the dialog after clicks on plain text */
.modal-container:focus {
  outline: none;
}

.modal-container {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  max-width: 640px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.modal-title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  letter-spacing: -0.01em;
  margin: 0;
}

.close-button {
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  transition:
    background-color var(--transition-fast),
    color var(--transition-fast);
}

.close-button:hover {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.close-button:focus-visible,
.btn-secondary:focus-visible,
.btn-primary:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
}

/* Backlog item context */
.item-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-4);
  padding: var(--space-4);
  margin-bottom: var(--space-6);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.item-summary-main {
  flex: 1;
  min-width: 160px;
}

.item-name {
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  overflow-wrap: anywhere;
}

.item-meta {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.mono {
  font-family: var(--font-mono);
}

.shortage-pill {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--danger-50);
  border: 1px solid var(--danger-500);
}

.shortage-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}

.shortage-value {
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  color: var(--danger-600);
  font-variant-numeric: tabular-nums;
}

/* Form */
.po-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.form-group.full {
  grid-column: 1 / -1;
}

label {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--color-text-secondary);
}

.optional {
  font-weight: var(--weight-regular);
  color: var(--color-text-muted);
}

.form-input {
  height: 36px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--text-base);
  font-family: inherit;
  min-width: 0;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.form-textarea {
  height: auto;
  padding: var(--space-2) var(--space-3);
  resize: vertical;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

.form-input[aria-invalid='true'] {
  border-color: var(--danger-500);
}

.field-error {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--danger-700);
}

.total-group {
  justify-content: flex-end;
}

.total-label {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--color-text-secondary);
}

.total-value {
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
  line-height: 36px;
}

.form-error {
  grid-column: 1 / -1;
  margin: 0;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  background: var(--danger-50);
  color: var(--danger-700);
  font-size: var(--text-sm);
}

.state-message {
  padding: var(--space-6) 0;
  text-align: center;
  color: var(--color-text-muted);
}

/* View mode */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
  gap: var(--space-6);
  margin: 0;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.info-item.full {
  grid-column: 1 / -1;
}

.info-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}

.info-value {
  margin: 0;
  font-size: var(--text-base);
  color: var(--color-text);
  font-weight: var(--weight-medium);
  overflow-wrap: anywhere;
}

.info-value.accent {
  color: var(--color-primary);
}

.info-value.strong {
  font-weight: var(--weight-semibold);
  font-variant-numeric: tabular-nums;
}

.info-value.notes {
  font-weight: var(--weight-regular);
  white-space: pre-wrap;
}

/* Footer */
.modal-footer {
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.btn-secondary,
.btn-primary {
  height: 36px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-md);
  font-weight: var(--weight-medium);
  font-size: var(--text-base);
  font-family: inherit;
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.btn-secondary {
  background: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  color: var(--color-text);
}

.btn-secondary:hover {
  background: var(--color-surface-muted);
}

.btn-primary {
  background: var(--color-primary);
  border: none;
  color: var(--color-surface);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 520px) {
  .po-form {
    grid-template-columns: 1fr;
  }
}

/* Modal transition animations (opacity on the overlay, transform on the panel) */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
