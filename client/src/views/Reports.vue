<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t('reports.title') }}</h2>
      <p>{{ t('reports.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.quarterlyPerformance') }}</h3>
        </div>
        <div v-if="quarterlyData.length === 0" class="empty-state">
          {{ t('reports.noData') }}
        </div>
        <div v-else class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.quarterlyTable.quarter') }}</th>
                <th>{{ t('reports.quarterlyTable.totalOrders') }}</th>
                <th>{{ t('reports.quarterlyTable.totalRevenue') }}</th>
                <th>{{ t('reports.quarterlyTable.avgOrderValue') }}</th>
                <th>{{ t('reports.quarterlyTable.fulfillmentRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td><strong>{{ q.quarter }}</strong></td>
                <td>{{ q.total_orders }}</td>
                <td>{{ formatMoney(q.total_revenue) }}</td>
                <td>{{ formatMoney(q.avg_order_value) }}</td>
                <td>
                  <span :class="getFulfillmentClass(q.fulfillment_rate)">
                    {{ q.fulfillment_rate }}%
                  </span>
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
        <div v-if="monthlyData.length === 0" class="empty-state">
          {{ t('reports.noData') }}
        </div>
        <div v-else class="chart-container">
          <div class="bar-chart">
            <div v-for="month in monthlyData" :key="month.month" class="bar-wrapper">
              <div class="bar-container">
                <div
                  class="bar"
                  :style="{ height: getBarHeight(month.revenue) + 'px' }"
                  :title="formatMoney(month.revenue)"
                ></div>
              </div>
              <div class="bar-label">{{ formatMonth(month.month) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.monthOverMonth') }}</h3>
        </div>
        <div v-if="monthlyData.length === 0" class="empty-state">
          {{ t('reports.noData') }}
        </div>
        <div v-else class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.monthlyTable.month') }}</th>
                <th>{{ t('reports.monthlyTable.orders') }}</th>
                <th>{{ t('reports.monthlyTable.revenue') }}</th>
                <th>{{ t('reports.monthlyTable.change') }}</th>
                <th>{{ t('reports.monthlyTable.growthRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(month, index) in monthlyData" :key="month.month">
                <td><strong>{{ formatMonth(month.month) }}</strong></td>
                <td>{{ month.order_count }}</td>
                <td>{{ formatMoney(month.revenue) }}</td>
                <td>
                  <span v-if="index > 0" :class="getChangeClass(month.revenue, monthlyData[index - 1].revenue)">
                    {{ getChangeValue(month.revenue, monthlyData[index - 1].revenue) }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="index > 0" :class="getChangeClass(month.revenue, monthlyData[index - 1].revenue)">
                    {{ getGrowthRate(month.revenue, monthlyData[index - 1].revenue) }}
                  </span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">
            {{ hasActiveFilters ? t('reports.summary.totalRevenueFiltered') : t('reports.summary.totalRevenue') }}
          </div>
          <div class="stat-value">{{ formatMoney(totalRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.summary.avgMonthlyRevenue') }}</div>
          <div class="stat-value">{{ formatMoney(avgMonthlyRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">
            {{ hasActiveFilters ? t('reports.summary.totalOrdersFiltered') : t('reports.summary.totalOrders') }}
          </div>
          <div class="stat-value">{{ totalOrders }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.summary.bestQuarter') }}</div>
          <div class="stat-value">{{ bestQuarter }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Reports',
  setup() {
    const { t, formatMoney } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const quarterlyData = ref([])
    const monthlyData = ref([])

    // Use shared filters
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      hasActiveFilters,
      getCurrentFilters
    } = useFilters()

    const loadData = async () => {
      try {
        loading.value = true
        error.value = null
        const filters = getCurrentFilters()

        const [fetchedQuarterly, fetchedMonthly] = await Promise.all([
          api.getQuarterlyReports(filters),
          api.getMonthlyTrends(filters)
        ])

        quarterlyData.value = fetchedQuarterly
        monthlyData.value = fetchedMonthly
      } catch (err) {
        error.value = t('reports.loadError', { message: err.message })
      } finally {
        loading.value = false
      }
    }

    // Watch for filter changes and reload data
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadData()
    })

    // Derived summary stats
    const totalRevenue = computed(() => {
      return monthlyData.value.reduce((sum, month) => sum + month.revenue, 0)
    })

    const avgMonthlyRevenue = computed(() => {
      if (monthlyData.value.length === 0) return 0
      return totalRevenue.value / monthlyData.value.length
    })

    const totalOrders = computed(() => {
      return monthlyData.value.reduce((sum, month) => sum + month.order_count, 0)
    })

    const bestQuarter = computed(() => {
      let bestQ = null
      let bestRevenue = -Infinity

      for (const q of quarterlyData.value) {
        if (q.total_revenue > 0 && q.total_revenue > bestRevenue) {
          bestRevenue = q.total_revenue
          bestQ = q.quarter
        }
      }

      return bestQ !== null ? bestQ : t('reports.notAvailable')
    })

    const maxMonthlyRevenue = computed(() => {
      return monthlyData.value.reduce((max, month) => Math.max(max, month.revenue), 0)
    })

    const formatMonth = (monthStr) => {
      if (typeof monthStr !== 'string') {
        return t('reports.notAvailable')
      }

      const parts = monthStr.split('-')
      if (parts.length !== 2) {
        return t('reports.notAvailable')
      }

      const year = parts[0]
      const monthIndex = parseInt(parts[1], 10)

      if (!year || isNaN(monthIndex) || monthIndex < 1 || monthIndex > 12) {
        return monthStr
      }

      return `${t(`reports.months.${monthIndex}`)} ${year}`
    }

    const getBarHeight = (revenue) => {
      // Calculate bar height (max height 200px)
      if (maxMonthlyRevenue.value === 0) {
        return 0
      }
      return (revenue / maxMonthlyRevenue.value) * 200
    }

    const getFulfillmentClass = (rate) => {
      if (rate >= 90) {
        return 'badge success'
      } else if (rate >= 75) {
        return 'badge warning'
      } else {
        return 'badge danger'
      }
    }

    const getChangeValue = (current, previous) => {
      const change = current - previous
      if (change > 0) {
        return `+${formatMoney(change)}`
      } else if (change < 0) {
        return `-${formatMoney(Math.abs(change))}`
      } else {
        return formatMoney(0)
      }
    }

    const getChangeClass = (current, previous) => {
      const change = current - previous
      if (change > 0) {
        return 'positive-change'
      } else if (change < 0) {
        return 'negative-change'
      } else {
        return ''
      }
    }

    const getGrowthRate = (current, previous) => {
      if (previous === 0) {
        return t('reports.notAvailable')
      }

      const rate = ((current - previous) / previous) * 100
      const sign = rate > 0 ? '+' : ''

      return `${sign}${rate.toFixed(1)}%`
    }

    onMounted(loadData)

    return {
      t,
      loading,
      error,
      quarterlyData,
      monthlyData,
      hasActiveFilters,
      formatMoney,
      totalRevenue,
      avgMonthlyRevenue,
      totalOrders,
      bestQuarter,
      formatMonth,
      getBarHeight,
      getFulfillmentClass,
      getChangeValue,
      getChangeClass,
      getGrowthRate
    }
  }
}
</script>

<style scoped>
.reports {
  padding: 0;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
  font-size: 0.875rem;
}

.reports-table {
  width: 100%;
  border-collapse: collapse;
}

.reports-table th {
  background: #f8fafc;
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #64748b;
  border-bottom: 2px solid #e2e8f0;
}

.reports-table td {
  padding: 0.75rem;
  font-size: 0.875rem;
  border-bottom: 1px solid #e2e8f0;
}

.reports-table tr:hover {
  background: #f8fafc;
}

.chart-container {
  padding: 2rem 1rem;
  min-height: 300px;
  overflow-x: auto;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 250px;
  gap: 0.5rem;
  min-width: 640px;
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

.bar {
  width: 100%;
  background: #3b82f6;
  border-radius: 6px 6px 0 0;
  transition: all 0.3s;
  cursor: pointer;
}

.bar:hover {
  background: #2563eb;
}

.bar-label {
  font-size: 0.75rem;
  color: #64748b;
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
  margin-top: 1.5rem;
}

.positive-change {
  color: #16a34a;
  font-weight: 600;
}

.negative-change {
  color: #dc2626;
  font-weight: 600;
}
</style>
