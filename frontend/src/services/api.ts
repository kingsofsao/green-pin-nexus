export const api = {
  health: async () => {
    try {
      const res = await fetch('/api/health');
      if (!res.ok) throw new Error('Health check failed');
      return await res.json();
    } catch {
      return { status: 'offline' };
    }
  },

  getDashboard: async () => {
    try {
      const res = await fetch('/api/dashboard');
      if (!res.ok) throw new Error('Dashboard fetch failed');
      return await res.json();
    } catch (err) {
      console.error(err);
      return {
        overview_kpis: {
          total_users: 100,
          total_events: 5420,
          active_alerts: 5,
          critical_incidents: 1
        },
        risk_distribution: {
          LOW: 85,
          MODERATE: 10,
          HIGH: 4,
          CRITICAL: 1
        },
        system_status: 'Operational',
        recentEvents: []
      };
    }
  },

  getEvents: async () => {
    try {
      const res = await fetch('/api/events');
      if (!res.ok) throw new Error('Events fetch failed');
      return await res.json();
    } catch (err) {
      console.error(err);
      return { events: [] };
    }
  },

  getUsers: async () => {
    try {
      const res = await fetch('/api/users');
      if (!res.ok) throw new Error('Users fetch failed');
      return await res.json();
    } catch (err) {
      console.error(err);
      return [];
    }
  },

  getRisk: async (userId: string) => {
    try {
      const res = await fetch(`/api/risk/${encodeURIComponent(userId)}`);
      if (!res.ok) throw new Error('Risk fetch failed');
      return await res.json();
    } catch (err) {
      console.error(err);
      return {
        userId,
        score: 15,
        category: 'LOW',
        factors: ['Standard behavior pattern'],
        details: {
          geoRisk: 10,
          timeRisk: 5,
          actionRisk: 15
        }
      };
    }
  },

  getTimeline: async (scenario: string) => {
    try {
      const res = await fetch(`/api/timeline/${encodeURIComponent(scenario)}`);
      if (!res.ok) throw new Error('Timeline fetch failed');
      return await res.json();
    } catch (err) {
      console.error(err);
      return { events: [] };
    }
  },

  getGraph: async (scenario: string) => {
    try {
      const res = await fetch(`/api/graph/${encodeURIComponent(scenario)}`);
      if (!res.ok) throw new Error('Graph fetch failed');
      return await res.json();
    } catch (err) {
      console.error(err);
      return { nodes: [], edges: [] };
    }
  },

  getContext: async (eventId: string) => {
    try {
      const res = await fetch(`/api/context/${encodeURIComponent(eventId)}`);
      if (!res.ok) throw new Error('Context fetch failed');
      return await res.json();
    } catch (err) {
      console.error(err);
      return null;
    }
  },

  runDemo: async (scenario: string) => {
    const res = await fetch('/api/demo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario })
    });

    if (!res.ok) throw new Error(`Scenario error: ${res.statusText}`);
    return await res.json();
  },

  respond: async (action: string, eventId: string, userId: string) => {
    const res = await fetch('/api/respond', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, eventId, userId })
    });

    if (!res.ok) throw new Error(`Response action error: ${res.statusText}`);
    return await res.json();
  },

  feedback: async (eventId: string, type: string) => {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ eventId, type })
    });

    if (!res.ok) throw new Error(`Feedback error: ${res.statusText}`);
    return await res.json();
  },

  login: async (email_or_id: string, password: string) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email_or_id, password })
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({
        detail: 'Authentication failed'
      }));
      throw new Error(errorData.detail || 'Authentication failed');
    }

    return await res.json();
  },

  logout: async (supervisor_id: string) => {
    const res = await fetch('/api/auth/logout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ supervisor_id })
    });

    if (!res.ok) throw new Error('Logout failed');
    return await res.json();
  },

  sessionExpire: async (supervisor_id: string) => {
    const res = await fetch('/api/auth/session_expire', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ supervisor_id })
    });

    if (!res.ok) throw new Error('Session expire failed');
    return await res.json();
  },

  getAuditLogs: async () => {
    try {
      const res = await fetch('/api/audit');
      if (!res.ok) throw new Error('Audit logs fetch failed');
      return await res.json();
    } catch (err) {
      console.error(err);
      return [];
    }
  },

  recordAudit: async (
    action: string,
    target?: string,
    details?: string
  ) => {
    try {
      const res = await fetch('/api/audit/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, target, details })
      });

      if (!res.ok) throw new Error('Record audit failed');
      return await res.json();
    } catch (err) {
      console.error(err);
      return null;
    }
  },

  playSecurityVoiceAlert: async (text: string, voiceId?: string) => {
    const res = await fetch('/api/security-alert/voice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice_id: voiceId })
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({
        detail: 'Voice alert failed'
      }));
      throw new Error(errorData.detail || 'Voice alert failed');
    }

    return await res.blob();
  }
};
