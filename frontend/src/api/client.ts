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

  createPlan: (data: object) =>
    request('/api/plans', { method: 'POST', body: JSON.stringify(data) }),
  getPlan: (planId: string) => request(`/api/plans/${planId}`),
  updateDay: (planId: string, dayIndex: number, data: object) =>
    request(`/api/plans/${planId}/days/${dayIndex}`, { method: 'PUT', body: JSON.stringify(data) }),

  listPosts: (brandId: string, planId?: string) =>
    request(`/api/posts?brand_id=${brandId}${planId ? `&plan_id=${planId}` : ''}`),
  approvePost: (postId: string) =>
    request(`/api/posts/${postId}/approve`, { method: 'PUT' }),
  exportPost: (postId: string) => request(`/api/posts/${postId}/export`),
  exportPlan: (planId: string) =>
    request(`/api/export/${planId}`, { method: 'POST' }),

  generateVideo: (postId: string, tier = 'fast') =>
    request(`/api/posts/${postId}/generate-video?tier=${tier}`, { method: 'POST' }),
  getVideoJob: (jobId: string) => request(`/api/video-jobs/${jobId}`),
}
