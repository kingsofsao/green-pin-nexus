from ..services.elevenlabs_service import generate_security_alert_audio
from fastapi import HTTPException
from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from ..database import get_db
from ..models.schemas import (
    DemoRequest, DashboardData, GraphData, ResponseAction, FeedbackRequest,
    LoginRequest, AuditLogEntry, RecordAuditRequest
)
from pydantic import BaseModel
from ..services.demo_service import DemoService
from ..detection.risk_engine import RiskEngine
import sqlite3
import json
import uuid
import bcrypt
from datetime import datetime, timedelta

router = APIRouter()
demo_service = DemoService()

def db_conn():
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()

def insert_audit_log(conn: sqlite3.Connection, supervisor_id: str, action: str, target: str = None, details: str = None):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (id, supervisor_id, action, target, timestamp, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), supervisor_id, action, target, datetime.now().isoformat(), details))
    conn.commit()

def check_lockout(conn: sqlite3.Connection, email_or_id: str) -> tuple[bool, str]:
    cursor = conn.cursor()
    cursor.execute("SELECT attempts, locked_until FROM login_attempts WHERE email = ?", (email_or_id,))
    row = cursor.fetchone()
    if row:
        attempts, locked_until = row['attempts'], row['locked_until']
        if attempts >= 5 and locked_until:
            try:
                locked_until_dt = datetime.fromisoformat(locked_until)
                if datetime.now() < locked_until_dt:
                    return True, "Too many failed authentication attempts. Please try again shortly."
                else:
                    cursor.execute("UPDATE login_attempts SET attempts = 0, locked_until = NULL WHERE email = ?", (email_or_id,))
                    conn.commit()
            except Exception:
                pass
    return False, ""

def record_failed_attempt(conn: sqlite3.Connection, email_or_id: str):
    cursor = conn.cursor()
    cursor.execute("SELECT attempts FROM login_attempts WHERE email = ?", (email_or_id,))
    row = cursor.fetchone()
    if row:
        attempts = row['attempts'] + 1
        locked_until = None
        if attempts >= 5:
            locked_until = (datetime.now() + timedelta(seconds=30)).isoformat()
        cursor.execute("UPDATE login_attempts SET attempts = ?, last_attempt = ?, locked_until = ? WHERE email = ?",
                       (attempts, datetime.now().isoformat(), locked_until, email_or_id))
    else:
        cursor.execute("INSERT INTO login_attempts (email, attempts, last_attempt, locked_until) VALUES (?, 1, ?, NULL)",
                       (email_or_id, datetime.now().isoformat()))
    conn.commit()

def reset_attempts(conn: sqlite3.Connection, email_or_id: str):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM login_attempts WHERE email = ?", (email_or_id,))
    conn.commit()

@router.get("/health")
def get_health():
    return {
        "status": "ok",
        "service": "GREEN PIN NEXUS",
        "engines": {
            "behavior_engine": "ONLINE",
            "sequence_engine": "ONLINE",
            "context_engine": "ONLINE",
            "risk_engine": "ONLINE",
            "response_engine": "ONLINE"
        }
    }

@router.get("/dashboard", response_model=DashboardData)
def get_dashboard(conn: sqlite3.Connection = Depends(db_conn)):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]
    
    cursor.execute("SELECT category, COUNT(*) FROM risk_scores GROUP BY category")
    risk_dist = {"LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0}
    for row in cursor.fetchall():
        if row[0]:
            risk_dist[row[0]] = row[1]
    
    cursor.execute("SELECT e.*, r.category as risk FROM events e LEFT JOIN risk_scores r ON e.user_id = r.user_id ORDER BY e.timestamp DESC LIMIT 10")
    recent = []
    for r in cursor.fetchall():
        d = dict(r)
        details = {}
        try:
            details = json.loads(d.get('details', '{}'))
        except Exception:
            pass
        recent.append({
            "id": d["id"],
            "userId": d["user_id"],
            "action": d["action"],
            "risk": d.get("risk") or "LOW",
            "status": "ALLOWED",
            "timestamp": d["timestamp"],
            "amount": details.get("amount")
        })

    cursor.execute("SELECT COUNT(*) FROM responses")
    actions_held = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE verdict = 'TRUE_POSITIVE' OR verdict = 'CONFIRMED'")
    confirmed_incidents = cursor.fetchone()[0]

    return DashboardData(
        overview_kpis={
            "total_users": total_users,
            "total_events": total_events,
            "active_alerts": risk_dist.get("HIGH", 0) + risk_dist.get("CRITICAL", 0),
            "critical_incidents": risk_dist.get("CRITICAL", 0),
            "actions_held": actions_held,
            "confirmed_incidents": confirmed_incidents
        },
        risk_distribution=risk_dist,
        system_status="Operational",
        recentEvents=recent
    )

@router.get("/events")
def get_events(conn: sqlite3.Connection = Depends(db_conn)):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.*, r.category as risk, r.score as risk_score, u.role as role, u.privilege_level as privilege_level
        FROM events e 
        LEFT JOIN risk_scores r ON e.user_id = r.user_id 
        LEFT JOIN users u ON e.user_id = u.id
        ORDER BY e.timestamp DESC LIMIT 150
    """)
    rows = cursor.fetchall()
    events_list = []
    for r in rows:
        d = dict(r)
        details = {}
        try:
            details = json.loads(d.get('details', '{}'))
        except Exception:
            pass
        
        status = "ALLOWED"
        if d.get("risk") == "CRITICAL":
            status = "HELD" if "PAYMENT" in d.get("action", "") else "FLAGGED"
        elif d.get("risk") == "HIGH":
            status = "FLAGGED"

        events_list.append({
            "id": d["id"],
            "userId": d["user_id"],
            "role": d.get("role") or "Privileged Staff",
            "privilege": d.get("privilege_level") or "HIGH",
            "action": d["action"],
            "resource": details.get("account_id") or "CORE_BANKING_LEDGER",
            "beneficiary": details.get("beneficiary_id") or "BEN-STANDARD",
            "amount": details.get("amount"),
            "risk": d.get("risk") or "LOW",
            "riskScore": d.get("risk_score") or 10,
            "status": status,
            "timestamp": d["timestamp"],
            "device": d.get("device_id") or "ADMIN-WS-01",
            "location": d.get("location") or "Mumbai HQ"
        })
    return {"events": events_list}

@router.get("/events/{event_id}")
def get_event(event_id: str, conn: sqlite3.Connection = Depends(db_conn)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    d = dict(row)
    try:
        d['details'] = json.loads(d.get('details', '{}'))
    except Exception:
        pass
    return d

@router.get("/users")
def get_users(conn: sqlite3.Connection = Depends(db_conn)):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.*, COALESCE(r.score, 12.0) as score, COALESCE(r.category, 'LOW') as category,
               COALESCE(r.breakdown, '{}') as breakdown, COALESCE(r.explanations, '[]') as explanations
        FROM users u 
        LEFT JOIN risk_scores r ON u.id = r.user_id
        ORDER BY score DESC
    """)
    users = []
    for r in cursor.fetchall():
        d = dict(r)
        breakdown = {}
        explanations = []
        try:
            breakdown = json.loads(d.get('breakdown', '{}'))
        except Exception:
            pass
        try:
            explanations = json.loads(d.get('explanations', '[]'))
        except Exception:
            pass
            
        users.append({
            "id": d["id"],
            "name": d["name"],
            "role": d["role"],
            "department": d["department"],
            "privilege": d["privilege_level"],
            "peerGroup": d["peer_group"],
            "workingHours": d["working_hours"],
            "riskScore": d["score"],
            "category": d["category"],
            "behaviorRisk": int(breakdown.get("behavioral", 12)),
            "sequenceRisk": int(breakdown.get("sequence", 10)),
            "financialRisk": int(breakdown.get("financial", 10)),
            "contextRisk": int(breakdown.get("context", 10)),
            "explanations": explanations
        })
    return users

@router.get("/users/{user_id}")
def get_user(user_id: str, conn: sqlite3.Connection = Depends(db_conn)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)

@router.get("/risk/{user_id}")
def get_risk(user_id: str, conn: sqlite3.Connection = Depends(db_conn)):
    insert_audit_log(conn, "SUP-001", "ALERT_VIEWED", user_id, f"Viewed risk profile for user {user_id}")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM risk_scores WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        return {
            "userId": user_id,
            "score": 15,
            "category": "LOW",
            "factors": ["Activity strictly aligns with historical peer baseline"],
            "details": {
                "geoRisk": 10,
                "timeRisk": 5,
                "actionRisk": 15,
                "financialRisk": 10,
                "privilegeRisk": 10
            }
        }
        
    res = dict(row)
    breakdown = {}
    explanations = []
    try:
        breakdown = json.loads(res.get('breakdown', '{}'))
    except Exception:
        pass
    try:
        explanations = json.loads(res.get('explanations', '[]'))
    except Exception:
        pass
        
    return {
        "userId": user_id,
        "score": res.get("score", 0),
        "category": res.get("category", "LOW"),
        "factors": explanations if explanations else ["Standard baseline behavior"],
        "details": {
            "geoRisk": int(breakdown.get("behavioral", 15)),
            "timeRisk": int(breakdown.get("context", 10)),
            "actionRisk": int(breakdown.get("sequence", 20)),
            "financialRisk": int(breakdown.get("financial", 10)),
            "privilegeRisk": int(breakdown.get("privilege", 10))
        }
    }

@router.get("/timeline/{scenario}")
def get_timeline(scenario: str, conn: sqlite3.Connection = Depends(db_conn)):
    scenario_clean = scenario.lower()
    
    if scenario_clean in ["attack", "compromised"]:
        events = [
            {
                "id": "EVT-ATTACK-1",
                "timestamp": "2026-08-28T11:42:00",
                "userId": "EMP-1042",
                "action": "LOGIN",
                "amount": None,
                "risk": "LOW",
                "cumulativeScore": 15,
                "context": "User logged in during regular hours from recognized internal workstation."
            },
            {
                "id": "EVT-ATTACK-2",
                "timestamp": "2026-08-28T11:44:00",
                "userId": "EMP-1042",
                "action": "BENEFICIARY_MODIFIED",
                "amount": None,
                "risk": "MODERATE",
                "cumulativeScore": 42,
                "context": "Added new unverified beneficiary BEN-0771 without peer verification."
            },
            {
                "id": "EVT-ATTACK-3",
                "timestamp": "2026-08-28T11:46:00",
                "userId": "EMP-1042",
                "action": "TRANSACTION_LIMIT_CHANGED",
                "amount": None,
                "risk": "HIGH",
                "cumulativeScore": 68,
                "context": "Escalated daily transfer limit on account ACC-5521 from ₹50,000 to ₹10,00,000."
            },
            {
                "id": "EVT-ATTACK-4",
                "timestamp": "2026-08-28T11:49:00",
                "userId": "EMP-1042",
                "action": "PAYMENT_INITIATED",
                "amount": 850000.0,
                "risk": "CRITICAL",
                "cumulativeScore": 96,
                "context": "Initiated payment of ₹8,50,000 to newly created beneficiary BEN-0771."
            },
            {
                "id": "EVT-ATTACK-5",
                "timestamp": "2026-08-28T11:50:00",
                "userId": "EMP-1042",
                "action": "REQUIRED_APPROVAL_MISSING",
                "amount": None,
                "risk": "CRITICAL",
                "cumulativeScore": 98,
                "context": "Mandatory dual-custody approval step bypassed or missing."
            },
            {
                "id": "EVT-ATTACK-6",
                "timestamp": "2026-08-28T11:51:00",
                "userId": "EMP-1042",
                "action": "NO_BUSINESS_CONTEXT",
                "amount": None,
                "risk": "CRITICAL",
                "cumulativeScore": 99,
                "context": "No matching Jira ticket, change request, or incident authorization found."
            }
        ]
        return {"events": events}
        
    elif scenario_clean in ["emergency", "legitimate_exception"]:
        events = [
            {
                "id": "EVT-EMERG-1",
                "timestamp": "2026-08-28T02:15:00",
                "userId": "EMP-1098",
                "action": "LOGIN",
                "amount": None,
                "risk": "MODERATE",
                "cumulativeScore": 55,
                "context": "Off-hours login detected at 02:15 AM (Initial anomaly flag)."
            },
            {
                "id": "EVT-EMERG-2",
                "timestamp": "2026-08-28T02:18:00",
                "userId": "EMP-1098",
                "action": "DATABASE_QUERY",
                "amount": None,
                "risk": "HIGH",
                "cumulativeScore": 72,
                "context": "High-volume schema queries executed on production core DB."
            },
            {
                "id": "EVT-EMERG-3",
                "timestamp": "2026-08-28T02:22:00",
                "userId": "EMP-1098",
                "action": "PERMISSION_CHANGED",
                "amount": None,
                "risk": "MODERATE",
                "cumulativeScore": 45,
                "context": "Validated against Active Incident INC-1029 and Ticket TKT-5567. Risk reduced."
            },
            {
                "id": "EVT-EMERG-4",
                "timestamp": "2026-08-28T02:25:00",
                "userId": "EMP-1098",
                "action": "MAINTENANCE_COMPLETED",
                "amount": None,
                "risk": "LOW",
                "cumulativeScore": 25,
                "context": "Emergency database failover complete. Context successfully verified."
            }
        ]
        return {"events": events}
        
    else:
        events = [
            {
                "id": "EVT-NORM-1",
                "timestamp": "2026-08-28T09:30:00",
                "userId": "EMP-1002",
                "action": "LOGIN",
                "amount": None,
                "risk": "LOW",
                "cumulativeScore": 10,
                "context": "Routine morning authentication from registered laptop."
            },
            {
                "id": "EVT-NORM-2",
                "timestamp": "2026-08-28T10:15:00",
                "userId": "EMP-1002",
                "action": "VIEW_ACCOUNT",
                "amount": None,
                "risk": "LOW",
                "cumulativeScore": 12,
                "context": "Standard account reconciliation query."
            },
            {
                "id": "EVT-NORM-3",
                "timestamp": "2026-08-28T11:00:00",
                "userId": "EMP-1002",
                "action": "PAYMENT_INITIATED",
                "amount": 25000.0,
                "risk": "LOW",
                "cumulativeScore": 18,
                "context": "Scheduled vendor disbursement with existing dual authorization."
            }
        ]
        return {"events": events}

@router.get("/graph/{scenario}", response_model=GraphData)
def get_graph(scenario: str, conn: sqlite3.Connection = Depends(db_conn)):
    scenario_clean = scenario.lower()
    
    if scenario_clean in ["attack", "compromised"]:
        nodes = [
            {"id": "user-1042", "type": "default", "data": {"label": "EMP-1042 (Arun Kumar)\nSr Payment Admin\nPrivilege: HIGH"}, "position": {"x": 50, "y": 150}, "style": {"background": "#ef4444", "color": "#fff", "border": "2px solid #b91c1c", "borderRadius": "8px", "padding": "12px", "fontSize": "13px", "fontWeight": "bold"}},
            {"id": "acc-5521", "type": "default", "data": {"label": "Account ACC-5521\nLimit Raised: ₹10L\nDept: Payment Ops"}, "position": {"x": 320, "y": 40}, "style": {"background": "#f59e0b", "color": "#1e293b", "border": "2px solid #d97706", "borderRadius": "8px", "padding": "12px", "fontSize": "13px", "fontWeight": "bold"}},
            {"id": "ben-0771", "type": "default", "data": {"label": "Beneficiary BEN-0771\n(New / Unverified Offshore)\nCreated: 11:44"}, "position": {"x": 320, "y": 260}, "style": {"background": "#ef4444", "color": "#fff", "border": "2px solid #b91c1c", "borderRadius": "8px", "padding": "12px", "fontSize": "13px", "fontWeight": "bold"}},
            {"id": "txn-9281", "type": "default", "data": {"label": "Transaction TXN-9281\n₹8,50,000\nBaseline Exceeded 17x"}, "position": {"x": 600, "y": 150}, "style": {"background": "#991b1b", "color": "#fff", "border": "2px solid #7f1d1d", "borderRadius": "8px", "padding": "12px", "fontSize": "13px", "fontWeight": "bold"}},
            {"id": "appr-missing", "type": "default", "data": {"label": "Approval: MISSING\nTicket: NONE FOUND\nContext Risk: 100%"}, "position": {"x": 880, "y": 150}, "style": {"background": "#1e293b", "color": "#f87171", "border": "2px dashed #ef4444", "borderRadius": "8px", "padding": "12px", "fontSize": "13px", "fontWeight": "bold"}}
        ]
        edges = [
            {"id": "e1", "source": "user-1042", "target": "acc-5521", "label": "CHANGES_LIMIT", "animated": True, "style": {"stroke": "#f59e0b", "strokeWidth": 2}},
            {"id": "e2", "source": "user-1042", "target": "ben-0771", "label": "MODIFIES_BENEFICIARY", "animated": True, "style": {"stroke": "#ef4444", "strokeWidth": 2}},
            {"id": "e3", "source": "acc-5521", "target": "txn-9281", "label": "DEBIT_SOURCE", "style": {"stroke": "#94a3b8", "strokeWidth": 2}},
            {"id": "e4", "source": "ben-0771", "target": "txn-9281", "label": "CREDIT_DESTINATION", "style": {"stroke": "#ef4444", "strokeWidth": 2}},
            {"id": "e5", "source": "txn-9281", "target": "appr-missing", "label": "UNAUTHORIZED_EXECUTION", "animated": True, "style": {"stroke": "#ef4444", "strokeWidth": 3}}
        ]
    elif scenario_clean in ["emergency", "legitimate_exception"]:
        nodes = [
            {"id": "user-1098", "type": "default", "data": {"label": "EMP-1098 (Priya Sharma)\nDatabase Administrator\nPrivilege: HIGH"}, "position": {"x": 50, "y": 150}, "style": {"background": "#3b82f6", "color": "#fff", "borderRadius": "8px", "padding": "12px", "fontWeight": "bold"}},
            {"id": "tkt-5567", "type": "default", "data": {"label": "Ticket TKT-5567\nDB Failover Emergency\nStatus: APPROVED"}, "position": {"x": 320, "y": 40}, "style": {"background": "#10b981", "color": "#fff", "borderRadius": "8px", "padding": "12px", "fontWeight": "bold"}},
            {"id": "inc-1029", "type": "default", "data": {"label": "Incident INC-1029\nProduction Outage Sev-1\nActive Window: 02:00-04:00"}, "position": {"x": 320, "y": 260}, "style": {"background": "#10b981", "color": "#fff", "borderRadius": "8px", "padding": "12px", "fontWeight": "bold"}},
            {"id": "db-core", "type": "default", "data": {"label": "Core Cluster DB\nReplication Failover\nContext Validated"}, "position": {"x": 600, "y": 150}, "style": {"background": "#6366f1", "color": "#fff", "borderRadius": "8px", "padding": "12px", "fontWeight": "bold"}}
        ]
        edges = [
            {"id": "e1", "source": "user-1098", "target": "tkt-5567", "label": "REFERENCED_BY", "style": {"stroke": "#10b981", "strokeWidth": 2}},
            {"id": "e2", "source": "user-1098", "target": "inc-1029", "label": "ASSIGNED_ENGINEER", "style": {"stroke": "#10b981", "strokeWidth": 2}},
            {"id": "e3", "source": "user-1098", "target": "db-core", "label": "PERFORMS_FAILOVER", "style": {"stroke": "#3b82f6", "strokeWidth": 2}}
        ]
    else:
        nodes = [
            {"id": "user-1002", "type": "default", "data": {"label": "EMP-1002 (Karan Verma)\nPayment Analyst\nPrivilege: MEDIUM"}, "position": {"x": 100, "y": 150}, "style": {"background": "#10b981", "color": "#fff", "borderRadius": "8px", "padding": "12px", "fontWeight": "bold"}},
            {"id": "acc-101", "type": "default", "data": {"label": "Account ACC-101\nStandard Disbursement\nStatus: NORMAL"}, "position": {"x": 380, "y": 150}, "style": {"background": "#334155", "color": "#fff", "borderRadius": "8px", "padding": "12px", "fontWeight": "bold"}},
            {"id": "ben-201", "type": "default", "data": {"label": "Beneficiary BEN-201\nVerified Corporate Vendor\nApproved Supplier"}, "position": {"x": 660, "y": 150}, "style": {"background": "#10b981", "color": "#fff", "borderRadius": "8px", "padding": "12px", "fontWeight": "bold"}}
        ]
        edges = [
            {"id": "e1", "source": "user-1002", "target": "acc-101", "label": "STANDARD_ACCESS", "style": {"stroke": "#10b981", "strokeWidth": 2}},
            {"id": "e2", "source": "acc-101", "target": "ben-201", "label": "RECURRING_PAYMENT", "style": {"stroke": "#10b981", "strokeWidth": 2}}
        ]
    return GraphData(nodes=nodes, edges=edges)

@router.get("/context/{event_id}")
def get_context(event_id: str, conn: sqlite3.Connection = Depends(db_conn)):
    insert_audit_log(conn, "SUP-001", "INVESTIGATION_OPENED", event_id, f"Investigated details for event {event_id}")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.*, r.category as risk, r.score as risk_score, r.breakdown, r.explanations 
        FROM events e 
        LEFT JOIN risk_scores r ON e.user_id = r.user_id 
        WHERE e.id = ?
    """, (event_id,))
    row = cursor.fetchone()
    
    if not row:
        return {
            "event": {
                "id": event_id or "EVT-ATTACK-4",
                "userId": "EMP-1042",
                "action": "PAYMENT_INITIATED",
                "amount": 850000,
                "risk": "CRITICAL",
                "timestamp": datetime.now().isoformat()
            },
            "explanation": "WHY WAS THIS FLAGGED? 1. Transaction amount (₹8,50,000) significantly deviates from normal range (₹5,000–₹50,000). 2. Transaction limit increased right before payment. 3. New unverified beneficiary BEN-0771. 4. Required dual approval missing. 5. No supporting business ticket or maintenance window found.",
            "evidence": [
                "1. Transaction amount is significantly above the user's normal range (₹5,000–₹50,000).",
                "2. Beneficiary BEN-0771 is unfamiliar and was added < 5 minutes prior.",
                "3. Transaction limit was increased on ACC-5521 shortly before payment.",
                "4. Required dual-custody approval is MISSING.",
                "5. No supporting business ticket (Jira/ITSM) was found.",
                "6. Action sequence deviates from expected baseline workflow."
            ],
            "isLegitimateException": False
        }
        
    d = dict(row)
    details = {}
    try:
        details = json.loads(d.get('details', '{}'))
    except Exception:
        pass
        
    is_emergency_user = (d.get("user_id") == "EMP-1098")
    
    if is_emergency_user:
        return {
            "event": {
                "id": d["id"],
                "userId": d["user_id"],
                "action": d["action"],
                "amount": details.get("amount"),
                "risk": "MODERATE",
                "timestamp": d["timestamp"]
            },
            "explanation": "EMERGENCY MAINTENANCE DETECTED: Initial off-hours anomaly is mitigated by matching active Incident INC-1029, approved Ticket TKT-5567, and authorized Database Administrator role during an emergency failover window.",
            "evidence": [
                "Incident INC-1029: Production Failover (ACTIVE)",
                "Ticket TKT-5567: Emergency DB Maintenance (APPROVED)",
                "Maintenance Window: ACTIVE (02:00–04:00 AM)",
                "Authorized Role: Database Administrator (VERIFIED)",
                "Business Justification: DATABASE FAILOVER"
            ],
            "isLegitimateException": True,
            "exceptionReason": "Context validation confirms legitimate emergency operation. Risk downgraded to MODERATE (Recommended: VERIFY + MONITOR)."
        }
        
    return {
        "event": {
            "id": d["id"],
            "userId": d["user_id"],
            "action": d["action"],
            "amount": details.get("amount"),
            "risk": d.get("risk") or "LOW",
            "timestamp": d["timestamp"]
        },
        "explanation": "Action sequence evaluated against behavioral baseline, privilege level, and enterprise context records.",
        "evidence": [
            f"User ID: {d.get('user_id')}",
            f"Action: {d.get('action')}",
            f"Device: {d.get('device_id') or 'ADMIN-WS-01'}",
            "Sequence Analysis: Workflow continuity verified"
        ],
        "isLegitimateException": False
    }

@router.get("/responses")
def get_responses(conn: sqlite3.Connection = Depends(db_conn)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM responses ORDER BY timestamp DESC LIMIT 50")
    return [dict(r) for r in cursor.fetchall()]

@router.get("/feedback")
def get_feedback(conn: sqlite3.Connection = Depends(db_conn)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM analyst_feedback ORDER BY timestamp DESC LIMIT 50")
    return [dict(r) for r in cursor.fetchall()]

@router.post("/demo")
@router.post("/demo/run")
def run_demo(req: DemoRequest):
    scenario = req.scenario.lower()
    if scenario in ["normal"]:
        demo_service.run_normal_scenario()
    elif scenario in ["attack", "compromised"]:
        demo_service.run_attack_scenario()
    elif scenario in ["emergency", "legitimate_exception"]:
        demo_service.run_emergency_scenario()
    elif scenario in ["reset"]:
        demo_service.reset_demo()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {req.scenario}")
    return {"status": "success", "scenario": req.scenario}

@router.post("/response")
@router.post("/respond")
def post_response(req: ResponseAction, conn: sqlite3.Connection = Depends(db_conn)):
    cursor = conn.cursor()
    event_id = req.event_id or req.eventId or "EVT-SIM-9281"
    cursor.execute("INSERT INTO responses (id, event_id, action, timestamp) VALUES (?, ?, ?, ?)",
                   (str(uuid.uuid4()), event_id, req.action, datetime.now().isoformat()))
    conn.commit()
    
    # Audit log
    insert_audit_log(conn, "SUP-001", "SIMULATED_RESPONSE", req.action, f"Executed response action for event {event_id}")
    
    return {"status": "success", "action": req.action, "simulation": True, "timestamp": datetime.now().isoformat()}

@router.post("/feedback")
def post_feedback(req: FeedbackRequest, conn: sqlite3.Connection = Depends(db_conn)):
    cursor = conn.cursor()
    event_id = req.event_id or req.eventId or "EVT-FEEDBACK"
    user_id = req.user_id or req.userId or "EMP-1042"
    verdict = req.verdict or req.type or "CONFIRMED"
    cursor.execute("""
        INSERT INTO analyst_feedback (id, event_id, user_id, analyst, verdict, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), event_id, user_id, req.analyst or "SOC Analyst", verdict, "Analyst review recorded", datetime.now().isoformat()))
    conn.commit()
    
    # Audit log
    insert_audit_log(conn, "SUP-001", "SUPERVISOR_DECISION", verdict, f"Verdict: {verdict} for user {user_id}")
    
    return {
        "status": "success",
        "feedback": verdict,
        "message": "Feedback captured for future rule and baseline refinement.",
        "timestamp": datetime.now().isoformat()
    }

class SessionActionRequest(BaseModel):
    supervisor_id: str

@router.post("/auth/login")
def login(req: LoginRequest, conn: sqlite3.Connection = Depends(db_conn)):
    is_locked, err_msg = check_lockout(conn, req.email_or_id)
    if is_locked:
        insert_audit_log(conn, "UNKNOWN", "LOGIN_FAILURE", req.email_or_id, "Lockout active")
        raise HTTPException(status_code=403, detail=err_msg)

    # Password policy check
    pw = req.password
    has_upper = any(c.isupper() for c in pw)
    has_lower = any(c.islower() for c in pw)
    has_digit = any(c.isdigit() for c in pw)
    has_special = any(not c.isalnum() for c in pw)
    if len(pw) < 8 or not (has_upper and has_lower and has_digit and has_special):
        record_failed_attempt(conn, req.email_or_id)
        insert_audit_log(conn, "UNKNOWN", "LOGIN_FAILURE", req.email_or_id, "Password policy violation")
        raise HTTPException(
            status_code=401,
            detail="AUTHENTICATION FAILED: Invalid supervisor credentials. Please verify your login details."
        )

    clean_id = req.email_or_id.strip()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM supervisors WHERE LOWER(id) = LOWER(?) OR LOWER(email) = LOWER(?)", (clean_id, clean_id))
    supervisor_row = cursor.fetchone()

    if not supervisor_row:
        record_failed_attempt(conn, req.email_or_id)
        insert_audit_log(conn, "UNKNOWN", "LOGIN_FAILURE", req.email_or_id, "Supervisor not found")
        raise HTTPException(
            status_code=401,
            detail="AUTHENTICATION FAILED: Invalid supervisor credentials. Please verify your login details."
        )

    sup = dict(supervisor_row)
    pw_hash = sup['password_hash'].encode('utf-8')
    if not bcrypt.checkpw(pw.encode('utf-8'), pw_hash):
        record_failed_attempt(conn, req.email_or_id)
        insert_audit_log(conn, sup['id'], "LOGIN_FAILURE", req.email_or_id, "Incorrect password")
        raise HTTPException(
            status_code=401,
            detail="AUTHENTICATION FAILED: Invalid supervisor credentials. Please verify your login details."
        )

    # Success
    reset_attempts(conn, req.email_or_id)
    insert_audit_log(conn, sup['id'], "LOGIN_SUCCESS", sup['id'], "Authentication verified")
    
    return {
        "status": "success",
        "supervisor": {
            "id": sup['id'],
            "name": sup['name'],
            "role": sup['role'],
            "email": sup['email']
        }
    }

@router.post("/auth/logout")
def logout(req: SessionActionRequest, conn: sqlite3.Connection = Depends(db_conn)):
    insert_audit_log(conn, req.supervisor_id, "LOGOUT", req.supervisor_id, "Supervisor logged out")
    return {"status": "success"}

@router.post("/auth/session_expire")
def session_expire(req: SessionActionRequest, conn: sqlite3.Connection = Depends(db_conn)):
    insert_audit_log(conn, req.supervisor_id, "SESSION_EXPIRED", req.supervisor_id, "Supervisor session expired due to inactivity")
    return {"status": "success"}

@router.get("/audit")
def get_audit_logs(conn: sqlite3.Connection = Depends(db_conn)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 100")
    return [dict(row) for row in cursor.fetchall()]

@router.post("/audit/record")
def record_audit(req: RecordAuditRequest, conn: sqlite3.Connection = Depends(db_conn)):
    insert_audit_log(conn, "SUP-001", req.action, req.target, req.details)
    return {"status": "success"}


class VoiceAlertRequest(BaseModel):
    text: str
    voice_id: str | None = None


@router.post("/security-alert/voice")
async def security_alert_voice(request: VoiceAlertRequest):
    text = request.text.strip()

    if not text:
        raise HTTPException(status_code=400, detail="Alert text cannot be empty.")

    if len(text) > 1000:
        raise HTTPException(status_code=400, detail="Alert text is too long.")

    audio = await generate_security_alert_audio(
        text=text,
        voice_id=request.voice_id,
    )

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="security-alert.mp3"',
            "Cache-Control": "no-store",
        },
    )
