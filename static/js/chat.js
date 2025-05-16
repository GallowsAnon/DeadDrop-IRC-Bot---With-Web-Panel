// This file is deprecated. All functionality has been moved to webchat.js
console.warn('chat.js is deprecated. Please use webchat.js instead.');

// Chat page JS
let lastMessages = [];
let lastUserList = [];

function renderMessages(messages) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) {
        console.error('Chat messages container not found');
        return;
    }
    
    chatMessages.innerHTML = '';
    if (!messages || messages.length === 0) {
        chatMessages.innerHTML = '<div class="text-muted text-center p-3">No messages yet</div>';
        return;
    }
    
    messages.forEach(msg => {
        const div = document.createElement('div');
        div.className = 'mb-2';
        div.innerHTML = `<span class="text-muted small">[${msg.timestamp}]</span> <strong>${msg.nick}</strong>: ${msg.message}`;
        chatMessages.appendChild(div);
    });
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderUserList(users) {
    const userList = document.getElementById('user-list');
    if (!userList) {
        console.error('User list container not found');
        return;
    }
    
    userList.innerHTML = '';
    if (!users || users.length === 0) {
        userList.innerHTML = '<li class="list-group-item text-muted text-center">No users</li>';
        return;
    }
    
    users.sort().forEach(nick => {
        const li = document.createElement('li');
        li.className = 'list-group-item';
        li.textContent = nick;
        userList.appendChild(li);
    });
}

function fetchMessages() {
    if (!channel) {
        console.debug('No channel selected, skipping message fetch');
        return;
    }
    
    fetch(`/api/get_messages?channel=${encodeURIComponent(channel)}`)
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
        .then(data => {
            console.debug(`Fetched ${data.messages?.length || 0} messages for ${channel}`);
            if (data.success) {
                if (JSON.stringify(data.messages) !== JSON.stringify(lastMessages)) {
                    renderMessages(data.messages);
                    lastMessages = data.messages;
                }
            } else {
                console.error('Failed to fetch messages:', data.error);
            }
        })
        .catch(error => console.error('Error fetching messages:', error));
}

function fetchUserList() {
    if (!channel) {
        console.debug('No channel selected, skipping user list fetch');
        return;
    }
    
    fetch(`/api/get_users?channel=${encodeURIComponent(channel)}`)
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
        .then(data => {
            console.debug(`Fetched ${data.users?.length || 0} users for ${channel}`);
            if (data.success) {
                if (JSON.stringify(data.users) !== JSON.stringify(lastUserList)) {
                    renderUserList(data.users);
                    lastUserList = data.users;
                }
            } else {
                console.error('Failed to fetch users:', data.error);
            }
        })
        .catch(error => console.error('Error fetching users:', error));
}

function sendMessage(msg) {
    if (!channel || !msg.trim()) return;
    
    fetch('/api/send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, channel })
    })
    .then(res => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
    })
    .then(data => {
        if (!data.success) {
            console.error('Failed to send message:', data.error);
            alert('Failed to send message: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error sending message:', error);
        alert('Error sending message: ' + error.message);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    console.debug('Chat page initialized for channel:', channel);
    
    const form = document.getElementById('chat-form');
    const input = document.getElementById('chat-input');
    
    if (form && input) {
        form.addEventListener('submit', e => {
            e.preventDefault();
            const msg = input.value.trim();
            if (msg) {
                sendMessage(msg);
                input.value = '';
            }
        });
    } else {
        console.error('Chat form or input not found');
    }
    
    // Initial fetch
    fetchMessages();
    fetchUserList();
    
    // Set up polling
    setInterval(fetchMessages, 1500);
    setInterval(fetchUserList, 2000);
    
    // Set up socket.io event handlers
    const socket = io();
    socket.on('user_list_update', function(data) {
        console.debug('Received user list update:', data);
        if (data.channel === channel) {
            renderUserList(data.users);
            lastUserList = data.users;
        }
    });
    
    socket.on('message_update', function(data) {
        console.debug('Received message update:', data);
        if (data.channel === channel) {
            lastMessages.push(data.message);
            if (lastMessages.length > 100) {
                lastMessages.shift();
            }
            renderMessages(lastMessages);
        }
    });
}); 