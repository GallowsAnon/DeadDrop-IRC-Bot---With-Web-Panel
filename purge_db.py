from app import app
from models import db, User, BotSettings, AISettings

def purge_database():
    with app.app_context():
        # Delete all bot settings
        BotSettings.query.delete()
        
        # Delete all AI settings
        AISettings.query.delete()
        
        # Create default bot settings
        bot_settings = BotSettings(
            server='irc.example.com',
            port=6697,
            use_ssl=True,
            nick='bot',
            username='bot',
            realname='IRC Bot',
            channels='#test',
            is_connected=False
        )
        db.session.add(bot_settings)
        
        # Create default AI settings
        ai_settings = AISettings(
            system_prompt="You are a helpful IRC bot. Keep your responses concise and friendly.",
            is_enabled=False
        )
        db.session.add(ai_settings)
        
        # Ensure admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin')
            db.session.add(admin)
        
        # Commit changes
        db.session.commit()
        print("Database purged successfully! Bot and AI settings have been reset to defaults.")

if __name__ == '__main__':
    purge_database() 