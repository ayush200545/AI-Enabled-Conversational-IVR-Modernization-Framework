# ============================================================
#  dashboard.py — MILESTONE 2: Feature 5
#  Configuration & Live Admin Dashboard
#  Visit: http://localhost:8000/dashboard
# ============================================================

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from datetime import datetime
import database as db

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    stats = db.get_stats()

    # ── Build bed cards ──────────────────────────────────────
    bed_cards = ""
    for dept, data in db.bed_data.items():
        available = data["available"]
        total     = data["total"]
        occupied  = total - available
        pct       = int((available / total) * 100)
        icon      = data["icon"]

        if pct > 50:
            status_class = "good"
            status_label = "Available"
        elif pct > 20:
            status_class = "warn"
            status_label = "Limited"
        else:
            status_class = "critical"
            status_label = "Critical"

        # Arc fill for donut
        arc_pct = pct

        bed_cards += f"""
        <div class="bed-card {status_class}">
            <div class="bed-header">
                <span class="dept-icon">{icon}</span>
                <div>
                    <div class="dept-name">{dept.upper()}</div>
                    <div class="status-badge {status_class}">{status_label}</div>
                </div>
            </div>
            <div class="bed-donut">
                <svg viewBox="0 0 36 36" class="donut-svg">
                    <circle class="donut-track" cx="18" cy="18" r="15.9"/>
                    <circle class="donut-fill {status_class}" cx="18" cy="18" r="15.9"
                        stroke-dasharray="{arc_pct} {100 - arc_pct}"
                        stroke-dashoffset="25"/>
                </svg>
                <div class="donut-center">
                    <span class="donut-number">{available}</span>
                    <span class="donut-label">free</span>
                </div>
            </div>
            <div class="bed-stats">
                <div class="bed-stat">
                    <span class="stat-val">{total}</span>
                    <span class="stat-key">Total</span>
                </div>
                <div class="bed-stat">
                    <span class="stat-val" style="color:var(--good)">{available}</span>
                    <span class="stat-key">Free</span>
                </div>
                <div class="bed-stat">
                    <span class="stat-val" style="color:var(--critical)">{occupied}</span>
                    <span class="stat-key">Occupied</span>
                </div>
            </div>
        </div>"""

    # ── Build call log rows ──────────────────────────────────
    log_rows = ""
    logs_to_show = list(reversed(db.call_logs[-15:]))

    if not logs_to_show:
        log_rows = """
        <tr class="empty-row">
            <td colspan="6">
                <div class="empty-state">📵 No calls yet — waiting for first call...</div>
            </td>
        </tr>"""
    else:
        for i, log in enumerate(logs_to_show):
            status = log.get("status", "")
            action = log.get("action", "")

            if status in ["confirmed", "connected", "checked", "alerted"]:
                badge_class = "badge-success"
            elif status in ["error", "no_beds"]:
                badge_class = "badge-error"
            else:
                badge_class = "badge-info"

            action_icons = {
                "incoming_call":       "📞",
                "admission":           "🏥",
                "bed_check":           "🛏️",
                "emergency":           "🚨",
                "transfer_reception":  "📲",
                "selected_admission":  "➡️",
                "selected_bed_check":  "➡️",
                "invalid_input":       "⚠️",
            }
            icon = action_icons.get(action, "•")

            pid = log.get("patient_id", "—")
            pid_html = f'<span class="patient-id">{pid}</span>' if pid != "—" else '<span class="dash">—</span>'

            fade_style = f"animation-delay: {i * 0.05}s"

            log_rows += f"""
            <tr style="{fade_style}" class="log-row">
                <td><span class="time-badge">{log.get('time','')}</span></td>
                <td><span class="caller-num">{log.get('caller','')}</span></td>
                <td>{icon} {action.replace('_', ' ').title()}</td>
                <td><span class="dept-pill">{log.get('department','—')}</span></td>
                <td><span class="badge {badge_class}">{status}</span></td>
                <td>{pid_html}</td>
            </tr>"""

    # ── Config checklist ─────────────────────────────────────
    config_items = [
        ("Welcome Prompt",      "/ivr/welcome",    "POST", "Plays greeting when call arrives"),
        ("Menu Driven",         "Gather + Say",    "XML",  "Press 1,2,3,9 options"),
        ("Menu Handle",         "/ivr/menu",       "POST", "Routes digits to correct flow"),
        ("Admission Service",   "/ivr/admission",  "POST", "Reserves beds, issues Patient ID"),
        ("Bed Status Service",  "/ivr/bed-status", "POST", "Reports live bed availability"),
        ("Emergency Service",   "menu.py",         "AUTO", "Alerts team, plays emergency info"),
        ("Live Dashboard",      "/dashboard",      "GET",  "This page — real-time monitoring"),
    ]

    config_rows = ""
    for name, endpoint, method, desc in config_items:
        config_rows += f"""
        <div class="config-row">
            <span class="config-check">✅</span>
            <div class="config-info">
                <span class="config-name">{name}</span>
                <span class="config-desc">{desc}</span>
            </div>
            <div class="config-tags">
                <span class="tag tag-endpoint">{endpoint}</span>
                <span class="tag tag-method">{method}</span>
            </div>
        </div>"""

    now = datetime.now()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="5">
    <title>City Hospital — IVR Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg:         #060b14;
            --surface:    #0d1625;
            --surface2:   #121e30;
            --border:     rgba(255,255,255,0.06);
            --border2:    rgba(255,255,255,0.1);
            --accent:     #00d4ff;
            --accent2:    #0099cc;
            --good:       #00e676;
            --warn:       #ffab40;
            --critical:   #ff5252;
            --text:       #e8f0fe;
            --text2:      #8899aa;
            --text3:      #445566;
            --glow:       rgba(0,212,255,0.15);
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
        }}

        /* ── Background grid ── */
        body::before {{
            content: '';
            position: fixed; inset: 0;
            background-image:
                linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
            z-index: 0;
        }}

        .wrapper {{
            position: relative; z-index: 1;
            max-width: 1300px;
            margin: 0 auto;
            padding: 32px 24px;
        }}

        /* ── HEADER ── */
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 36px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border2);
        }}

        .header-left {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        .logo {{
            width: 52px; height: 52px;
            background: linear-gradient(135deg, var(--accent), #0055ff);
            border-radius: 14px;
            display: flex; align-items: center; justify-content: center;
            font-size: 24px;
            box-shadow: 0 0 24px rgba(0,212,255,0.3);
        }}

        .header-title h1 {{
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: var(--text);
        }}

        .header-title p {{
            font-size: 13px;
            color: var(--text2);
            margin-top: 2px;
        }}

        .header-right {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .live-pill {{
            display: flex;
            align-items: center;
            gap: 7px;
            background: rgba(0,230,118,0.1);
            border: 1px solid rgba(0,230,118,0.25);
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
            color: var(--good);
            letter-spacing: 0.5px;
        }}

        .live-dot {{
            width: 7px; height: 7px;
            background: var(--good);
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.4; transform: scale(0.8); }}
        }}

        .time-display {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: var(--text2);
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 6px 14px;
            border-radius: 8px;
        }}

        /* ── STAT CARDS ── */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 28px;
        }}

        .stat-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
            position: relative;
            overflow: hidden;
            transition: border-color 0.2s;
        }}

        .stat-card:hover {{
            border-color: var(--border2);
        }}

        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
        }}

        .stat-card.c1::before {{ background: linear-gradient(90deg, var(--accent), transparent); }}
        .stat-card.c2::before {{ background: linear-gradient(90deg, var(--good), transparent); }}
        .stat-card.c3::before {{ background: linear-gradient(90deg, var(--critical), transparent); }}
        .stat-card.c4::before {{ background: linear-gradient(90deg, var(--warn), transparent); }}

        .stat-icon {{
            font-size: 20px;
            margin-bottom: 12px;
            display: block;
        }}

        .stat-number {{
            font-size: 36px;
            font-weight: 700;
            line-height: 1;
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: -1px;
        }}

        .stat-card.c1 .stat-number {{ color: var(--accent); }}
        .stat-card.c2 .stat-number {{ color: var(--good); }}
        .stat-card.c3 .stat-number {{ color: var(--critical); }}
        .stat-card.c4 .stat-number {{ color: var(--warn); }}

        .stat-label {{
            font-size: 12px;
            color: var(--text2);
            margin-top: 6px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-weight: 500;
        }}

        /* ── SECTION TITLE ── */
        .section-title {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text2);
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .section-title::after {{
            content: '';
            flex: 1;
            height: 1px;
            background: var(--border);
        }}

        /* ── BED CARDS ── */
        .beds-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 28px;
        }}

        .bed-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            transition: transform 0.2s, border-color 0.2s;
        }}

        .bed-card:hover {{
            transform: translateY(-2px);
            border-color: var(--border2);
        }}

        .bed-card.good  {{ border-top: 2px solid var(--good); }}
        .bed-card.warn  {{ border-top: 2px solid var(--warn); }}
        .bed-card.critical {{ border-top: 2px solid var(--critical); }}

        .bed-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
        }}

        .dept-icon {{
            font-size: 28px;
            width: 48px; height: 48px;
            background: var(--surface2);
            border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
        }}

        .dept-name {{
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 1px;
            color: var(--text);
        }}

        .status-badge {{
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-top: 3px;
            padding: 2px 8px;
            border-radius: 20px;
            display: inline-block;
        }}

        .status-badge.good     {{ background: rgba(0,230,118,0.12); color: var(--good); }}
        .status-badge.warn     {{ background: rgba(255,171,64,0.12); color: var(--warn); }}
        .status-badge.critical {{ background: rgba(255,82,82,0.12);  color: var(--critical); }}

        /* Donut chart */
        .bed-donut {{
            position: relative;
            width: 90px; height: 90px;
            margin: 0 auto 20px;
        }}

        .donut-svg {{
            width: 100%; height: 100%;
            transform: rotate(-90deg);
        }}

        .donut-track {{
            fill: none;
            stroke: var(--surface2);
            stroke-width: 3.5;
        }}

        .donut-fill {{
            fill: none;
            stroke-width: 3.5;
            stroke-linecap: round;
            transition: stroke-dasharray 0.5s ease;
        }}

        .donut-fill.good     {{ stroke: var(--good); filter: drop-shadow(0 0 4px var(--good)); }}
        .donut-fill.warn     {{ stroke: var(--warn); filter: drop-shadow(0 0 4px var(--warn)); }}
        .donut-fill.critical {{ stroke: var(--critical); filter: drop-shadow(0 0 4px var(--critical)); }}

        .donut-center {{
            position: absolute;
            inset: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}

        .donut-number {{
            font-size: 22px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            line-height: 1;
        }}

        .donut-label {{
            font-size: 10px;
            color: var(--text2);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .bed-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            text-align: center;
        }}

        .bed-stat {{
            display: flex;
            flex-direction: column;
            gap: 3px;
        }}

        .stat-val {{
            font-size: 18px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }}

        .stat-key {{
            font-size: 10px;
            color: var(--text3);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* ── MAIN CONTENT GRID ── */
        .main-grid {{
            display: grid;
            grid-template-columns: 1fr 360px;
            gap: 20px;
        }}

        /* ── CALL LOG TABLE ── */
        .table-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
        }}

        .table-header {{
            padding: 18px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .table-title {{
            font-size: 14px;
            font-weight: 600;
            color: var(--text);
        }}

        .table-count {{
            font-size: 12px;
            color: var(--text2);
            font-family: 'JetBrains Mono', monospace;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            padding: 10px 16px;
            text-align: left;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text3);
            background: var(--surface2);
            border-bottom: 1px solid var(--border);
        }}

        td {{
            padding: 11px 16px;
            font-size: 13px;
            color: var(--text2);
            border-bottom: 1px solid var(--border);
        }}

        .log-row {{
            animation: fadeIn 0.4s ease both;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(4px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}

        .log-row:last-child td {{ border-bottom: none; }}
        .log-row:hover td {{ background: var(--surface2); }}

        .time-badge {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: var(--accent);
        }}

        .caller-num {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
        }}

        .dept-pill {{
            background: var(--surface2);
            border: 1px solid var(--border2);
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .badge {{
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .badge-success {{ background: rgba(0,230,118,0.1);  color: var(--good); }}
        .badge-error   {{ background: rgba(255,82,82,0.1);  color: var(--critical); }}
        .badge-info    {{ background: rgba(0,212,255,0.1);  color: var(--accent); }}

        .patient-id {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: var(--accent);
            background: rgba(0,212,255,0.08);
            padding: 2px 7px;
            border-radius: 5px;
        }}

        .dash {{ color: var(--text3); }}

        .empty-state {{
            text-align: center;
            padding: 32px;
            color: var(--text3);
            font-size: 13px;
        }}

        /* ── CONFIG PANEL ── */
        .config-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
        }}

        .config-header {{
            padding: 18px 20px;
            border-bottom: 1px solid var(--border);
        }}

        .config-title {{
            font-size: 14px;
            font-weight: 600;
        }}

        .config-subtitle {{
            font-size: 12px;
            color: var(--text2);
            margin-top: 3px;
        }}

        .config-body {{
            padding: 12px;
        }}

        .config-row {{
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 4px;
            transition: background 0.15s;
        }}

        .config-row:hover {{
            background: var(--surface2);
        }}

        .config-check {{ font-size: 14px; margin-top: 1px; flex-shrink: 0; }}

        .config-info {{
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}

        .config-name {{
            font-size: 13px;
            font-weight: 600;
            color: var(--text);
        }}

        .config-desc {{
            font-size: 11px;
            color: var(--text2);
        }}

        .config-tags {{
            display: flex;
            flex-direction: column;
            gap: 3px;
            align-items: flex-end;
        }}

        .tag {{
            font-size: 10px;
            font-family: 'JetBrains Mono', monospace;
            padding: 2px 7px;
            border-radius: 5px;
            white-space: nowrap;
        }}

        .tag-endpoint {{
            background: rgba(0,212,255,0.08);
            color: var(--accent);
            border: 1px solid rgba(0,212,255,0.15);
        }}

        .tag-method {{
            background: rgba(255,255,255,0.04);
            color: var(--text3);
            border: 1px solid var(--border);
        }}

        /* ── FOOTER ── */
        .footer {{
            margin-top: 28px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .footer-text {{
            font-size: 12px;
            color: var(--text3);
        }}

        .footer-stack {{
            display: flex;
            gap: 8px;
        }}

        .stack-tag {{
            font-size: 11px;
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 4px 10px;
            border-radius: 6px;
            color: var(--text2);
        }}
    </style>
</head>
<body>
<div class="wrapper">

    <!-- HEADER -->
    <div class="header">
        <div class="header-left">
            <div class="logo">🏥</div>
            <div class="header-title">
                <h1>City Hospital IVR</h1>
                <p>Milestone 2 — Live Admin Dashboard</p>
            </div>
        </div>
        <div class="header-right">
            <div class="live-pill">
                <div class="live-dot"></div>
                LIVE
            </div>
            <div class="time-display">{now.strftime('%d %b %Y &nbsp; %H:%M:%S')}</div>
        </div>
    </div>

    <!-- STAT CARDS -->
    <div class="stats-grid">
        <div class="stat-card c1">
            <span class="stat-icon">📞</span>
            <div class="stat-number">{stats['total_calls']}</div>
            <div class="stat-label">Total Calls</div>
        </div>
        <div class="stat-card c2">
            <span class="stat-icon">✅</span>
            <div class="stat-number">{stats['total_admitted']}</div>
            <div class="stat-label">Admissions</div>
        </div>
        <div class="stat-card c3">
            <span class="stat-icon">🚨</span>
            <div class="stat-number">{stats['emergency']}</div>
            <div class="stat-label">Emergencies</div>
        </div>
        <div class="stat-card c4">
            <span class="stat-icon">🛏️</span>
            <div class="stat-number">{stats['bed_checks']}</div>
            <div class="stat-label">Bed Checks</div>
        </div>
    </div>

    <!-- BED STATUS -->
    <div class="section-title">🛏️ Bed Availability — Real Time</div>
    <div class="beds-grid">
        {bed_cards}
    </div>

    <!-- BOTTOM GRID -->
    <div class="main-grid">

        <!-- CALL LOG -->
        <div class="table-card">
            <div class="table-header">
                <div class="table-title">📋 Live Call Log</div>
                <div class="table-count">{len(db.call_logs)} events</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Caller</th>
                        <th>Action</th>
                        <th>Department</th>
                        <th>Status</th>
                        <th>Patient ID</th>
                    </tr>
                </thead>
                <tbody>
                    {log_rows}
                </tbody>
            </table>
        </div>

        <!-- CONFIG PANEL -->
        <div class="config-card">
            <div class="config-header">
                <div class="config-title">⚙️ System Configuration</div>
                <div class="config-subtitle">All milestone features active</div>
            </div>
            <div class="config-body">
                {config_rows}
            </div>
        </div>

    </div>

    <!-- FOOTER -->
    <div class="footer">
        <div class="footer-text">Auto-refreshes every 5 seconds &nbsp;|&nbsp; Hospital IVR Milestone 2</div>
        <div class="footer-stack">
            <span class="stack-tag">FastAPI</span>
            <span class="stack-tag">Twilio</span>
            <span class="stack-tag">TwiML</span>
            <span class="stack-tag">Python 3</span>
            <span class="stack-tag">ngrok</span>
        </div>
    </div>

</div>
</body>
</html>"""