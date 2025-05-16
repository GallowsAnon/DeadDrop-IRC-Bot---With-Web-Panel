import random

class Module:
    """
    Coffee Module - Serves coffee to users.
    """

    def __init__(self, bot):
        self.bot = bot
        self.coffee_types = [
            "Espresso", "Cappuccino", "Latte", "Mocha", "Americano",
            "Macchiato", "Flat White", "Irish Coffee", "Turkish Coffee",
            "Vienna Coffee", "Cortado", "Ristretto", "Doppio",
            "Lungo", "Affogato"
        ]

    def handle_command(self, connection, event, command, args, channel, nick):
        """
        Handles commands for this module.
        """
        # Command is already processed and doesn't include the trigger prefix
        if command == 'coffee':
            if not args:
                self.bot.send_message(connection, channel, f"{nick}: Usage: !coffee <nick>")
                return

            target_nick = args[0]  # The person who receives coffee
            coffee_type = random.choice(self.coffee_types)
            self.bot.send_message(connection, channel, f"brews a hot {coffee_type} for {target_nick}!")

    def handle_message(self, connection, event, channel, nick, message):
        """
        Handles regular messages for this module.
        """
        pass  # This module doesn't handle regular messages 