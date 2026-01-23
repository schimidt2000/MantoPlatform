from datetime import datetime
from flask import Blueprint, redirect, request, session, url_for, render_template
from flask_login import login_required
from .service import get_authorization_url, build_flow, save_token, fetch_events_for_month

calendar_bp = Blueprint("calendar", __name__)

CALENDAR_ID = "eventos@mantoproducoes.com.br"

@calendar_bp.route("/google/connect")
@login_required
def google_connect():
    redirect_uri = url_for("calendar.google_callback", _external=True)
    auth_url, state = get_authorization_url(redirect_uri)
    session["google_oauth_state"] = state
    return redirect(auth_url)

@calendar_bp.route("/google/callback")
@login_required
def google_callback():
    state = session.get("google_oauth_state")
    redirect_uri = url_for("calendar.google_callback", _external=True)

    flow = build_flow(redirect_uri)
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials
    save_token(creds)

    return redirect(url_for("calendar.agenda"))

@calendar_bp.route("/agenda")
@login_required
def agenda():
    # ym = "YYYY-MM"
    ym = request.args.get("ym", "").strip()
    now = datetime.now()

    if ym:
        year, month = ym.split("-")
        year = int(year)
        month = int(month)
    else:
        year = now.year
        month = now.month
        ym = f"{year:04d}-{month:02d}"

    items = fetch_events_for_month(CALENDAR_ID, year, month)

    # anterior e próximo mês (para botões)
    if month == 1:
        prev_ym = f"{year-1:04d}-12"
    else:
        prev_ym = f"{year:04d}-{month-1:02d}"

    if month == 12:
        next_ym = f"{year+1:04d}-01"
    else:
        next_ym = f"{year:04d}-{month+1:02d}"

    return render_template(
        "calendar_list.html",
        ym=ym,
        prev_ym=prev_ym,
        next_ym=next_ym,
        events=items,
    )
