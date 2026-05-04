import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from google import genai
import stripe
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_secret_key_for_development_only')

# Smart Database Configuration
db_url = os.getenv("DATABASE_URL", "sqlite:///users.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configure APIs
API_KEY = os.getenv("GEMINI_API_KEY")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_mock_key")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_mock_secret")

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    credits = db.Column(db.Integer, default=3)
    history = db.relationship('History', backref='user', lazy=True)

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prompt_topic = db.Column(db.String(250), nullable=False) # e.g., the platform or product
    generated_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists.', 'error')
            return redirect(url_for('register'))
            
        new_user = User(email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('home'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Stripe Payments ---
@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': '50 AI Generation Credits',
                        },
                        'unit_amount': 500,
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=request.host_url + '?payment_success=true',
            cancel_url=request.host_url + '?payment_canceled=true',
            client_reference_id=str(current_user.id)
        )
        return jsonify({"url": checkout_session.url})
    except Exception as e:
        return jsonify(error=str(e)), 403

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        user_id = session.get('client_reference_id')
        if user_id:
            user = User.query.get(int(user_id))
            if user:
                user.credits += 50
                db.session.commit()

    return '', 200

# --- Application Routes ---
@app.route('/')
@login_required
def home():
    if request.args.get('payment_success'):
        flash('Payment successful! 50 Credits have been added to your account.', 'success')
    return render_template('index.html', user=current_user)

@app.route('/history')
@login_required
def history():
    user_history = History.query.filter_by(user_id=current_user.id).order_by(History.timestamp.desc()).all()
    return render_template('history.html', user=current_user, history=user_history)

@app.route('/api/generate', methods=['POST'])
@login_required
def generate():
    if current_user.credits <= 0:
        return jsonify({"error": "Insufficient credits", "code": "OUT_OF_CREDITS"}), 402

    data = request.json
    prompt_text = data.get('prompt')
    
    # We optionally extract 'topic' or 'platform' from the frontend if passed
    # For now, we will just use a generic 'AI Generation' or extract the first 30 chars
    topic = data.get('topic', 'AI Generation')
    
    if not prompt_text:
        return jsonify({"error": "No prompt provided"}), 400
        
    if not API_KEY:
         return jsonify({"error": "API Key is missing."}), 500

    try:
        client = genai.Client(api_key=API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_text,
        )
        
        # Deduct a credit
        current_user.credits -= 1
        
        # Save to History
        new_entry = History(
            user_id=current_user.id,
            prompt_topic=topic,
            generated_text=response.text
        )
        db.session.add(new_entry)
        db.session.commit()
        
        return jsonify({"result": response.text, "remaining_credits": current_user.credits})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
