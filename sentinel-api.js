/*
 * PROJECT SENTINEL data-access boundary.
 * The browser uses same-origin /api routes served by backend/main.py.
 */
(function initSentinelApi(global) {
  // The API is intentionally same-origin. Opening code.html directly from the
  // filesystem makes relative /api requests target file:// and cannot work.
  if (window.location.protocol === 'file:') {
    window.location.replace(`http://127.0.0.1:8000/${window.location.hash || ''}`);
    return;
  }

  const API_BASE = '/api';
  const DATASET_CONTRACT = Object.freeze({
    source: 'neo (3).csv',
    fields: Object.freeze([
      'id', 'name', 'est_diameter_min', 'est_diameter_max', 'relative_velocity',
      'miss_distance', 'orbiting_body', 'sentry_object', 'absolute_magnitude', 'hazardous',
    ]),
    note: 'The deployed model verifies mag, km/h, and km only for its three input fields. Diameter units are not asserted by this frontend.',
  });

  class ApiError extends Error {
    constructor(message, status, detail) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.detail = detail;
    }
  }

  async function request(path, options) {
    let response;
    try {
      response = await fetch(`${API_BASE}${path}`, {
        headers: { Accept: 'application/json', ...(options && options.headers) },
        ...options,
      });
    } catch (error) {
      throw new ApiError('The API could not be reached. Start the FastAPI service and try again.');
    }

    if (!response.ok) {
      let detail = '';
      try {
        const body = await response.json();
        detail = typeof body.detail === 'string' ? body.detail : '';
      } catch (error) {
        // Keep the safe status-only message when a proxy or server returns no JSON.
      }
      throw new ApiError(detail || `API request failed (${response.status}).`, response.status, detail);
    }

    try {
      return await response.json();
    } catch (error) {
      throw new ApiError('The API returned an invalid JSON response.', response.status);
    }
  }

  global.SentinelApi = Object.freeze({
    datasetContract: DATASET_CONTRACT,
    getModelInfo: () => request('/model-info'),
    predict: (payload) => request('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
    listAsteroids: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return request(`/asteroids${query ? `?${query}` : ''}`);
    },
  });
})(window);
