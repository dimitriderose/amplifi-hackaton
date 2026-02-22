import { useState, useEffect } from 'react'
import { api } from '../api/client'

export function useContentPlan(brandId: string) {
  const [plan, setPlan] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  // Load the most recent plan on mount (so page refresh restores the calendar)
  useEffect(() => {
    if (!brandId) return
    setLoading(true)
    api.listPlans(brandId)
      .then((res: any) => {
        const plans: any[] = res.plans || []
        if (plans.length > 0) setPlan(plans[0])
      })
      .catch(() => { /* silently ignore — user can generate a new plan */ })
      .finally(() => setLoading(false))
  }, [brandId])

  const generatePlan = async (numDays = 7, businessEvents?: string) => {
    setGenerating(true)
    setError('')
    try {
      const result = await api.createPlan(brandId, numDays, businessEvents) as any
      setPlan(result)
    } catch (err: any) {
      setError(err.message || 'Failed to generate plan')
    } finally {
      setGenerating(false)
    }
  }

  const updateDay = async (planId: string, dayIndex: number, data: any) => {
    setLoading(true)
    try {
      await api.updateDay(brandId, planId, dayIndex, data)
      // Refresh plan after updating a day
      const updated = await api.getPlan(brandId, planId) as any
      if (updated?.plan_profile) {
        setPlan({ plan_id: planId, ...updated.plan_profile })
      }
    } catch (err: any) {
      setError(err.message || 'Failed to update day')
    } finally {
      setLoading(false)
    }
  }

  return { plan, loading, generating, error, generatePlan, updateDay }
}
