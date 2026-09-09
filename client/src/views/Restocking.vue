<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budgetLabel') }}: {{ currencySymbol }}{{ budget.toLocaleString() }}</h3>
          <span v-if="refreshing" class="refreshing-indicator">{{ t('common.loading') }}</span>
        </div>
        <input
          type="range"
          class="budget-slider"
          min="0"
          max="10000"
          step="250"
          v-model.number="budget"
        >
        <p class="refresh-note">{{ t('restocking.refreshNote') }}</p>

        <div class="budget-summary">
          <div class="summary-item">
            <span class="summary-label">{{ t('restocking.totalEstimatedCost') }}</span>
            <span class="summary-value">{{ currencySymbol }}{{ totalEstimatedCost.toLocaleString() }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('restocking.remainingBudget') }}</span>
            <span class="summary-value">{{ currencySymbol }}{{ remainingBudget.toLocaleString() }}</span>
          </div>
        </div>
      </div>

      <div v-if="lastPlacedOrder" class="success-banner">
        {{ t('restocking.orderPlaced', { orderNumber: lastPlacedOrder.order_number, days: lastPlacedOrder.lead_time_days }) }}
      </div>
      <div v-if="submitError" class="error">{{ submitError }}</div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ lineItems.length }})</h3>
          <button
            class="btn-primary"
            :disabled="!canPlaceOrder"
            @click="placeOrder"
          >
            {{ t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="lineItems.length === 0" class="empty-state">
          {{ t('restocking.noRecommendations') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.warehouse') }}</th>
                <th>{{ t('restocking.table.category') }}</th>
                <th>{{ t('restocking.table.currentDemand') }}</th>
                <th>{{ t('restocking.table.forecastedDemand') }}</th>
                <th>{{ t('restocking.table.recommendedQty') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.lineTotal') }}</th>
                <th>{{ t('restocking.table.remove') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in lineItems" :key="`${item.item_sku}-${item.warehouse}`">
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td>{{ translateWarehouse(item.warehouse) }}</td>
                <td>{{ item.category }}</td>
                <td>{{ item.current_demand }}</td>
                <td>{{ item.forecasted_demand }}</td>
                <td>{{ item.recommended_quantity }}</td>
                <td>{{ currencySymbol }}{{ item.unit_cost.toLocaleString() }}</td>
                <td>
                  <input
                    type="number"
                    class="quantity-input"
                    min="0"
                    :max="item.recommended_quantity"
                    v-model.number="item.quantity"
                    @change="clampQuantity(item)"
                    @blur="clampQuantity(item)"
                  >
                </td>
                <td><strong>{{ currencySymbol }}{{ lineTotal(item).toLocaleString() }}</strong></td>
                <td>
                  <button class="btn-remove" @click="removeItem(item)">
                    {{ t('restocking.table.remove') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
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

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateWarehouse } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const loading = ref(true)
    const refreshing = ref(false)
    const error = ref(null)

    const budget = ref(5000)
    const totalEstimatedCost = ref(0)
    const remainingBudget = ref(0)
    const lineItems = ref([])

    const submitting = ref(false)
    const submitError = ref(null)
    const lastPlacedOrder = ref(null)

    const { selectedLocation, selectedCategory } = useFilters()

    let requestId = 0
    let budgetDebounceTimer = null

    const loadRecommendations = async () => {
      if (!budget.value || budget.value <= 0) {
        lineItems.value = []
        totalEstimatedCost.value = 0
        remainingBudget.value = 0
        error.value = null
        loading.value = false
        refreshing.value = false
        return
      }

      const myRequestId = ++requestId
      error.value = null
      if (!loading.value) refreshing.value = true

      try {
        const data = await api.getRestockingRecommendations({
          budget: budget.value,
          warehouse: selectedLocation.value,
          category: selectedCategory.value
        })

        if (myRequestId !== requestId) return

        totalEstimatedCost.value = data.total_estimated_cost
        remainingBudget.value = data.remaining_budget
        lineItems.value = data.items.map(item => ({ ...item }))
      } catch (err) {
        if (myRequestId !== requestId) return
        error.value = 'Failed to load restocking recommendations: ' + err.message
      } finally {
        if (myRequestId === requestId) {
          loading.value = false
          refreshing.value = false
        }
      }
    }

    // Debounce budget-driven reloads so slider dragging doesn't spam requests
    watch(budget, () => {
      if (budgetDebounceTimer) clearTimeout(budgetDebounceTimer)
      budgetDebounceTimer = setTimeout(() => {
        loadRecommendations()
      }, 300)
    })

    // Filter changes reload immediately; every reload fully replaces lineItems,
    // discarding any in-progress edits (surfaced to the user via refresh-note).
    watch([selectedLocation, selectedCategory], () => {
      loadRecommendations()
    })

    const clampQuantity = (item) => {
      let value = Number(item.quantity)
      if (!Number.isFinite(value)) value = 0
      item.quantity = Math.min(Math.max(0, value), item.recommended_quantity)
    }

    const removeItem = (item) => {
      lineItems.value = lineItems.value.filter(i => i !== item)
    }

    const lineTotal = (item) => {
      return item.quantity * item.unit_cost
    }

    const canPlaceOrder = computed(() => {
      return !submitting.value && lineItems.value.some(item => item.quantity > 0)
    })

    const placeOrder = async () => {
      submitting.value = true
      submitError.value = null
      try {
        const payload = {
          budget: budget.value,
          items: lineItems.value
            .filter(item => item.quantity > 0)
            .map(item => ({
              item_sku: item.item_sku,
              item_name: item.item_name,
              quantity: item.quantity,
              unit_cost: item.unit_cost,
              warehouse: item.warehouse,
              category: item.category
            }))
        }

        const order = await api.submitRestockingOrder(payload)
        lastPlacedOrder.value = order
        await loadRecommendations()
      } catch (err) {
        submitError.value = err.response?.data?.detail || ('Failed to place order: ' + err.message)
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadRecommendations)

    return {
      t,
      currencySymbol,
      translateWarehouse,
      loading,
      refreshing,
      error,
      budget,
      totalEstimatedCost,
      remainingBudget,
      lineItems,
      submitting,
      submitError,
      lastPlacedOrder,
      clampQuantity,
      removeItem,
      lineTotal,
      canPlaceOrder,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-slider {
  width: 100%;
  accent-color: #3b82f6;
  margin: 0.5rem 0;
}

.refresh-note {
  color: #64748b;
  font-size: 0.813rem;
  font-style: italic;
  margin-bottom: 1rem;
}

.refreshing-indicator {
  color: #64748b;
  font-size: 0.813rem;
  font-style: italic;
}

.budget-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.75rem;
  background: #f8fafc;
  border-radius: 8px;
}

.summary-label {
  font-size: 0.813rem;
  color: #64748b;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.summary-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
}

.success-banner {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
  font-size: 0.938rem;
}

.quantity-input {
  width: 80px;
  padding: 0.375rem 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #334155;
}

.btn-remove {
  background: none;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 0.375rem 0.75rem;
  border-radius: 6px;
  font-size: 0.813rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-remove:hover {
  background: #fef2f2;
}
</style>
