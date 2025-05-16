// Webchat JS: Connects to backend via SocketIO and updates UI

document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const statusDiv = document.getElementById('webchat-status');
    const channelList = document.getElementById('channel-list');
    const userList = document.getElementById('user-list');
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const topicBar = document.getElementById('topic-bar');
    const topicText = document.getElementById('topic-text');
    const joinChannelBtn = document.getElementById('join-channel-btn');
    const joinChannelModal = document.getElementById('join-channel-modal');
    const joinChannelInput = document.getElementById('join-channel-input');
    const joinChannelCancel = document.getElementById('join-channel-cancel');
    const joinChannelConfirm = document.getElementById('join-channel-confirm');
    const partChannelBtn = document.getElementById('part-channel-btn');

    let currentChannel = window.initialChannel || null;
    let botNick = null;
    const channelMessages = {};

    // --- SocketIO Events ---
    socket.on('webchat_status', function(data) {
        if (data.connected) {
            statusDiv.textContent = 'Bot connected. You can chat!';
            if (data.nick) botNick = data.nick;
            // If we have an initial channel, join it
            if (currentChannel) {
                socket.emit('webchat_join_channel', { channel: currentChannel });
            }
        } else {
            statusDiv.textContent = 'Bot is not connected. Webchat is unavailable.';
        }
    });

    socket.on('webchat_channels', function(data) {
        console.log('Received channel list update:', data.channels);
        channelList.innerHTML = '';
        data.channels.forEach(channel => {
            const li = document.createElement('li');
            li.textContent = channel;
            li.className = 'cursor-pointer px-4 py-2 hover:bg-indigo-100';
            li.onclick = function() {
                currentChannel = channel;
                Array.from(channelList.children).forEach(li2 => {
                    li2.classList.toggle('bg-indigo-200', li2.textContent === currentChannel);
                });
                socket.emit('webchat_get_topic', { channel: currentChannel });
                socket.emit('webchat_users_request', { channel: currentChannel });
                socket.emit('webchat_messages_request', { channel: currentChannel });
                renderMessagesForCurrentChannel();
            };
            if (channel === currentChannel) {
                li.classList.add('bg-indigo-200');
            }
            channelList.appendChild(li);
        });
    });

    socket.on('webchat_users', function(data) {
        console.log('Received userlist update:', data.users);
        userList.innerHTML = '';
        const modePriority = {'~': 0, '&': 1, '@': 2, '%': 3, '+': 4, '': 5};
        data.users.sort((a, b) => {
            const modeA = modePriority[a.mode] !== undefined ? modePriority[a.mode] : 99;
            const modeB = modePriority[b.mode] !== undefined ? modePriority[b.mode] : 99;
            if (modeA !== modeB) return modeA - modeB;
            return a.nick.localeCompare(b.nick, undefined, {sensitivity: 'base'});
        });
        data.users.forEach(user => {
            const li = document.createElement('li');
            let badgeClass = 'badge-none';
            if (user.mode === '@') badgeClass = 'badge-op';
            else if (user.mode === '+') badgeClass = 'badge-voice';
            else if (user.mode === '%') badgeClass = 'badge-halfop';
            else if (user.mode === '&') badgeClass = 'badge-admin';
            else if (user.mode === '~') badgeClass = 'badge-owner';
            li.innerHTML = `<span class="badge ${badgeClass}"></span>${user.nick}`;
            li.className = 'px-4 py-1 cursor-pointer hover:bg-indigo-100 user-list-item';
            li.onclick = function() {
                if (user.nick !== botNick) {
                    socket.emit('webchat_open_query', { nick: user.nick });
                }
            };
            userList.appendChild(li);
        });
    });

    socket.on('webchat_messages', function(data) {
        // Store messages for the current channel
        if (currentChannel) {
            channelMessages[currentChannel] = data.messages;
            renderMessagesForCurrentChannel();
        }
    });

    socket.on('webchat_message', function(msg) {
        // Append message to the correct channel
        if (!msg || !currentChannel) return;
        // Use msg.channel if present, else fallback to currentChannel
        const chan = msg.channel || currentChannel;
        if (!channelMessages[chan]) channelMessages[chan] = [];
        channelMessages[chan].push(msg);
        // Only render if we're viewing this channel
        if (chan === currentChannel) renderMessagesForCurrentChannel();
    });

    function renderMessagesForCurrentChannel() {
        chatMessages.innerHTML = '';
        const msgs = channelMessages[currentChannel] || [];
        msgs.forEach(msg => {
            appendMessage(msg.nick, msg.message, msg.timestamp);
        });
    }

    socket.on('webchat_topic', function(data) {
        if (data.channel === currentChannel) {
            topicText.textContent = data.topic || 'No topic set';
        }
    });

    function appendMessage(nick, message, timestamp) {
        const div = document.createElement('div');
        if (!nick) {
            // System message (join/part or URL info)
            div.innerHTML = `<span class="text-xs text-gray-400">[${timestamp}]</span> <span class="italic text-gray-500">${message}</span>`;
        } else {
            // Generate a consistent color for the nick
            const nickColor = getNickColor(nick);
            div.innerHTML = `<span class="text-xs text-gray-400">[${timestamp}]</span> <span class="font-bold" style="color: ${nickColor}">${nick}</span>: <span>${message}</span>`;
        }
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Function to generate a consistent color for a nick
    function getNickColor(nick) {
        // Simple hash function to generate a number from the nick
        let hash = 0;
        for (let i = 0; i < nick.length; i++) {
            hash = nick.charCodeAt(i) + ((hash << 5) - hash);
        }
        
        // Convert the hash to a color
        const hue = Math.abs(hash % 360); // Use the full color spectrum
        const saturation = 70 + Math.abs(hash % 30); // 70-100% saturation
        const lightness = 40 + Math.abs(hash % 20); // 40-60% lightness
        
        return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
    }

    // --- Sending messages ---
    sendBtn.onclick = sendMessage;
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') sendMessage();
    });

    function sendMessage() {
        const msg = chatInput.value.trim();
        if (!msg || !currentChannel) return;
        socket.emit('webchat_send_message', { channel: currentChannel, message: msg });
        chatInput.value = '';
    }

    // --- Join channel event ---
    socket.on('webchat_joined_channel', function(data) {
        currentChannel = data.channel;
        Array.from(channelList.children).forEach(li2 => {
            li2.classList.toggle('bg-indigo-200', li2.textContent === currentChannel);
        });
        socket.emit('webchat_get_topic', { channel: currentChannel });
        socket.emit('webchat_users_request', { channel: currentChannel });
        socket.emit('webchat_messages_request', { channel: currentChannel });
        // Render messages for the new channel if already cached
        renderMessagesForCurrentChannel();
    });

    // --- Join Channel Modal Logic ---
    joinChannelBtn.onclick = function() {
        joinChannelModal.classList.remove('hidden');
        joinChannelInput.value = '';
        joinChannelInput.focus();
    };
    joinChannelCancel.onclick = function() {
        joinChannelModal.classList.add('hidden');
    };
    joinChannelConfirm.onclick = function() {
        const chan = joinChannelInput.value.trim();
        if (chan) {
            socket.emit('webchat_join_channel', { channel: chan });
            joinChannelModal.classList.add('hidden');
            // Switch to the new channel immediately
            currentChannel = chan;
            // Update channel list highlighting
            Array.from(channelList.children).forEach(li => {
                li.classList.toggle('bg-indigo-200', li.textContent === currentChannel);
            });
        }
    };
    joinChannelInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') joinChannelConfirm.onclick();
    });

    // --- Part Channel ---
    partChannelBtn.onclick = function() {
        if (currentChannel) {
            socket.emit('webchat_part_channel', { channel: currentChannel });
        }
    };

    // --- Handle Query (Private Message) Open ---
    socket.on('webchat_opened_query', function(data) {
        currentChannel = data.nick;
        // Highlight nothing in channel list, show query in topic bar
        Array.from(channelList.children).forEach(li => li.classList.remove('bg-indigo-200'));
        topicBar.textContent = `Private chat with ${data.nick}`;
        chatMessages.innerHTML = '';
        (data.messages || []).forEach(msg => appendMessage(msg.nick, msg.message, msg.timestamp));
    });

    // Request initial state
    socket.emit('webchat_init');
}); 