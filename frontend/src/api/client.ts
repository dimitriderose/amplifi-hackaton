async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  createBrand: (data: object) =>
    request('/api/brands', { method: 'POST', body: JSON.stringify(data) }),
  analyzeBrand: (brandId: string, data: object) =>
    request(`/api/brands/${brandId}/analyze`, { method: 'POST', body: JSON.stringify(data) }),
  getBrand: (brandId: string) => request(`/api/brands/${brandId}`),
  updateBrand: (brandId: string, data: object) =>
    request(`/api/brands/${brandId}`, { method: 'PUT', body: JSON.stringify(data) }),
  uploadBrandAsset: (brandId: string, formData: FormData) =>
    fetch(`/api/brands/${brandId}/upload`, { method: 'POST', body: formData }).then(r => r.json()),

  listPlans: (brandId: string) => request(`/api/brands/${brandId}/plans`),
  createPlan: (brandId: string, numDays = 7, businessEvents?: string) =>
    request(`/api/brands/${brandId}/plans`, {
      method: 'POST',
      body: JSON.stringify({ num_days: numDays, business_events: businessEvents || null }),
    }),
  getPlan: (brandId: string, planId: string) => request(`/api/brands/${brandId}/plans/${planId}`),
  updateDay: (brandId: string, planId: string, dayIndex: number, data: object) =>
    request(`/api/brands/${brandId}/plans/${planId}/days/${dayIndex}`, { method: 'PUT', body: JSON.stringify(data) }),

  listPosts: (brandId: string, planId?: string) =>
    request(`/api/posts?brand_id=${brandId}${planId ? `&plan_id=${planId}` : ''}`),
  reviewPost: (brandId: string, postId: string) =>
    request(`/api/brands/${brandId}/posts/${postId}/review`, { method: 'POST' }),
  approvePost: (brandId: string, postId: string) =>
    request(`/api/brands/${brandId}/posts/${postId}/approve`, { method: 'POST' }),
  exportPost: (postId: string, brandId: string) => request(`/api/posts/${postId}/export?brand_id=${brandId}`),
  exportPlan: (planId: string, brandId: string) =>
    fetch(`/api/export/${planId}?brand_id=${encodeURIComponent(brandId)}`, { method: 'POST' })
      .then(async r => {
        if (!r.ok) {
          const err = await r.json().catch(() => ({ error: r.statusText }))
          throw new Error(err.error || `HTTP ${r.status}`)
        }
        const blob = await r.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `amplifi_export_${planId}.zip`
        a.click()
        URL.revokeObjectURL(url)
      }),

  generateVideo: (postId: string, tier = 'fast', brandId = '') =>
    request(`/api/posts/${postId}/generate-video?tier=${tier}&brand_id=${brandId}`, { method: 'POST' }),
  getVideoJob: (jobId: string) => request(`/api/video-jobs/${jobId}`),
}
