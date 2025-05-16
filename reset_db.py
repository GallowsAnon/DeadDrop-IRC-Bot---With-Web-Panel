from app import app
from models import db, User, BotSettings, AISettings, Module
import random

def reset_database():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables with new schema
        db.create_all()
        
        # Create default bot settings with placeholder data
        bot_settings = BotSettings(
            server='irc.example.com',
            port=6697,
            use_ssl=True,
            nick='bot',
            username='bot',
            realname='IRC Bot',
            channels='#welcome',
            is_connected=False
        )
        db.session.add(bot_settings)
        
        # Create default AI settings
        ai_settings = AISettings(
            system_prompt="You are a helpful IRC bot. Keep your responses concise and friendly.",
            is_enabled=False
        )
        db.session.add(ai_settings)
        
        # Create welcome module
        welcome_module = Module(
            name="Welcome Module",
            trigger="!welcome",
            code="""
import random

class Module:
    def __init__(self, bot):
        self.bot = bot
        self.welcome_messages = [
            "Welcome to the channel!",
            "Glad to have you here!",
            "Hello and welcome!",
            "Welcome aboard!",
            "Great to see you here!"
        ]

    def handle_command(self, connection, event, command, args, channel, nick):
        if command == 'welcome':
            if not args:
                self.bot.send_message(connection, channel, f"{nick}: Usage: !welcome <nick>")
                return

            target_nick = args[0]
            welcome_msg = random.choice(self.welcome_messages)
            self.bot.send_message(connection, channel, f"{welcome_msg} {target_nick}!")

    def handle_message(self, connection, event, channel, nick, message):
        pass
""",
            is_enabled=True
        )
        db.session.add(welcome_module)
        
        # Commit all changes
        db.session.commit()
        print("Database reset completed successfully!")
        print("No users exist in the database. Please create an admin account through the web interface.")

if __name__ == '__main__':
    reset_database() 