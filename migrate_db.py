from app import app
from models import db, User, BotSettings, AISettings

with app.app_context():
    # Drop all tables
    db.drop_all()
    # Create all tables with new schema
    db.create_all()
    
    # Create default admin user
    admin = User(username='admin', is_admin=True)
    admin.set_password('admin')
    db.session.add(admin)
    
    # Create default AI settings
    ai_settings = AISettings()
    db.session.add(ai_settings)
    
    # Create default bot settings
    bot_settings = BotSettings(
        server='irc.example.com',
        port=6697,
        use_ssl=True,
        nick='bot',
        username='bot',
        realname='IRC Bot',
        channels='#test'
    )
    db.session.add(bot_settings)
    
    # Commit all changes
    db.session.commit()
    print("Database migration completed successfully!") 