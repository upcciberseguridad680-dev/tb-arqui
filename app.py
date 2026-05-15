from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///streetweb.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User model for login system
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Insecurity incident model
class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    district = db.Column(db.String(100), nullable=False)
    incident_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    severity = db.Column(db.Integer, default=1)  # 1-5 scale
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(100))  # e.g., police report, news, etc.

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get some statistics for the dashboard
    total_incidents = Incident.query.count()
    recent_incidents = Incident.query.order_by(Incident.date_reported.desc()).limit(5).all()

    # Get incident types for filter
    incident_types = db.session.query(Incident.incident_type.distinct()).all()
    incident_types = [t[0] for t in incident_types]

    # Get districts for filter
    districts = db.session.query(Incident.district.distinct()).all()
    districts = [d[0] for d in districts]

    return render_template('dashboard.html',
                         total_incidents=total_incidents,
                         recent_incidents=recent_incidents,
                         incident_types=incident_types,
                         districts=districts)

@app.route('/heatmap')
def heatmap():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get filter parameters
    incident_type = request.args.get('type', '')
    district = request.args.get('district', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # Build query
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

    # Convert to format needed for heatmap
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
                         heatmap_data=json.dumps(heatmap_data))

@app.route('/api/incidents')
def api_incidents():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    incidents = Incident.query.all()
    result = []
    for incident in incidents:
        result.append({
            'id': incident.id,
            'district': incident.district,
            'incident_type': incident.incident_type,
            'description': incident.description,
            'latitude': incident.latitude,
            'longitude': incident.longitude,
            'severity': incident.severity,
            'date_reported': incident.date_reported.isoformat() if incident.date_reported else None,
            'source': incident.source
        })

    return jsonify(result)

# Initialize database and add sample data
def init_db():
    db.create_all()

    # Create admin user if none exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@streetweb.com')
        admin.set_password('admin123')  # Change in production!
        db.session.add(admin)

    # Add sample Lima/Callao data if none exists
    if Incident.query.count() == 0:
        sample_incidents = [
            {
                'district': 'Miraflores',
                'incident_type': 'Robo',
                'description': 'Robo de celular en parque Kennedy',
                'latitude': -12.1216,
                'longitude': -77.0282,
                'severity': 3,
                'source': 'Policía Nacional'
            },
            {
                'district': 'San Isidro',
                'incident_type': 'Asalto',
                'description': 'Asalto a mano armada en vía pública',
                'latitude': -12.1032,
                'longitude': -77.0362,
                'severity': 4,
                'source': 'Denuncia ciudadana'
            },
            {
                'district': 'Barranco',
                'incident_type': 'Hurto',
                'description': 'Hurto de bolsa en malecón',
                'latitude': -12.1516,
                'longitude': -77.0123,
                'severity': 2,
                'source': 'Testigo ocular'
            },
            {
                'district': 'La Punta',
                'incident_type': 'Riña',
                'description': 'Pelea en establecimiento nocturno',
                'latitude': -12.0663,
                'longitude': -77.1368,
                'severity': 3,
                'source': 'Serenazgo'
            },
            {
                'district': 'Callao',
                'incident_type': 'Robo',
                'description': 'Robo a transporte público',
                'latitude': -12.0566,
                'longitude': -77.1181,
                'severity': 4,
                'source': 'Policía del Callao'
            },
            {
                'district': 'Villa El Salvador',
                'incident_type': 'Extorsión',
                'description': 'Extorsión a pequeño comerciante',
                'latitude': -12.1881,
                'longitude': -76.9845,
                'severity': 5,
                'source': 'Denuncia anónima'
            }
        ]

        for inc_data in sample_incidents:
            incident = Incident(**inc_data)
            db.session.add(incident)

    db.session.commit()

# Create tables and add sample data on first request
@app.before_first_request
def initialize():
    init_db()

# Health check endpoint for smoke tests
@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)