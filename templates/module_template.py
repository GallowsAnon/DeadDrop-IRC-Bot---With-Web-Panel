"""
This is a template for creating IRC bot modules.
Copy this template and modify it to create your own module.
"""

class Module:
    def __init__(self, bot):
        self.bot = bot
        self.name = "Example Module"
        self.description = "An example module that demonstrates the module system"
        self.trigger = "!"  # The command trigger for this module

    def init(self, bot):
        """
        Called when the module is loaded.
        Use this to initialize any resources your module needs.
        """
        self.bot = bot
        print(f"Module {self.name} initialized!")

    def cleanup(self):
        """
        Called when the module is unloaded.
        Use this to clean up any resources your module created.
        """
        print(f"Module {self.name} cleaned up!")

    def handle_message(self, connection, event, channel, nick, message):
        """
        Called for every message in channels the bot is in.
        Use this to handle general messages.
        """
        # Example: Echo messages containing "hello"
        if "hello" in message.lower():
            self.bot.send_message(connection, channel, f"Hello {nick}!")

    def handle_command(self, connection, event, command, args, channel, nick):
        """
        Called when a command is used (message starts with the trigger).
        Use this to handle commands.
        """
        # Example: Handle !echo command
        if command == "echo":
            if args:
                self.bot.send_message(connection, channel, " ".join(args))
            else:
                self.bot.send_message(connection, channel, "Usage: !echo <message>") 