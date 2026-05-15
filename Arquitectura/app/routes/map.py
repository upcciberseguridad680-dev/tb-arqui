from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from app.models import db, Incident
from app.utils import login_required
import json
from datetime import datetime

map_bp = Blueprint('map', __name__)

@map_bp.route('/heatmap')
@login_required
def heatmap():
    incident_types = db.session.query(Incident.incident_type.distinct()).all()
    incident_types = [t[0] for t in incident_types]
    districts = db.session.query(Incident.district.distinct()).all()
    districts = [d[0] for d in districts]
    incident_type = request.args.get('type', '')
    district = request.args.get('district', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    query = Incident.query
    if incident_type:
        query = query.filter(Incident.incident_type == incident_type)
    if district:
        query = query.filter(Incident.district == district)
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Incident.date_reported >= start_date_obj)
        except ValueError:
            pass
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Incident.date_reported <= end_date_obj)
        except ValueError:
            pass
    incidents = query.all()
    heatmap_data = []
    for incident in incidents:
        heatmap_data.append({
            'lat': incident.latitude,
            'lng': incident.longitude,
            'intensity': incident.severity,
            'district': incident.district,
            'type': incident.incident_type,
            'description': incident.description,
            'date': incident.date_reported.strftime('%Y-%m-%d %H:%M')
        })
    return render_template('heatmap.html',
                            incidents=incidents,
                            heatmap_data=json.dumps(heatmap_data),
                            incident_types=incident_types,
                            districts=districts)
