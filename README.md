# DeadDrop IRC Bot & Web Management Portal

A powerful IRC bot and web management solution that combines advanced IRC functionality with an intuitive web interface for complete control and monitoring.

![DeadDrop Bot Overview](https://i.imgur.com/FzW8jql.png)

## 🌟 Key Features

### Known Bugs
- **Disconnect/Connect**: Bot has an issue where when disconnecting from a network via he webpanel, the UI doesn't correctly update (In progress)
- **Chanserv messages**: Chanserv messages are not persistent in webchat, this should be an easy fix

### Recent Bug Fixes
- **Crash On Kick**: Implemented a tiered kicking sysyem with warnings and a frontend method to clear user warnings. Bot will no longer kick anyone VOP and above for spam or caps. Or Channel Management can be disabled per channel.

### IRC Bot Capabilities
- **Bouncer Functionality**: Seamlessly maintain connections and message history
- **NickServ Integration**: Automatic identification and registration, may need alterations for other networks. This will be tested in future builds.
- **Channel Management**: Auto-join channels and maintain presence
- **Message Handling**: Process and respond to various IRC commands
- **Custom Commands**: Extensible command system for custom functionality
- **URL Parsing**: Automatic detection and processing of URLs in chat
  - Title extraction
  - Content preview
  - Link validation
  - Custom URL handlers

### AI Integration
- **ChatGPT Integration**: Natural language processing and responses
- **Gemini Integration**: Natural language processing and responses
- **Context-Aware Conversations**: Maintain conversation context
- **Custom AI Prompts**: Configurable AI behavior per channel
- **AI Command System**: Direct AI interactions through commands
- **Response Filtering**: Control AI response content and format with Hot Loading

### Module System
- **Dynamic Module Loading**: Hot-reload modules without restart
- **Custom Module Creation**: Easy-to-use module development framework with AI Helper
- **Module Management**: Enable/disable modules through web interface
- **Module Configuration**: Per-module settings and customization
- **Event System**: Subscribe to bot events for custom functionality
- **API Integration**: Connect external services through modules

### Web Management Portal
- **Real-time Monitoring**: Live view of bot status and activities
- **Configuration Management**: Easy-to-use interface for bot settings
- **User Authentication**: Secure access control system
- **Channel Management**: Add/remove channels and configure settings
- **Log Viewer**: Access and search through bot logs
- **User Management**: Control access levels and permissions
- **Module Dashboard**: Manage and configure bot modules
- **AI Settings**: Configure AI behavior and responses

### WebChat Interface
- **Browser-Based Chat**: Access IRC through web interface
- **Real-time Updates**: Instant message delivery
- **Channel Management**: Join/leave channels through web interface
- **Private Messaging**: Direct message support
- **File Sharing**: Upload and share files
- **Mobile Responsive**: Access from any device
- **Theme Support**: Customizable chat appearance

![Web Management Interface](https://i.imgur.com/AxoKemt.png)

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- Modern web browser for the management interface
- IRC network access

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/GallowsAnon/deaddrop.git
   cd deaddrop-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the application:
   ```bash
   python app.py
   ```

### Default Access
- Web Interface: `http://localhost:5000`
- You will be prompted on first run to create a new user or in the event that no users are in the database

![Login Screen](https://i.imgur.com/1Wf9298.png)

## 📋 Configuration

### Bot Configuration
- IRC Network Settings
- NickServ Credentials
- Channel Auto-join List
- Command Prefixes
- Logging Levels
- AI Integration Settings
- Module Configuration
- URL Parser Settings

### Web Portal Settings
- Port Configuration
- SSL/TLS Settings
- Session Management
- Database Connection
- WebChat Configuration
- Module Management
- AI Response Settings

![Configuration Panel](https://i.imgur.com/92PliU9.png)

## 🛠️ Project Structure

```
deaddrop-bot/
├── app.py              # Main application entry point
├── irc_bot.py         # IRC bot implementation
├── irc_bouncer.py     # IRC bouncer functionality
├── models.py          # Database models
├── config.py          # Configuration file
├── init_db.py         # Database initialization
├── requirements.txt   # Python dependencies
├── modules/          # Bot modules directory
│   ├── ai/           # AI-related modules
│   ├── url/          # URL parsing modules
│   └── custom/       # Custom user modules
├── templates/         # Web interface templates
│   ├── dashboard.html
│   ├── login.html
│   ├── settings.html
│   └── webchat.html
└── static/           # Static web assets
    ├── css/
    ├── js/
    └── img/
```

## 🔒 Security Features

- Encrypted password storage
- Session management
- Rate limiting *Coming Soon*
- IP-based access control *Coming Soon*
- SSL/TLS support

![Security Settings](https://i.imgur.com/AxoKemt.png)

## 📊 Monitoring & Logging

- Real-time bot status
- Connection statistics
- Channel activity logs
- Error tracking
- Performance metrics *Coming Soon*

![Monitoring Dashboard](https://i.imgur.com/FzW8jql.png)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Thanks to all contributors
- Inspired by various IRC bot projects
- Built with modern web technologies

---

For support, feature requests, or bug reports, please open an issue on GitHub. 