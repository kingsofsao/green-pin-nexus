import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/Card';
import Badge from '../components/Badge';
import { api } from '../services/api';
import { Shield, Users, AlertTriangle, Activity, Play, ArrowRight, ShieldAlert, GitBranch, RefreshCw } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';

export default function Overview() {
  const [data, setData] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const loadData = async () => {
    setLoading(true);
    try {
      const [dash, hlth] = await Promise.all([api.getDashboard(), api.health()]);
      setData(dash);
      setHealth(hlth);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!data) return <div className="p-8 text-slate-400">Loading intelligence dashboard...</div>;

  const kpis = data.overview_kpis || {};
  const riskDist = data.risk_distribution || {};

  const pieData = [
    { name: 'Low Risk', value: riskDist.LOW || 85, color: '#10b981' },
    { name: 'Moderate', value: riskDist.MODERATE || 10, color: '#f59e0b' },
    { name: 'High Risk', value: riskDist.HIGH || 4, color: '#f97316' },
    { name: 'Critical', value: riskDist.CRITICAL || 1, color: '#ef4444' },
  ];

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 font-[Inter]">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1">GOOD MORNING, ANANYA</h1>
          <h2 className="text-lg font-semibold text-primary uppercase tracking-widest font-mono mb-2">
            PRIVILEGED SECURITY OVERVIEW
          </h2>
          <p className="text-slate-400">Monitoring privileged identities and investigating high-risk activity.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition-colors"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <div className="flex items-center gap-2 bg-panel px-3.5 py-2 rounded-lg border border-slate-800">
            <span className="text-xs text-slate-400">Pipeline Status:</span>
            <Badge level={health?.status === 'ok' ? 'ONLINE' : 'OFFLINE'} />
          </div>
        </div>
      </div>

      {/* Quick Action Navigation Bar */}
      <Card className="p-4 bg-slate-900/60 border-slate-800">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">Quick Actions & Demonstrations:</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          <button
            onClick={() => navigate('/demo-center')}
            className="p-3 rounded-lg bg-primary/10 hover:bg-primary/20 border border-primary/30 text-primary flex items-center justify-between text-xs font-bold transition-all"
          >
            <span className="flex items-center gap-2">
              <Play size={15} /> Demo Center
            </span>
            <ArrowRight size={14} />
          </button>
          <button
            onClick={() => navigate('/response-center')}
            className="p-3 rounded-lg bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 flex items-center justify-between text-xs font-bold transition-all"
          >
            <span className="flex items-center gap-2">
              <ShieldAlert size={15} /> Response Center
            </span>
            <ArrowRight size={14} />
          </button>
          <button
            onClick={() => navigate('/attack-timeline')}
            className="p-3 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-400 flex items-center justify-between text-xs font-bold transition-all"
          >
            <span className="flex items-center gap-2">
              <Activity size={15} /> Attack Timeline
            </span>
            <ArrowRight size={14} />
          </button>
          <button
            onClick={() => navigate('/relationship-graph')}
            className="p-3 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 text-blue-400 flex items-center justify-between text-xs font-bold transition-all"
          >
            <span className="flex items-center gap-2">
              <GitBranch size={15} /> Relationship Graph
            </span>
            <ArrowRight size={14} />
          </button>
        </div>
      </Card>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* PRIVILEGED OFFICERS MONITORED */}
        <Card className="flex items-center gap-3.5 cursor-pointer hover:border-slate-700 transition-colors" onClick={() => navigate('/officers')}>
          <div className="p-3 bg-primary/10 text-primary rounded-xl border border-primary/20 shrink-0">
            <Users size={20} />
          </div>
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Officers Monitored</p>
            <p className="text-xl font-bold font-mono text-slate-100">248</p>
            <span className="text-[9px] text-slate-500 font-mono italic">Simulated</span>
          </div>
        </Card>

        {/* HIGH-RISK IDENTITIES */}
        <Card className="flex items-center gap-3.5 cursor-pointer hover:border-slate-700 transition-colors" onClick={() => navigate('/officers')}>
          <div className="p-3 bg-warning/10 text-warning rounded-xl border border-warning/20 shrink-0">
            <AlertTriangle size={20} />
          </div>
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">High-Risk Identities</p>
            <p className="text-xl font-bold font-mono text-amber-500">23</p>
            <span className="text-[9px] text-slate-500 font-mono italic">Simulated</span>
          </div>
        </Card>

        {/* CRITICAL ALERTS */}
        <Card className="flex items-center gap-3.5 cursor-pointer hover:border-slate-700 transition-colors" onClick={() => navigate('/alerts')}>
          <div className="p-3 bg-danger/10 text-danger rounded-xl border border-danger/20 shrink-0">
            <ShieldAlert size={20} />
          </div>
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Critical Alerts</p>
            <p className="text-xl font-bold font-mono text-red-500">7</p>
            <span className="text-[9px] text-slate-500 font-mono italic">Simulated</span>
          </div>
        </Card>

        {/* ACTIVE INVESTIGATIONS */}
        <Card className="flex items-center gap-3.5 cursor-pointer hover:border-slate-700 transition-colors" onClick={() => navigate('/live-activity')}>
          <div className="p-3 bg-info/10 text-info rounded-xl border border-info/20 shrink-0">
            <Activity size={20} />
          </div>
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Active Investigations</p>
            <p className="text-xl font-bold font-mono text-blue-400">12</p>
            <span className="text-[9px] text-slate-500 font-mono italic">Simulated</span>
          </div>
        </Card>

        {/* PENDING DECISIONS */}
        <Card className="flex items-center gap-3.5 cursor-pointer hover:border-slate-700 transition-colors" onClick={() => navigate('/response-center')}>
          <div className="p-3 bg-purple-500/10 text-purple-400 rounded-xl border border-purple-500/20 shrink-0">
            <Shield size={20} />
          </div>
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Pending Decisions</p>
            <p className="text-xl font-bold font-mono text-purple-400">5</p>
            <span className="text-[9px] text-slate-500 font-mono italic">Simulated</span>
          </div>
        </Card>
      </div>

      {/* Charts & Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Privileged Risk Distribution" className="lg:col-span-1 flex flex-col justify-between">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={75}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                  itemStyle={{ color: '#e2e8f0', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-2 border-t border-slate-800">
            {pieData.map((p, idx) => (
              <div key={idx} className="flex items-center justify-between p-1.5 rounded bg-slate-800/40">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.color }}></span>
                  <span className="text-slate-300">{p.name}:</span>
                </span>
                <span className="font-bold text-slate-100">{p.value}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Recent Privileged Activity Stream" className="lg:col-span-2">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-slate-400 uppercase bg-slate-800/50">
                <tr>
                  <th className="px-3.5 py-2.5">User ID</th>
                  <th className="px-3.5 py-2.5">Action</th>
                  <th className="px-3.5 py-2.5">Amount</th>
                  <th className="px-3.5 py-2.5">Risk Level</th>
                  <th className="px-3.5 py-2.5">Time</th>
                  <th className="px-3.5 py-2.5 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody>
                {data.recentEvents?.map((event: any, i: number) => (
                  <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                    <td className="px-3.5 py-2.5 font-mono font-bold text-slate-200">{event.userId}</td>
                    <td className="px-3.5 py-2.5 font-medium text-slate-300">{event.action}</td>
                    <td className="px-3.5 py-2.5 font-mono text-slate-400">
                      {event.amount ? `₹${event.amount.toLocaleString()}` : '-'}
                    </td>
                    <td className="px-3.5 py-2.5"><Badge level={event.risk} /></td>
                    <td className="px-3.5 py-2.5 font-mono text-slate-400">{new Date(event.timestamp).toLocaleTimeString()}</td>
                    <td className="px-3.5 py-2.5 text-right">
                      <button
                        onClick={() => navigate('/context-investigation')}
                        className="px-2 py-1 bg-slate-800 hover:bg-primary/20 hover:text-primary rounded text-[11px] text-slate-300 font-semibold transition-colors"
                      >
                        Context
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
