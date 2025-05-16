document.addEventListener('DOMContentLoaded', function() {
    // Connect to WebSocket
    const socket = io();
    
    // Handle status updates
    socket.on('status_update', function(data) {
        // Update connection status
        const statusElements = document.querySelectorAll('[data-status-indicator]');
        statusElements.forEach(element => {
            if (data.connected) {
                element.innerHTML = '<span class="text-green-600 font-medium">Connected</span>';
            } else {
                element.innerHTML = '<span class="text-red-600 font-medium">Disconnected</span>';
            }
        });

        // Update server info
        const serverElements = document.querySelectorAll('[data-server-info]');
        serverElements.forEach(element => {
            element.textContent = `${data.server}:${data.port}`;
        });

        // Update connect/disconnect buttons
        const connectBtn = document.querySelector('[data-connect-btn]');
        const disconnectBtn = document.querySelector('[data-disconnect-btn]');
        
        if (connectBtn && disconnectBtn) {
            if (data.connected) {
                connectBtn.disabled = true;
                connectBtn.classList.add('bg-gray-400', 'cursor-not-allowed');
                connectBtn.classList.remove('bg-green-600', 'hover:bg-green-700');
                
                disconnectBtn.disabled = false;
                disconnectBtn.classList.remove('bg-gray-400', 'cursor-not-allowed');
                disconnectBtn.classList.add('bg-red-600', 'hover:bg-red-700');
            } else {
                connectBtn.disabled = false;
                connectBtn.classList.remove('bg-gray-400', 'cursor-not-allowed');
                connectBtn.classList.add('bg-green-600', 'hover:bg-green-700');
                
                disconnectBtn.disabled = true;
                disconnectBtn.classList.add('bg-gray-400', 'cursor-not-allowed');
                disconnectBtn.classList.remove('bg-red-600', 'hover:bg-red-700');
            }
        }

        // Update status text in bot control section
        const statusText = document.querySelector('.mt-2 .text-sm.text-gray-500');
        if (statusText) {
            if (data.connected) {
                statusText.innerHTML = 'Status: <span class="text-green-600 font-medium">Connected</span>';
            } else {
                statusText.innerHTML = 'Status: <span class="text-red-600 font-medium">Disconnected</span>';
            }
        }
    });
    
    // Handle form submissions
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
            }
        });
    });

    // Handle flash messages
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.display = 'none';
        }, 5000);
    });

    // Handle AI connection test
    const testAiButton = document.getElementById('test-ai-connection');
    const aiTestResult = document.getElementById('ai-test-result');
    const aiTestMessage = document.getElementById('ai-test-message');

    if (testAiButton) {
        testAiButton.addEventListener('click', function() {
            // Disable button and show loading state
            testAiButton.disabled = true;
            testAiButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Testing...';
            
            // Make API call to test AI connection
            fetch('/ai_settings/test_connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                // Show result
                aiTestResult.classList.remove('hidden');
                if (data.success) {
                    aiTestMessage.textContent = data.message;
                    aiTestMessage.className = 'text-green-600';
                } else {
                    aiTestMessage.textContent = data.message;
                    aiTestMessage.className = 'text-red-600';
                }
            })
            .catch(error => {
                aiTestResult.classList.remove('hidden');
                aiTestMessage.textContent = 'Error testing connection: ' + error.message;
                aiTestMessage.className = 'text-red-600';
            })
            .finally(() => {
                // Reset button state
                testAiButton.disabled = false;
                testAiButton.innerHTML = '<i class="fas fa-plug mr-2"></i>Test AI Connection';
            });
        });
    }
}); 