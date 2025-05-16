import importlib.util
import sys
import logging
from models import Module
from extensions import app, db
import traceback # Import traceback for better error details

logger = logging.getLogger(__name__)

class ModuleLoader:
    def __init__(self, bot):
        self.bot = bot
        # Store loaded modules and their triggers
        # Store instances of the module classes
        self.loaded_modules = {} # {module_id: module_instance}
        self.module_triggers = {} # {trigger: module_id}
        logger.info("[ModuleLoader] Initializing and loading modules.")
        self.load_modules()

    def load_modules(self):
        """Load all enabled modules from the database."""
        logger.info("[ModuleLoader] Starting to load modules from database.")
        with app.app_context():
            modules = Module.query.filter_by(is_enabled=True).all()
            logger.info(f"[ModuleLoader] Found {len(modules)} enabled modules in database.")
            # Unload existing modules before loading new ones
            self.unload_all_modules()
            for module_data in modules: # Renamed variable to avoid conflict with module object
                logger.info(f"[ModuleLoader] Loading module from DB - ID: {module_data.id}, Name: {module_data.name}, Raw Trigger: {module_data.trigger}")
                self.load_module(module_data)
        logger.info("[ModuleLoader] Finished loading modules.")


    def load_module(self, module_data):
        """Load a single module."""
        module_name = f"module_{module_data.id}"

        try:
            spec = importlib.util.spec_from_loader(
                module_name,
                loader=importlib.machinery.SourceFileLoader(module_name, "<string>")
            )

            # Create a new module object
            module_obj = importlib.util.module_from_spec(spec)

            # Add the module object to sys.modules
            sys.modules[module_name] = module_obj

            # Execute the module code within the module object's dictionary
            exec(module_data.code, module_obj.__dict__)

            # *** MODIFIED: Find and instantiate the Module class within the loaded module ***
            module_class = None
            for name, obj in module_obj.__dict__.items():
                if isinstance(obj, type) and name == 'Module': # Look for a class named 'Module'
                    module_class = obj
                    break

            if module_class is None:
                logger.error(f"[ModuleLoader] Module {module_data.name} (ID: {module_data.id}) does not contain a class named 'Module'.")
                self.cleanup_failed_load(module_data.id, module_name)
                return False

            # Instantiate the module class, passing the bot instance if init expects it
            # Assuming the Module class's init method takes the bot instance
            try:
                module_instance = module_class(self.bot)
                logger.info(f"[ModuleLoader] Instantiated Module class for module: {module_data.name}")
            except TypeError as e:
                 logger.error(f"[ModuleLoader] Error instantiating Module class for module {module_data.name}: {e}. Does its __init__ method accept the bot instance?")
                 self.cleanup_failed_load(module_data.id, module_name)
                 return False


            # Store the module instance and its trigger
            self.loaded_modules[module_data.id] = module_instance
            # Use the module's trigger for command dispatch
            # Ensure trigger is treated case-insensitively for lookup
            processed_trigger = module_data.trigger.lower()
            while processed_trigger and processed_trigger[0] in '!@#': # Remove common command prefixes
                 processed_trigger = processed_trigger[1:]

            if processed_trigger:
                 if processed_trigger in self.module_triggers:
                      logger.warning(f"[ModuleLoader] Duplicate trigger '{processed_trigger}' found. Module {module_data.name} (ID: {module_data.id}) will overwrite the previous mapping.")
                 self.module_triggers[processed_trigger] = module_data.id
                 logger.info(f"[ModuleLoader] Mapped processed trigger '{processed_trigger}' to module ID {module_data.id}.")
            else:
                 logger.warning(f"[ModuleLoader] Module {module_data.name} (ID: {module_data.id}) has no valid trigger defined after removing prefixes.")


            # Call the init method on the instance if it exists
            # Initialization is now handled by the instance's __init__
            # if hasattr(module_instance, 'init'):
            #     try:
            #         module_instance.init(self.bot) # Init should be called during instantiation
            #         logger.info(f"[ModuleLoader] Initialized module: {module_data.name}")
            #     except Exception as e:
            #         logger.error(f"[ModuleLoader] Error initializing module {module_data.name}: {e}")


            logger.info(f"[ModuleLoader] Successfully loaded and instantiated module: {module_data.name}")
            return True
        except Exception as e:
            logger.error(f"[ModuleLoader] Unexpected error loading module {module_data.name} (ID: {module_data.id}): {e}\n{traceback.format_exc()}") # Added traceback
            self.cleanup_failed_load(module_data.id, module_name)
            return False

    def cleanup_failed_load(self, module_id, module_name):
        """Helper to clean up resources if a module fails to load."""
        if module_id in self.loaded_modules:
            del self.loaded_modules[module_id]
        # Need to find the trigger by module ID to remove it from module_triggers
        trigger_to_remove = None
        for trigger, mod_id in list(self.module_triggers.items()):
            if mod_id == module_id:
                trigger_to_remove = trigger
                break
        if trigger_to_remove:
            del self.module_triggers[trigger_to_remove]

        if module_name in sys.modules:
            del sys.modules[module_name]
        logger.warning(f"[ModuleLoader] Cleaned up resources for failed module load ID: {module_id}")


    def unload_module(self, module_id):
        """Unload a module instance."""
        logger.info(f"[ModuleLoader] Attempting to unload module ID: {module_id}")
        if module_id in self.loaded_modules:
            module_instance = self.loaded_modules[module_id]
            # Call cleanup on the instance if it exists
            if hasattr(module_instance, 'cleanup'):
                try:
                    module_instance.cleanup()
                    logger.info(f"[ModuleLoader] Called cleanup for module ID {module_id}.")
                except Exception as e:
                    logger.error(f"[ModuleLoader] Error during cleanup for module ID {module_id}: {e}\n{traceback.format_exc()}") # Added traceback


            # Remove module instance from loaded_modules
            del self.loaded_modules[module_id]
            # Find and remove the trigger mapping
            trigger_to_remove = None
            for trigger, mod_id in list(self.module_triggers.items()):
                if mod_id == module_id:
                    trigger_to_remove = trigger
                    break
            if trigger_to_remove:
                del self.module_triggers[trigger_to_remove]
                logger.info(f"[ModuleLoader] Removed trigger '{trigger_to_remove}' for module ID {module_id}.")


            # Remove module object from sys.modules (important for complete reload)
            module_name = f"module_{module_id}"
            if module_name in sys.modules:
                 # Ensure no references to the old module object before deleting
                 # This is tricky, but removing from sys.modules is a start
                 del sys.modules[module_name]
                 logger.info(f"[ModuleLoader] Removed module object '{module_name}' from sys.modules.")


            logger.info(f"[ModuleLoader] Successfully unloaded module ID: {module_id}")
        else:
            logger.warning(f"[ModuleLoader] Attempted to unload module ID {module_id}, but it was not found in loaded_modules.")

    def unload_all_modules(self):
        """Unload all currently loaded modules."""
        logger.info("[ModuleLoader] Unloading all modules.")
        # Iterate over a copy of keys as unloading modifies the dictionary
        for module_id in list(self.loaded_modules.keys()):
            self.unload_module(module_id)
        logger.info("[ModuleLoader] Finished unloading all modules.")


    def reload_module(self, module_data):
        """Reload a module."""
        logger.info(f"[ModuleLoader] Reloading module: {module_data.name} (ID: {module_data.id})")
        self.unload_module(module_data.id)
        # Fetch the latest data from the database before loading
        with app.app_context():
             updated_module_data = Module.query.get(module_data.id)
             if updated_module_data:
                  return self.load_module(updated_module_data)
             else:
                  logger.error(f"[ModuleLoader] Cannot reload module ID {module_data.id}: module not found in database.")
                  return False


    def handle_message(self, connection, event):
        """Handle incoming messages by passing them to loaded module instances."""
        channel = event.target
        nick = event.source.nick
        message = event.arguments[0]

        # logger.debug(f"[ModuleLoader] handle_message received in {channel} from {nick}: {message}") # Optional: uncomment for verbose message logging

        for module_id, module_instance in self.loaded_modules.items(): # Iterate over module instances
            try:
                if hasattr(module_instance, 'handle_message'):
                    # Pass all required arguments to handle_message
                    # logger.debug(f"[ModuleLoader] Attempting to call handle_message for module ID {module_id}") # Optional: uncomment for verbose message dispatch logging
                    module_instance.handle_message(connection, event, channel, nick, message)
            except Exception as e:
                # Retrieve module name for better logging if possible
                module_name = f"ID {module_id}"
                # We can get the name from the instance if it has one
                if hasattr(module_instance, 'name'):
                    module_name = module_instance.name
                logger.error(f"[ModuleLoader] Error in module {module_name} handling message: {e}\n{traceback.format_exc()}") # Added traceback


    def handle_command(self, connection, event, command, args, channel, nick):
        """Handle commands by passing them to the relevant loaded module instance based on trigger."""
        logger.info(f"[ModuleLoader] handle_command received: '{command}' with args {args} from {nick} in {channel}")
        
        # Strip any command prefix from the command
        processed_command = command.lower()
        while processed_command and processed_command[0] in '!@#':
            processed_command = processed_command[1:]
            
        # Check if the processed command matches any loaded module's trigger
        if processed_command in self.module_triggers:
            module_id = self.module_triggers[processed_command]
            module_instance = self.loaded_modules.get(module_id)

            if module_instance and hasattr(module_instance, 'handle_command'):
                try:
                    logger.info(f"[ModuleLoader] Dispatching command '{processed_command}' to module ID {module_id}")
                    # Pass the processed command (without prefix) to handle_command
                    module_instance.handle_command(connection, event, processed_command, args, channel, nick)
                except Exception as e:
                    module_name = f"ID {module_id}"
                    if hasattr(module_instance, 'name'):
                        module_name = module_instance.name
                    logger.error(f"[ModuleLoader] Error in module {module_name} handling command: {e}\n{traceback.format_exc()}")
            else:
                logger.warning(f"[ModuleLoader] Trigger for command '{processed_command}' found (module ID {module_id}), but module instance not found or handle_command missing on instance.")
        else:
            logger.info(f"[ModuleLoader] No module found in module_triggers for command: {processed_command}")