import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/Card';
import Badge from '../components/Badge';
import { api } from '../services/api';
import { AlertOctagon, CheckCircle2, ShieldAlert, Zap, History, MessageSquare, Play, HelpCircle } from 'lucide-react';

export default function ResponseCenter() {
  const [criticalEvent, setCriticalEvent] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  
  // Response Confirmation Modal State
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingAction, setPendingAction] = useState<string>('');
  const [confirmMessage, setConfirmMessage] = useState<string>('');

  // Feedback State
  const [feedbackType, setFeedbackType] = useState<string>('TRUE_POSITIVE');
  const [supervisorNotes, setSupervisorNotes] = useState<string>('');

  const navigate = useNavigate();

  const fetchCritical = async () => {
    try {
      const data = await api.getEvents();
      const critical = (data.events || []).find((e: any) => (e.risk === 'CRITICAL' || e.risk === 'HIGH') && e.status !== 'DENIED');
      if (critical) {
        setCriticalEvent(critical);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchCritical();
  }, []);

  const handleSimulateAttack = async () => {
    setLoading(true);
    try {
      await api.runDemo('attack');
      setCriticalEvent({
        id: 'EVT-C1-04',
        userId: 'EMP-1042',
        role: 'Senior Payment Administrator',
        action: 'PAYMENT_INITIATED',
        amount: 850000,
        risk: 'CRITICAL',
        riskScore: 96,
        status: 'HELD',
        timestamp: new Date().toISOString()
      });
      setFeedback('Attack scenario triggered: High-risk incident loaded for containment.');
      setTimeout(() => setFeedback(null), 4000);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const initiateAction = (action: string) => {
    let msg = '';
    switch (action) {
      case 'HOLD_PAYMENT':
        msg = 'Are you sure you want to place this simulated payment on hold?';
        break;
      case 'RESTRICT_SESSION':
        msg = 'Are you sure you want to restrict this simulated session?';
        break;
      case 'ESCALATE':
        msg = 'Are you sure you want to escalate this incident?';
        break;
      case 'VERIFY':
        msg = 'Are you sure you want to request additional verification?';
        break;
      default:
        msg = `Are you sure you want to execute simulated response: ${action}?`;
    }
    setPendingAction(action);
    setConfirmMessage(msg);
    setShowConfirmModal(true);
  };

  const confirmAction = async () => {
    if (!criticalEvent) return;
    setLoading(true);
    setShowConfirmModal(false);
    try {
      await api.respond(pendingAction, criticalEvent.id, criticalEvent.userId);
      setFeedback(`RESPONSE EXECUTED — SIMULATION. Action '${pendingAction}' logged for user ${criticalEvent.userId}.`);
      setCriticalEvent(null);
      setTimeout(() => setFeedback(null), 5000);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const handleVoiceAlert = async () => {
    setVoiceLoading(true);
    setVoiceError(null);

    try {
      const event = criticalEvent;
      const eventDescription = event
        ? `Critical security alert. High risk privileged operation detected. Event ${event.id}. User ${event.userId}. Action ${event.action}. Risk score ${event.riskScore}.`
        : 'Critical security alert. No active threat is currently waiting in the response queue.';

      const blob = await api.playSecurityVoiceAlert(eventDescription);
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);

      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        setVoiceLoading(false);
      };

      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        setVoiceLoading(false);
        setVoiceError('The browser could not play the generated voice alert.');
      };

      await audio.play();
    } catch (err) {
      console.error(err);
      setVoiceLoading(false);
      setVoiceError(
        err instanceof Error ? err.message : 'Voice alert failed.'
      );
    }
  };

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!criticalEvent) return;
    setLoading(true);
    try {
      await api.feedback(criticalEvent.id, feedbackType);
      
      // Explicitly record custom notes audit
      await api.recordAudit(
        'SUPERVISOR_DECISION',
        criticalEvent.userId,
        `Supervisor Decision: ${feedbackType}. Notes: ${supervisorNotes || 'None'}`
      );

      setFeedback('Feedback recorded for future model calibration.');
      setCriticalEvent(null);
      setSupervisorNotes('');
      setTimeout(() => setFeedback(null), 5000);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Simulated Containment & Response Center</h1>
          <p className="text-slate-400 font-[Inter]">
            Execute rapid containment actions and provide ML calibration verdicts on privileged threats.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/incident-history')}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg border border-slate-700 transition-colors"
          >
            <History size={14} /> Incident History
          </button>
        </div>
      </div>

      {/* ELEVENLABS VOICE ALERT */}
      <Card className="border-red-500/30 bg-red-950/10">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="text-lg">🔊</div>
              <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                ELEVENLABS VOICE ALERT
              </h2>
            </div>
            <p className="text-xs text-slate-400">
              Generate an audible warning for the current privileged-access security event.
            </p>
          </div>

          <button
            onClick={handleVoiceAlert}
            disabled={voiceLoading}
            className="inline-flex items-center justify-center gap-2 bg-red-600 hover:bg-red-500 text-white px-4 py-2.5 rounded-lg font-bold text-xs transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play size={15} />
            {voiceLoading ? 'Generating Alert...' : 'Play Voice Alert'}
          </button>
        </div>

        {voiceError && (
          <div className="mt-3 text-xs text-red-400 border-t border-red-500/20 pt-3">
            {voiceError}
          </div>
        )}
      </Card>

      {feedback && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-5 py-3.5 rounded-lg flex items-center gap-3 shadow-lg animate-fade-in text-sm font-semibold">
          <CheckCircle2 size={20} className="shrink-0" />
          <span>{feedback}</span>
        </div>
      )}

      {!criticalEvent ? (
        <Card className="text-center py-14 border-slate-800">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-emerald-500/10 text-emerald-400 rounded-full flex items-center justify-center border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.15)]">
              <CheckCircle2 size={32} />
            </div>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mb-2">No Active Threat Waiting in Queue</h2>
          <p className="text-slate-400 max-w-md mx-auto text-sm mb-6">
            All current privileged sessions are within normal parameters. To test and verify response and containment actions, load a high-risk simulation alert below.
          </p>
          <button
            onClick={handleSimulateAttack}
            disabled={loading}
            className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-500 text-white px-6 py-3 rounded-lg font-bold transition-all shadow-[0_0_15px_rgba(239,68,68,0.3)] disabled:opacity-50 text-sm"
          >
            <Zap size={18} />
            {loading ? 'Triggering Incident...' : '⚡ Load Critical PAM Incident (EMP-1042)'}
          </button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="border-red-500/40 bg-red-950/10 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-800">
                <div className="w-11 h-11 bg-red-500/20 text-red-400 rounded-lg flex items-center justify-center border border-red-500/30">
                  <AlertOctagon size={26} />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-red-400">Immediate Containment Required</h2>
                  <p className="text-xs text-slate-400">Critical privileged access chain violation detected.</p>
                </div>
              </div>

              <div className="space-y-3.5 mb-6 text-sm">
                <div className="flex justify-between py-2 border-b border-slate-800/60">
                  <span className="text-slate-400">Event Reference</span>
                  <span className="font-mono text-slate-200 font-semibold">{criticalEvent.id}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-slate-800/60">
                  <span className="text-slate-400">Target Privileged User</span>
                  <span className="font-mono font-bold text-slate-100">{criticalEvent.userId}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-slate-800/60">
                  <span className="text-slate-400">Flagged Privileged Action</span>
                  <span className="font-semibold text-slate-200">{criticalEvent.action}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-slate-800/60">
                  <span className="text-slate-400">Evaluated Risk Level</span>
                  <Badge level={criticalEvent.risk} />
                </div>
                {criticalEvent.amount && (
                  <div className="flex justify-between py-2 border-b border-slate-800/60">
                    <span className="text-slate-400">Transaction Value</span>
                    <span className="font-mono font-bold text-red-400 text-base">₹{criticalEvent.amount.toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-lg border border-slate-700/80">
              <h4 className="font-semibold text-slate-200 text-sm mb-1.5 flex items-center gap-2">
                <ShieldAlert size={16} className="text-amber-400" />
                Response Engine Recommendation
              </h4>
              <p className="text-xs text-slate-300 leading-relaxed font-[Inter]">
                System recommends immediate transaction hold and session restriction due to abnormal payment velocity, unverified offshore beneficiary, and missing dual custody approval.
              </p>
            </div>
          </Card>

          <div className="space-y-6">
            <Card title="Simulated PAM Containment Actions" className="border-slate-800">
              <p className="text-xs text-slate-400 mb-4 font-[Inter]">
                Execute simulated mitigation workflows across the core banking PAM gateway:
              </p>
              <div className="space-y-3 font-semibold text-xs">
                <button 
                  onClick={() => initiateAction('HOLD_PAYMENT')}
                  disabled={loading}
                  className="w-full bg-slate-800 hover:bg-slate-800 border border-slate-700 hover:border-red-500 text-slate-100 py-3 px-4 rounded-lg font-bold transition-all disabled:opacity-50 flex items-center justify-between text-left"
                >
                  <span>[ HOLD PAYMENT — SIMULATION ]</span>
                  <span className="text-[10px] text-slate-500 font-mono">Simulated Response</span>
                </button>
                <button 
                  onClick={() => initiateAction('RESTRICT_SESSION')}
                  disabled={loading}
                  className="w-full bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-red-500 text-slate-100 py-3 px-4 rounded-lg font-bold transition-all disabled:opacity-50 flex items-center justify-between text-left"
                >
                  <span>[ RESTRICT SESSION — SIMULATION ]</span>
                  <span className="text-[10px] text-slate-500 font-mono">Simulated Response</span>
                </button>
                <button 
                  onClick={() => initiateAction('ESCALATE')}
                  disabled={loading}
                  className="w-full bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-amber-500 text-slate-100 py-3 px-4 rounded-lg font-bold transition-all disabled:opacity-50 flex items-center justify-between text-left"
                >
                  <span>[ ESCALATE INCIDENT ]</span>
                  <span className="text-[10px] text-slate-500 font-mono">Forward to SOC</span>
                </button>
                <button 
                  onClick={() => initiateAction('VERIFY')}
                  disabled={loading}
                  className="w-full bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-blue-500 text-slate-100 py-3 px-4 rounded-lg font-bold transition-all disabled:opacity-50 flex items-center justify-between text-left"
                >
                  <span>[ REQUEST ADDITIONAL VERIFICATION ]</span>
                  <span className="text-[10px] text-slate-500 font-mono">MFA Prompt</span>
                </button>
              </div>
            </Card>

            <Card title="Analyst Feedback Loop" className="border-slate-800">
              <form onSubmit={handleFeedbackSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Decision Verdict
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { type: 'TRUE_POSITIVE', label: 'CONFIRM TRUE POSITIVE' },
                      { type: 'FALSE_POSITIVE', label: 'FALSE POSITIVE' },
                      { type: 'NEEDS_REVIEW', label: 'NEEDS REVIEW' },
                    ].map((opt) => (
                      <button
                        type="button"
                        key={opt.type}
                        onClick={() => setFeedbackType(opt.type)}
                        className={`py-2 px-1 rounded-lg border text-[10px] font-bold text-center transition-all ${
                          feedbackType === opt.type
                            ? 'bg-primary/10 text-primary border-primary/40 ring-1 ring-primary/20'
                            : 'bg-darker text-slate-400 border-slate-750 hover:text-slate-350 hover:bg-slate-800/40'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label htmlFor="notes" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Supervisor Notes (Optional)
                  </label>
                  <textarea
                    id="notes"
                    rows={3}
                    placeholder="Enter security audit notes, findings, and justifications here..."
                    className="w-full bg-darker border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-primary placeholder-slate-600 font-[Inter] resize-none"
                    value={supervisorNotes}
                    onChange={(e) => setSupervisorNotes(e.target.value)}
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-primary hover:bg-primaryDark text-darker font-bold py-2 px-4 rounded-lg text-xs uppercase tracking-wider transition-colors disabled:opacity-50"
                >
                  Submit Decision Verdict
                </button>
              </form>
            </Card>
          </div>
        </div>
      )}

      {/* CONFIRMATION MODAL */}
      {showConfirmModal && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-50 p-4 font-[Inter]">
          <div className="w-full max-w-sm bg-panel border border-slate-800 rounded-xl p-5 shadow-2xl space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <HelpCircle className="text-amber-500 animate-pulse" size={20} />
              <h3 className="font-bold text-sm text-slate-100 uppercase tracking-wider">CONFIRM SIMULATED RESPONSE</h3>
            </div>
            
            <p className="text-xs text-slate-300 leading-relaxed">
              {confirmMessage}
            </p>

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 py-2 rounded text-xs font-bold transition-all border border-slate-700"
              >
                CANCEL
              </button>
              <button
                onClick={confirmAction}
                className="flex-1 bg-red-600 hover:bg-red-500 text-white py-2 rounded text-xs font-bold transition-all"
              >
                CONFIRM
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
