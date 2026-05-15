from flask import Blueprint, render_template, redirect, url_for, session
from app.models import db, Incident
from app.utils import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    total_incidents = Incident.query.count()
    recent_incidents = Incident.query.order_by(Incident.date_reported.desc()).limit(5).all()
    incident_types = db.session.query(Incident.incident_type.distinct()).all()
    incident_types = [t[0] for t in incident_types]
    districts = db.session.query(Incident.district.distinct()).all()
    districts = [d[0] for d in districts]
    return render_template('dashboard.html',
                            total_incidents=total_incidents,
                            recent_incidents=recent_incidents,
                            incident_types=incident_types,
                            districts=districts)
