from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import User, BotSettings, AISettings, init_db, URLWatcherSettings, Module, ChannelManagementSettings, UserWarning
from irc_bouncer import IRCBouncer, Channel
from extensions import app, db, socketio, login_manager, migrate
from flask_socketio import emit, join_room, leave_room
import os
import threading
import logging
import openai
import google.generativeai as genai
from datetime import datetime
from ai_utils import get_ai_response

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-to-a-secure-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///irc_bot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions with app
db.init_app(app)
migrate.init_app(app, db)
socketio.init_app(app)
login_manager.init_app(app)

# Initialize database
with app.app_context():
    init_db()

# Global bot instance
irc_bot = None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You need to be an admin to access this page.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def check_first_time_setup():
    if not request.endpoint or request.endpoint.startswith('static'):
        return
    
    # Skip for login and create_user routes to prevent redirect loops
    if request.endpoint in ['login', 'create_user', 'static']:
        return
        
    with app.app_context():
        if not User.query.first():
            if request.endpoint != 'create_user':
                return redirect(url_for('create_user'))

@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('create_user.html')
            
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('create_user.html')
            
        # Create new admin user
        user = User(username=username, is_admin=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('User created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('create_user.html')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    settings = BotSettings.query.first()
    channels = settings.channels.split(',') if settings and settings.channels else []
    return render_template('index.html', settings=settings, channels=channels)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    settings = BotSettings.query.first()
    if not settings:
        settings = BotSettings(
            server='irc.example.com',
            port=6697,
            use_ssl=True,
            nick='bot',
            username='bot',
            realname='IRC Bot',
            channels='#test',
            is_connected=False
        )
        db.session.add(settings)
        db.session.commit()
    
    # Check actual connection status
    global irc_bot
    if irc_bot:
        actual_status = irc_bot.is_actually_connected()
        if settings.is_connected != actual_status:
            settings.is_connected = actual_status
            db.session.commit()
    
    if request.method == 'POST':
        settings.server = request.form.get('server')
        settings.port = int(request.form.get('port'))
        settings.use_ssl = request.form.get('use_ssl') == 'on'
        settings.nick = request.form.get('nick')
        settings.username = request.form.get('username')
        settings.realname = request.form.get('realname')
        settings.nickserv_password = request.form.get('nickserv_password')
        settings.channels = request.form.get('channels')
        db.session.commit()
        
        flash('Settings updated successfully')
        return redirect(url_for('settings'))
    
    return render_template('settings.html', settings=settings)

@app.route('/connect', methods=['POST'])
@login_required
@admin_required
def connect():
    global irc_bot
    settings = BotSettings.query.first()
    if not settings:
        flash('No bot settings found', 'error')
        return redirect(url_for('settings'))
    
    if irc_bot and irc_bot.connection and irc_bot.connection.is_connected():
        flash('Bot is already connected', 'info')
    else:
        try:
            irc_bot = IRCBouncer(
                server=settings.server,
                port=settings.port,
                nick=settings.nick,
                username=settings.username,
                realname=settings.realname,
                use_ssl=settings.use_ssl
            )
            settings.is_connected = True
            db.session.commit()
            flash('Bot connected successfully', 'success')
        except Exception as e:
            logger.error(f"Failed to connect bot: {str(e)}")
            flash(f"Failed to connect bot: {str(e)}", 'error')
    
    return redirect(url_for('settings'))

@app.route('/disconnect', methods=['POST'])
@login_required
@admin_required
def disconnect():
    global irc_bot
    settings = BotSettings.query.first()
    if irc_bot and irc_bot.connection and irc_bot.connection.is_connected():
        try:
            irc_bot.disconnect()
            irc_bot = None
            settings.is_connected = False
            db.session.commit()
            flash('Bot disconnected successfully', 'success')
        except Exception as e:
            logger.error(f"Failed to disconnect bot: {str(e)}")
            flash(f"Failed to disconnect bot: {str(e)}", 'error')
    else:
        settings.is_connected = False
        db.session.commit()
        flash('Bot is not connected', 'info')
    
    return redirect(url_for('settings'))

@app.route('/ai_settings', methods=['GET'])
@login_required
@admin_required
def ai_settings():
    ai_settings = AISettings.query.first()
    if not ai_settings:
        ai_settings = AISettings()
        db.session.add(ai_settings)
        db.session.commit()
    return render_template('ai_settings.html', ai_settings=ai_settings)

@app.route('/ai_settings/update', methods=['POST'])
@login_required
@admin_required
def update_ai_settings():
    ai_settings = AISettings.query.first()
    if not ai_settings:
        ai_settings = AISettings()
        db.session.add(ai_settings)
    
    # Update settings
    ai_settings.openai_api_key = request.form.get('openai_api_key')
    ai_settings.gemini_api_key = request.form.get('gemini_api_key')
    ai_settings.ai_provider = request.form.get('ai_provider', 'openai')
    ai_settings.system_prompt = request.form.get('system_prompt')
    ai_settings.is_enabled = bool(request.form.get('is_enabled'))
    
    # Save changes
    try:
        db.session.commit()
        logger.info("AI settings updated successfully")
        flash('AI settings updated successfully!', 'success')
    except Exception as e:
        logger.error(f"Error saving AI settings: {e}")
        db.session.rollback()
        flash('Error saving AI settings. Please try again.', 'error')
    
    return redirect(url_for('ai_settings'))

@app.route('/ai_settings/test_connection', methods=['POST'])
@login_required
@admin_required
def test_ai_connection():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400

        provider = data.get('provider', 'openai')
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'message': f'No {provider} API key provided'
            }), 400
        
        try:
            if provider == 'openai':
                # Test the OpenAI API connection
                client = openai.OpenAI(
                    api_key=api_key,
                    timeout=10.0
                )
                
                # Make a simple test request
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Test connection"}],
                    max_tokens=5
                )
            else:  # gemini
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content("Test connection")
            
            return jsonify({
                'success': True,
                'message': f'Successfully connected to {provider} API'
            })
        except Exception as e:
            logger.error(f"Error testing {provider} connection: {e}")
            return jsonify({
                'success': False,
                'message': f'Failed to connect to {provider} API: {str(e)}'
            }), 400
    except Exception as e:
        logger.error(f"Error in test_ai_connection: {e}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        settings = BotSettings.query.first()
        global irc_bot
        actual_status = False
        if irc_bot:
            actual_status = irc_bot.is_actually_connected()
            if settings.is_connected != actual_status:
                settings.is_connected = actual_status
                db.session.commit()
        
        emit('status_update', {
            'connected': actual_status,
            'server': settings.server if settings else 'undefined',
            'port': settings.port if settings else 'undefined'
        })

@app.route('/webchat')
@login_required
def webchat():
    return render_template('webchat.html')

# --- Webchat SocketIO Events ---
@socketio.on('webchat_init')
def webchat_init():
    global irc_bot
    if not irc_bot or not irc_bot.is_actually_connected():
        emit('webchat_status', {'connected': False})
        return
    emit('webchat_status', {'connected': True})
    # Send channel list
    channels = list(irc_bot.webchat_channels.keys())
    emit('webchat_channels', {'channels': channels})
    # Auto-join first channel if any
    if channels:
        channel = channels[0]
        join_room(channel)
        emit('webchat_joined_channel', {'channel': channel})
        # Send users and messages
        emit('webchat_users', {'users': irc_bot.webchat_channels[channel].get_users()})
        emit('webchat_messages', {'messages': get_channel_messages(channel)})
        emit('webchat_topic', {'topic': get_channel_topic(channel)})

@socketio.on('webchat_part_channel')
def webchat_part_channel(data):
    channel = data.get('channel')
    global irc_bot
    if not irc_bot or not irc_bot.is_actually_connected() or not channel:
        return
    # Send PART command
    irc_bot.connection.part(channel)
    # Remove from channel list and notify clients
    if channel in irc_bot.webchat_channels:
        del irc_bot.webchat_channels[channel]
    if hasattr(irc_bot, 'webchat_messages') and channel in irc_bot.webchat_messages:
        del irc_bot.webchat_messages[channel]
    # Update BotSettings.channels
    settings = BotSettings.query.first()
    if settings:
        channels = [c.strip() for c in settings.channels.split(',') if c.strip()]
        if channel in channels:
            channels.remove(channel)
            settings.channels = ','.join(channels)
            db.session.commit()
    emit('webchat_channels', {'channels': list(irc_bot.webchat_channels.keys())})

@socketio.on('webchat_open_query')
def webchat_open_query(data):
    nick = data.get('nick')
    global irc_bot
    if not irc_bot or not irc_bot.is_actually_connected() or not nick:
        return
    # Get private message history
    pm_key = nick
    messages = []
    if hasattr(irc_bot, 'webchat_messages') and pm_key in irc_bot.webchat_messages:
        messages = irc_bot.webchat_messages[pm_key]
    emit('webchat_opened_query', {'nick': nick, 'messages': messages})

@socketio.on('webchat_join_channel')
def webchat_join_channel(data):
    channel = data.get('channel')
    global irc_bot
    if not irc_bot or not irc_bot.is_actually_connected() or not channel:
        return
    logger.info(f"Joining channel: {channel}")
    # If not already joined, join the channel
    if channel not in irc_bot.webchat_channels:
        logger.info(f"Channel {channel} not in webchat_channels, joining...")
        irc_bot.connection.join(channel)
        # Do NOT manually create the Channel object here; let the IRC event handler do it
    join_room(channel)
    # Update BotSettings.channels
    settings = BotSettings.query.first()
    if settings:
        channels = [c.strip() for c in settings.channels.split(',') if c.strip()]
        if channel not in channels:
            channels.append(channel)
            settings.channels = ','.join(channels)
            db.session.commit()
    # Get current channel list
    current_channels = list(irc_bot.webchat_channels.keys())
    logger.info(f"Current channels: {current_channels}")
    # Emit updated channel list to all clients
    emit('webchat_channels', {'channels': current_channels})
    # Emit joined channel event to the joining client
    emit('webchat_joined_channel', {'channel': channel})
    # Request initial data for the channel
    if channel in irc_bot.webchat_channels:
        emit('webchat_users', {'users': irc_bot.webchat_channels[channel].get_users()})
        emit('webchat_messages', {'messages': get_channel_messages(channel)})
        emit('webchat_topic', {'topic': get_channel_topic(channel)})

@socketio.on('webchat_send_message')
def webchat_send_message(data):
    channel = data.get('channel')
    message = data.get('message')
    global irc_bot
    if not irc_bot or not irc_bot.is_actually_connected() or not channel or not message:
        return
    # If channel is a user (private message)
    if channel not in irc_bot.webchat_channels:
        irc_bot.send_message(irc_bot.connection, channel, message)
        return
    # Otherwise, normal channel message
    irc_bot.send_message(irc_bot.connection, channel, message)

@socketio.on('webchat_get_topic')
def webchat_get_topic(data):
    channel = data.get('channel')
    global irc_bot
    if not irc_bot or not irc_bot.is_actually_connected() or not channel:
        return
    # Get topic from local storage or request from server
    topic = ''
    if hasattr(irc_bot, 'topics') and channel in irc_bot.topics:
        topic = irc_bot.topics[channel]
    else:
        # Request topic from server
        irc_bot.connection.topic(channel)
    emit('webchat_topic', {'topic': topic, 'channel': channel})

@socketio.on('webchat_users_request')
def webchat_users_request(data):
    channel = data.get('channel')
    global irc_bot
    if not irc_bot or not irc_bot.is_actually_connected() or not channel:
        return
    if channel in irc_bot.webchat_channels:
        emit('webchat_users', {'users': irc_bot.webchat_channels[channel].get_users()})

@socketio.on('webchat_messages_request')
def webchat_messages_request(data):
    channel = data.get('channel')
    global irc_bot
    if not irc_bot or not irc_bot.is_actually_connected() or not channel:
        return
    emit('webchat_messages', {'messages': get_channel_messages(channel)})

@socketio.on('webchat_set_topic')
def webchat_set_topic(data):
    channel = data.get('channel')
    topic = data.get('topic')
    global irc_bot
    if not irc_bot or not irc_bot.is_actually_connected() or not channel:
        return
    logger.info(f"Setting topic for {channel}: {topic}")
    # Send TOPIC command to IRC server
    irc_bot.connection.topic(channel, topic)
    # Update local topic storage
    if hasattr(irc_bot, 'topics'):
        irc_bot.topics[channel] = topic
    # Emit topic update to all clients in the channel
    emit('webchat_topic', {'topic': topic}, room=channel)

# --- Helper functions for webchat ---
def get_channel_messages(channel):
    # You may want to store messages in IRCBouncer for this to work
    if hasattr(irc_bot, 'webchat_messages') and channel in irc_bot.webchat_messages:
        return irc_bot.webchat_messages[channel]
    return []

def get_channel_topic(channel):
    if hasattr(irc_bot, 'topics') and channel in irc_bot.topics:
        return irc_bot.topics[channel]
    return ''

def now_str():
    return datetime.now().strftime('%H:%M:%S')

# --- IRCBouncer hooks for relaying events to webchat ---
# You need to add logic in IRCBouncer to call these when messages/users/topics update
# Example usage in IRCBouncer:
#   from extensions import socketio
#   socketio.emit('webchat_message', {...}, room=channel)

@app.route('/url_settings', methods=['GET', 'POST'])
@login_required
@admin_required
def url_settings():
    settings = URLWatcherSettings.query.first()
    if not settings:
        settings = URLWatcherSettings()
        db.session.add(settings)
        db.session.commit()
    if request.method == 'POST':
        settings.url_color = request.form.get('url_color')
        settings.youtube_color = request.form.get('youtube_color')
        settings.youtube_api_key = request.form.get('youtube_api_key')
        db.session.commit()
        flash('URL Watcher settings updated successfully!', 'success')
        return redirect(url_for('url_settings'))
    return render_template('url_settings.html', settings=settings)

@app.route('/modules')
@login_required
@admin_required
def modules():
    modules = Module.query.all()
    return render_template('modules.html', modules=modules)

@app.route('/modules', methods=['POST'])
@login_required
@admin_required
def create_module():
    data = request.get_json()
    module = Module(
        name=data['name'],
        trigger=data['trigger'],
        code=data['code']
    )
    db.session.add(module)
    db.session.commit()
    
    # Reload modules after creating a new one
    if irc_bot and hasattr(irc_bot, 'module_loader'):
        irc_bot.module_loader.load_modules()
    
    return jsonify({'success': True})

@app.route('/modules/<int:id>', methods=['GET'])
@login_required
@admin_required
def get_module(id):
    module = Module.query.get_or_404(id)
    return jsonify({
        'id': module.id,
        'name': module.name,
        'trigger': module.trigger,
        'code': module.code
    })

@app.route('/modules/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_module(id):
    module = Module.query.get_or_404(id)
    data = request.get_json()
    module.name = data['name']
    module.trigger = data['trigger']
    module.code = data['code']
    db.session.commit()
    
    # Reload modules after updating
    if irc_bot and hasattr(irc_bot, 'module_loader'):
        irc_bot.module_loader.load_modules()
    
    return jsonify({'success': True})

@app.route('/modules/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_module(id):
    module = Module.query.get_or_404(id)
    db.session.delete(module)
    db.session.commit()
    
    # Reload modules after deletion
    if irc_bot and hasattr(irc_bot, 'module_loader'):
        irc_bot.module_loader.load_modules()
    
    return jsonify({'success': True})

@app.route('/modules/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_module(id):
    module = Module.query.get_or_404(id)
    module.is_enabled = not module.is_enabled
    db.session.commit()
    
    # Reload modules after toggling
    if irc_bot and hasattr(irc_bot, 'module_loader'):
        irc_bot.module_loader.load_modules()
    
    return jsonify({'success': True})

@app.route('/modules/generate', methods=['POST'])
@login_required
@admin_required
def generate_module():
    data = request.get_json()
    description = data.get('description')
    
    # Get AI settings
    ai_settings = AISettings.query.first()
    if not ai_settings or not ai_settings.is_enabled:
        return jsonify({'error': 'AI is not enabled'}), 400
    
    try:
        if ai_settings.ai_provider == 'openai':
            if not ai_settings.openai_api_key:
                return jsonify({'error': 'OpenAI API key is missing'}), 400
            client = openai.OpenAI(api_key=ai_settings.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are a Python module generator for an IRC bot. Generate a Python module that can be hot-loaded into the bot. The module must follow these requirements:

1. The module must be a class named 'Module'
2. The class must have these methods:
   - __init__(self, bot): Initialize the module with the bot instance
   - handle_command(self, connection, event, command, args, channel, nick): Handle commands
   - handle_message(self, connection, event, channel, nick, message): Handle regular messages

3. The handle_command method receives these parameters:
   - connection: The IRC connection object
   - event: The IRC event object
   - command: The command name (without the trigger prefix - the module loader strips !@# prefixes)
   - args: List of command arguments
   - channel: The channel where the command was used
   - nick: The nickname of the user who used the command

4. The handle_message method receives these parameters:
   - connection: The IRC connection object
   - event: The IRC event object
   - channel: The channel where the message was sent
   - nick: The nickname of the user who sent the message
   - message: The message content

5. To send messages, ALWAYS use self.bot.send_message(connection, channel, message) instead of connection.privmsg().
   This ensures messages appear in both IRC and the webchat interface.

6. Important notes about command handling:
   - The module loader automatically strips command prefixes (!@#) from commands
   - When checking commands in handle_command, use the command name without the prefix
   - Example: If trigger is set to "coffee" in database, handle_command will receive "coffee" (not "!coffee")
   - The trigger in the database can include a prefix (e.g. "!coffee"), but handle_command will receive it without the prefix

Keep the code concise and focused on the described functionality.
DO NOT include ```python or ``` in your response. Just provide the raw Python code."""},
                    {"role": "user", "content": f"Generate a Python module for an IRC bot that: {description}"}
                ],
                max_tokens=1000
            )
            code = response.choices[0].message.content.strip()
            # Remove any remaining code block markers
            code = code.replace('```python', '').replace('```', '')
        else:  # gemini
            if not ai_settings.gemini_api_key:
                return jsonify({'error': 'Gemini API key is missing'}), 400
            genai.configure(api_key=ai_settings.gemini_api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(
                f"""You are a Python module generator for an IRC bot. Generate a Python module that can be hot-loaded into the bot. The module must follow these requirements:

1. The module must be a class named 'Module'
2. The class must have these methods:
   - __init__(self, bot): Initialize the module with the bot instance
   - handle_command(self, connection, event, command, args, channel, nick): Handle commands
   - handle_message(self, connection, event, channel, nick, message): Handle regular messages

3. The handle_command method receives these parameters:
   - connection: The IRC connection object
   - event: The IRC event object
   - command: The command name (without the trigger prefix - the module loader strips !@# prefixes)
   - args: List of command arguments
   - channel: The channel where the command was used
   - nick: The nickname of the user who used the command

4. The handle_message method receives these parameters:
   - connection: The IRC connection object
   - event: The IRC event object
   - channel: The channel where the message was sent
   - nick: The nickname of the user who sent the message
   - message: The message content

5. To send messages, ALWAYS use self.bot.send_message(connection, channel, message) instead of connection.privmsg().
   This ensures messages appear in both IRC and the webchat interface.

6. Important notes about command handling:
   - The module loader automatically strips command prefixes (!@#) from commands
   - When checking commands in handle_command, use the command name without the prefix
   - Example: If trigger is set to "coffee" in database, handle_command will receive "coffee" (not "!coffee")
   - The trigger in the database can include a prefix (e.g. "!coffee"), but handle_command will receive it without the prefix

Keep the code concise and focused on the described functionality.
DO NOT include ```python or ``` in your response. Just provide the raw Python code.

Generate a Python module for an IRC bot that: {description}"""
            )
            code = response.text.strip()
            # Remove any remaining code block markers
            code = code.replace('```python', '').replace('```', '')
        
        return jsonify({'code': code})
    except Exception as e:
        logger.error(f"Error generating module: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/modules/template')
@login_required
@admin_required
def module_template():
    with open('templates/module_template.py', 'r') as f:
        return f.read()

@app.route('/channel_management')
@login_required
@admin_required
def channel_management():
    settings = BotSettings.query.first()
    channels = settings.channels.split(',') if settings and settings.channels else []
    
    # Get or create settings for each channel
    channel_settings = {}
    for channel in channels:
        channel = channel.strip()
        settings = ChannelManagementSettings.query.filter_by(channel=channel).first()
        if not settings:
            settings = ChannelManagementSettings(channel=channel)
            db.session.add(settings)
            db.session.commit()
        channel_settings[channel] = settings
    
    return render_template('channel_management.html', channel_settings=channel_settings)

@app.route('/channel_management/update', methods=['POST'])
@login_required
@admin_required
def update_channel_management():
    channel = request.form.get('channel')
    is_enabled = request.form.get('is_enabled') == 'on'
    flood_threshold = int(request.form.get('flood_threshold', 8))
    flood_timeframe = int(request.form.get('flood_timeframe', 60))
    caps_percentage = int(request.form.get('caps_percentage', 70))
    warning_timeout_1 = int(request.form.get('warning_timeout_1', 60))
    warning_timeout_2 = int(request.form.get('warning_timeout_2', 120))
    warning_ban_duration = int(request.form.get('warning_ban_duration', 86400))
    
    settings = ChannelManagementSettings.query.filter_by(channel=channel).first()
    if not settings:
        settings = ChannelManagementSettings(channel=channel)
        db.session.add(settings)
    
    settings.is_enabled = is_enabled
    settings.flood_threshold = flood_threshold
    settings.flood_timeframe = flood_timeframe
    settings.caps_percentage = caps_percentage
    settings.warning_timeout_1 = warning_timeout_1
    settings.warning_timeout_2 = warning_timeout_2
    settings.warning_ban_duration = warning_ban_duration
    
    db.session.commit()
    
    # Reload settings in the bot
    global irc_bot
    if irc_bot:
        irc_bot.reload_channel_settings()
    
    return jsonify({'success': True})

@app.route('/clear_warning', methods=['POST'])
@login_required
def clear_warning():
    channel = request.form.get('channel')
    nick = request.form.get('nick')
    
    if not channel or not nick:
        return jsonify({'success': False, 'error': 'Missing channel or nick'})
    
    global irc_bot
    if not irc_bot:
        return jsonify({'success': False, 'error': 'Bot not initialized'})
    
    # Clear the warning
    irc_bot.user_warnings.clear_warning(channel, nick)
    
    return jsonify({'success': True})

@app.route('/get_warnings')
@login_required
def get_warnings():
    global irc_bot
    if not irc_bot:
        return jsonify({'success': False, 'error': 'Bot not initialized'})
    
    # Get warnings from database
    with app.app_context():
        warnings = UserWarning.query.all()
        warnings_list = [{
            'channel': w.channel,
            'nick': w.nick,
            'warning_count': w.warning_count,
            'last_warning': w.last_warning.isoformat() if w.last_warning else None
        } for w in warnings]
    
    return jsonify({'success': True, 'warnings': warnings_list})

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'initdb':
        with app.app_context():
            from models import init_db
            init_db()
            print('Database initialized.')
    else:
        with app.app_context():
            logger.info("Starting web server on 127.0.0.1:5000")
            socketio.run(app, host='127.0.0.1', port=5000, debug=False) 