import logging
import openai
import google.generativeai as genai
from models import AISettings
import time
import threading

logger = logging.getLogger(__name__)

def send_delayed_message(bot, connection, channel, message, delay):
    """Send a message after a delay."""
    time.sleep(delay)
    bot.send_message(connection, channel, message)

def get_ai_response(message, conversation=None):
    """Get a response from either OpenAI or Gemini."""
    ai_settings = AISettings.query.first()
    if not ai_settings or not ai_settings.is_enabled:
        logger.warning("AI settings not found or AI is not enabled")
        return None
    
    logger.info(f"Getting AI response using provider: {ai_settings.ai_provider}")
    
    if ai_settings.ai_provider == 'openai':
        if not ai_settings.openai_api_key:
            logger.warning("OpenAI API key is missing")
            return None
        try:
            client = openai.OpenAI(api_key=ai_settings.openai_api_key)
            messages = [{"role": "system", "content": ai_settings.system_prompt}]
            if conversation and conversation.is_active():
                messages.extend(conversation.messages)
            messages.append({"role": "user", "content": message})
            
            logger.info(f"Sending request to OpenAI with messages: {messages}")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            result = response.choices[0].message.content.strip()
            logger.info(f"Received response from OpenAI: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting OpenAI response: {e}")
            return None
    else:  # gemini
        if not ai_settings.gemini_api_key:
            logger.warning("Gemini API key is missing")
            return None
        try:
            genai.configure(api_key=ai_settings.gemini_api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Build conversation history
            messages = []
            if conversation and conversation.is_active():
                for msg in conversation.messages:
                    messages.append(msg["content"])
            
            # Join messages with newlines and add system prompt at the start
            prompt = ai_settings.system_prompt + "\n\n" + "\n".join(messages) + "\n" + message
            
            logger.info(f"Sending request to Gemini with prompt: {prompt}")
            response = model.generate_content(prompt)
            
            if response and response.text:
                result = response.text.strip()
                logger.info(f"Received response from Gemini: {result}")
                return result
            elif response and response.parts:
                try:
                    # Attempt to extract text from parts
                    result = "".join([part.text for part in response.parts if hasattr(part, 'text')]).strip()
                    if result:
                        logger.info(f"Received response from Gemini (from parts): {result}")
                        return result
                    else:
                        logger.error("Gemini response parts did not contain text")
                        return None
                except Exception as part_e:
                    logger.error(f"Error extracting text from Gemini response parts: {part_e}")
                    return None
            else:
                logger.error("Unexpected response format from Gemini API: neither text nor parts found")
                return None
        except Exception as e:
            logger.error(f"Error getting Gemini response: {e}")
            return None 