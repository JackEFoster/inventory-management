// Restocking recommendation logic.
//
// Items are ranked by trend first, then by forecast growth, and added in that
// order until the budget runs out. The ranking is intentional: the budget goes
// to items whose demand is rising before items that are flat or falling.

const TREND_PRIORITY = {
  increasing: 0,
  stable: 1,
  decreasing: 2
}

// Same growth formula as getChangePercent in views/Demand.vue
export function growthPercent(forecast) {
  if (!forecast.current_demand) return 0
  return ((forecast.forecasted_demand - forecast.current_demand) / forecast.current_demand) * 100
}

// Returns forecasts annotated with suggestedQty and selected, in ranked order.
// An item that does not fully fit gets a partial quantity when at least one
// unit fits. Items that cannot afford a single unit are skipped.
export function buildRecommendations(forecasts, budget) {
  const ranked = [...forecasts]
    .filter(f => f.unit_cost > 0 && f.forecasted_demand > 0)
    .sort((a, b) => {
      const byTrend = (TREND_PRIORITY[a.trend] ?? 99) - (TREND_PRIORITY[b.trend] ?? 99)
      if (byTrend !== 0) return byTrend
      return growthPercent(b) - growthPercent(a)
    })

  let remaining = Math.max(0, budget)
  const recommendations = []

  for (const forecast of ranked) {
    const fullQty = forecast.forecasted_demand
    const fullCost = fullQty * forecast.unit_cost
    let qty = 0

    if (fullCost <= remaining) {
      qty = fullQty
    } else {
      qty = Math.floor(remaining / forecast.unit_cost)
    }

    if (qty > 0) {
      remaining -= qty * forecast.unit_cost
      recommendations.push({ ...forecast, suggestedQty: qty, selected: true })
    }
  }

  return recommendations
}

// Cost of buying every forecast item at its forecasted quantity. Used as the
// upper bound of the budget slider.
export function fullForecastCost(forecasts) {
  return forecasts
    .filter(f => f.unit_cost > 0 && f.forecasted_demand > 0)
    .reduce((sum, f) => sum + f.forecasted_demand * f.unit_cost, 0)
}
