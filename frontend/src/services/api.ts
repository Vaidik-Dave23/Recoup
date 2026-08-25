// Recoup Frontend API Service - Integration with FastAPI Backend

const BASE_URL = import.meta.env.VITE_API_URL || '/api';

function getHeaders(): HeadersInit {
  const token = localStorage.getItem('recoup_token');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const options: RequestInit = {
    method,
    headers: getHeaders(),
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${BASE_URL}${path}`, options);

  if (response.status === 401) {
    // Session expired or unauthorized, clean up token
    localStorage.removeItem('recoup_token');
    if (!['/auth/login', '/auth/register'].includes(path)) {
      window.dispatchEvent(new Event('auth_expired'));
    }
  }

  if (!response.ok) {
    let errorDetail = 'API Request Failed';
    try {
      const errRes = await response.json();
      errorDetail = errRes.detail || errRes.message || errorDetail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Authentication
  async login(payload: unknown) {
    const data = await request<{ access_token: string }>('POST', '/auth/login', payload);
    localStorage.setItem('recoup_token', data.access_token);
    return data;
  },

  async register(payload: unknown) {
    const data = await request<{ access_token: string; user: any }>('POST', '/auth/register', payload);
    localStorage.setItem('recoup_token', data.access_token);
    return data;
  },

  async getMe() {
    return request<unknown>('GET', '/auth/me');
  },

  logout() {
    localStorage.removeItem('recoup_token');
  },

  // Recovery Cases
  async getCases() {
    return request<unknown[]>('GET', '/recovery-cases');
  },

  async getCase(caseId: string) {
    return request<unknown>('GET', `/recovery-cases/${caseId}`);
  },

  async updateCase(caseId: string, payload: unknown) {
    return request<unknown>('PATCH', `/recovery-cases/${caseId}`, payload);
  },

  async runAgent(caseId: string) {
    return request<unknown>('POST', `/recovery-cases/${caseId}/agent/run`);
  },

  async resumeAgent(caseId: string) {
    return request<unknown>('POST', `/recovery-cases/${caseId}/agent/resume`);
  },

  // AI Investigations (Trace Nodes)
  async getAIInvestigations(caseId: string) {
    return request<unknown[]>('GET', `/ai-investigations/case/${caseId}`);
  },

  // Recovery Actions Log
  async getRecoveryActions(caseId?: string) {
    if (caseId) {
      return request<unknown[]>('GET', `/recovery-actions/case/${caseId}`);
    }
    return request<unknown[]>('GET', '/recovery-actions');
  },

  // Outcomes
  async getOutcomes(caseId?: string) {
    if (caseId) {
      return request<unknown[]>('GET', `/recovery-outcomes/case/${caseId}`);
    }
    return request<unknown[]>('GET', '/recovery-outcomes');
  },

  async createOutcome(payload: {
    case_id: string;
    action_id: string;
    recovered: boolean;
    amount_recovered: number;
    notes?: string;
  }) {
    return request<unknown>('POST', '/recovery-outcomes', payload);
  },

  // Escalations
  async getEscalations() {
    return request<unknown[]>('GET', '/escalations');
  },

  async getEscalationsForCase(caseId: string) {
    return request<unknown[]>('GET', `/escalations/case/${caseId}`);
  },

  async updateEscalation(escalationId: string, payload: unknown) {
    return request<unknown>('PATCH', `/escalations/${escalationId}`, payload);
  },

  // Fault Lab Scenarios
  async getScenarios() {
    return request<unknown[]>('GET', '/fault-scenarios');
  },

  async executeScenario(scenarioId: string) {
    return request<{ success: boolean; case_id: string; message: string }>(
      'POST',
      `/fault-scenarios/${scenarioId}/execute`
    );
  },

  // Audit Logs
  async getAuditLogs() {
    return request<unknown[]>('GET', '/audit-logs');
  },

  // Dashboard Overview
  async getDashboardOverview() {
    return request<unknown>('GET', '/dashboard/overview');
  },

  // Merchant Settings
  async getMerchant() {
    return request<unknown>('GET', '/merchants/me');
  },

  async updateMerchant(payload: unknown) {
    return request<unknown>('PATCH', '/merchants/me', payload);
  },

  async getMerchantUsers() {
    return request<unknown[]>('GET', '/merchants/me/users');
  },
};
