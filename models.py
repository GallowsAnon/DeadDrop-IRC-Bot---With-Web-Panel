from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class BotSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    use_ssl = db.Column(db.Boolean, default=True)
    nick = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    realname = db.Column(db.String(255), nullable=False)
    nickserv_password = db.Column(db.String(255))
    channels = db.Column(db.Text)  # Store channels as comma-separated string
    is_connected = db.Column(db.Boolean, default=False)

class AISettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    openai_api_key = db.Column(db.String(255))
    gemini_api_key = db.Column(db.String(255))
    ai_provider = db.Column(db.String(20), default='openai')  # 'openai' or 'gemini'
    system_prompt = db.Column(db.Text, default="You are a helpful IRC bot. Keep your responses concise and friendly.")
    is_enabled = db.Column(db.Boolean, default=False)

class URLWatcherSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url_color = db.Column(db.String(4), default='12')  # IRC color code as string
    youtube_color = db.Column(db.String(4), default='13')  # IRC color code as string
    youtube_api_key = db.Column(db.String(128), default='')

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    trigger = db.Column(db.String(10), nullable=False, default='!')
    code = db.Column(db.Text, nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Module {self.name}>'

class ChannelManagementSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(100), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    flood_threshold = db.Column(db.Integer, default=8)  # Number of messages
    flood_timeframe = db.Column(db.Integer, default=60)  # Time in seconds
    caps_percentage = db.Column(db.Integer, default=70)  # Percentage of caps to trigger kick
    warning_timeout_1 = db.Column(db.Integer, default=60)  # First warning timeout in seconds
    warning_timeout_2 = db.Column(db.Integer, default=120)  # Second warning timeout in seconds
    warning_ban_duration = db.Column(db.Integer, default=86400)  # Third warning ban duration in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ChannelManagementSettings {self.channel}>'

class UserWarning(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(100), nullable=False)
    nick = db.Column(db.String(100), nullable=False)
    warning_count = db.Column(db.Integer, default=0)
    last_warning = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserWarning {self.channel}:{self.nick}>'

def init_db():
    db.create_all()
    
    # Create default AI settings if they don't exist
    if not AISettings.query.first():
        ai_settings = AISettings()
        db.session.add(ai_settings)
        db.session.commit() 