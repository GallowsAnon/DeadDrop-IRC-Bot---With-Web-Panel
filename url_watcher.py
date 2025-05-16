import re
import requests
import urllib.parse
from bs4 import BeautifulSoup
from extensions import socketio, db, app
from models import URLWatcherSettings
import logging

logger = logging.getLogger(__name__)

IRC_COLORS = {
    'red': '\x0304',
    'blue': '\x0302',
    'bold': '\x02',
    'reset': '\x0f',
}

class URLWatcher:
    def __init__(self, bot):
        self.bot = bot

    def get_settings(self):
        with app.app_context():
            settings = URLWatcherSettings.query.first()
            if not settings:
                settings = URLWatcherSettings()
                db.session.add(settings)
                db.session.commit()
            return settings

    def _get_title(self, url):
        try:
            response = requests.get(url, timeout=(5, 5))
            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.get_text().strip()
        except Exception as e:
            logger.warning(f"Error fetching URL {url}: {e}")
        return None

    def _get_youtube_video_info(self, url):
        video_info = {'title': 'N/A', 'duration': 'N/A', 'view_count': 'N/A', 'likes': 'N/A', 'dislikes': 'N/A'}
        try:
            parsed_url = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed_url.query)
            if 'v' in query:
                video_id = query['v'][0]
                with app.app_context():
                    api_key = self.get_settings().youtube_api_key or ''
                api_url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,statistics&id={video_id}&key={api_key}'
                response = requests.get(api_url, timeout=(5, 5))
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items')
                    if items:
                        video_item = items[0]
                        statistics = video_item.get('statistics', {})
                        snippet = video_item.get('snippet', {})
                        content_details = video_item.get('contentDetails', {})
                        
                        # Format duration (PT1H2M3S -> 01:02:03)
                        duration = content_details.get('duration', 'PT0S')
                        duration = duration.replace('PT', '')
                        hours = '00'
                        minutes = '00'
                        seconds = '00'
                        if 'H' in duration:
                            hours, duration = duration.split('H')
                            hours = hours.zfill(2)
                        if 'M' in duration:
                            minutes, duration = duration.split('M')
                            minutes = minutes.zfill(2)
                        if 'S' in duration:
                            seconds = duration.replace('S', '').zfill(2)
                        formatted_duration = f"{hours}:{minutes}:{seconds}"
                        
                        # Format view count
                        view_count = statistics.get('viewCount', '0')
                        if view_count.isdigit():
                            view_count = int(view_count)
                            if view_count >= 1000000:
                                view_count = f"{view_count/1000000:.1f}M"
                            elif view_count >= 1000:
                                view_count = f"{view_count/1000:.1f}K"
                        
                        video_info['title'] = snippet.get('title', 'N/A')
                        video_info['duration'] = formatted_duration
                        video_info['view_count'] = view_count
                        video_info['likes'] = statistics.get('likeCount', 'N/A')
                        video_info['dislikes'] = statistics.get('dislikeCount', 'N/A')
        except Exception as e:
            logger.warning(f"Error fetching YouTube info for {url}: {e}")
        return video_info

    def handle_message(self, channel, nick, message):
        urls = re.findall(r'(https?://\S+)', message)
        if not urls:
            return
        with app.app_context():
            settings = self.get_settings()
            for url in urls:
                parsed_url = urllib.parse.urlparse(url)
                domain = parsed_url.netloc
                # IRC color codes
                irc_url_color = f'\x03{settings.url_color}' if settings.url_color else ''
                irc_youtube_color = f'\x03{settings.youtube_color}' if settings.youtube_color else ''
                irc_bold = '\x02'
                irc_reset = '\x0f'
                # Convert IRC colors to hex for webchat
                irc_to_hex = {
                    '00': '#FFFFFF', '01': '#000000', '02': '#00007F', '03': '#009300',
                    '04': '#FF0000', '05': '#7F0000', '06': '#9C009C', '07': '#FC7F00',
                    '08': '#FFFF00', '09': '#00FC00', '10': '#009393', '11': '#00FFFF',
                    '12': '#0000FC', '13': '#FF00FF', '14': '#7F7F7F', '15': '#D2D2D2'
                }
                web_url_color = irc_to_hex.get(settings.url_color, '#2196f3')
                web_youtube_color = irc_to_hex.get(settings.youtube_color, '#e91e63')
                # --- YouTube ---
                if 'youtube.com' in domain or 'youtu.be' in domain:
                    video_info = self._get_youtube_video_info(url)
                    # IRC formatted message
                    irc_output = f"{irc_youtube_color}{irc_bold}{video_info['title']}{irc_reset} {irc_bold}::{irc_reset} {irc_bold}{video_info['duration']}{irc_reset} {irc_bold}::{irc_reset} {irc_bold}{video_info['view_count']}{irc_reset} {irc_bold}::{irc_reset} {irc_bold}+{video_info['likes']} -{video_info['dislikes']}{irc_reset}"
                    # Send to IRC
                    self.bot.connection.privmsg(channel, irc_output)
                    # Send to webchat with HTML formatting
                    socketio.emit('webchat_message', {
                        'nick': self.bot.nick,
                        'message': f"<span style='color:{web_youtube_color};font-weight:bold'>{video_info['title']}</span> <b>::</b> <b>{video_info['duration']}</b> <b>::</b> <b>{video_info['view_count']}</b> <b>::</b> <b>+{video_info['likes']} -{video_info['dislikes']}</b>",
                        'timestamp': self.bot.now_str(),
                        'channel': channel
                    }, room=channel)
                else:
                    title = self._get_title(url)
                    if title:
                        # IRC formatted message
                        irc_output = f"{irc_url_color}{irc_bold}{title}{irc_reset}"
                        # Send to IRC
                        self.bot.connection.privmsg(channel, irc_output)
                        # Send to webchat with HTML formatting
                        socketio.emit('webchat_message', {
                            'nick': self.bot.nick,
                            'message': f"<span style='color:{web_url_color};font-weight:bold'>{title}</span>",
                            'timestamp': self.bot.now_str(),
                            'channel': channel
                        }, room=channel) 