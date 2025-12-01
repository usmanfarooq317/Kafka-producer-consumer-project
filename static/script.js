// Initialize Socket.IO connection
const socket = io();

// DOM Elements
const messageForm = document.getElementById('message-form');
const messagesContainer = document.getElementById('messages-container');
const messageCount = document.getElementById('message-count');
const valueSlider = document.getElementById('value');
const valueDisplay = document.getElementById('value-display');
const clearBtn = document.getElementById('clear-messages');
const pauseBtn = document.getElementById('pause-messages');
const chartCanvas = document.getElementById('messageChart');

// Statistics
let stats = {
    total: 0,
    info: 0,
    alert: 0,
    warning: 0,
    success: 0,
    error: 0
};

// Chart instance
let messageChart = null;
let isPaused = false;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initializeChart();
    setupEventListeners();
    updateValueDisplay();
    checkSystemStatus();
    
    // Periodically check system status
    setInterval(checkSystemStatus, 30000);
});

// Chart.js initialization
function initializeChart() {
    const ctx = chartCanvas.getContext('2d');
    messageChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Messages per Minute',
                data: [],
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Event Listeners
function setupEventListeners() {
    // Message form submission
    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        sendMessage();
    });

    // Value slider
    valueSlider.addEventListener('input', updateValueDisplay);

    // Clear messages button
    clearBtn.addEventListener('click', clearMessages);

    // Pause messages button
    pauseBtn.addEventListener('click', togglePause);

    // Socket.IO event listeners
    socket.on('connect', function() {
        console.log('WebSocket connected');
        updateIndicator('ws-indicator', true, 'Connected');
    });

    socket.on('disconnect', function() {
        console.log('WebSocket disconnected');
        updateIndicator('ws-indicator', false, 'Disconnected');
    });

    socket.on('new_message', function(data) {
        if (!isPaused) {
            addMessageToUI(data);
            updateStats(data.category);
            updateChart();
        }
    });

    socket.on('send_status', function(data) {
        updateSendStatus(data);
    });
}

// Update value display
function updateValueDisplay() {
    valueDisplay.textContent = valueSlider.value;
}

// Send message to server
function sendMessage() {
    const sender = document.getElementById('sender').value;
    const category = document.getElementById('category').value;
    const message = document.getElementById('message').value;
    const value = parseInt(valueSlider.value);

    if (!message.trim()) {
        alert('Please enter a message');
        return;
    }

    const messageData = {
        timestamp: new Date().toISOString(),
        sender: sender,
        category: category,
        message: message,
        value: value
    };

    // Emit to server via Socket.IO
    socket.emit('send_message', messageData);

    // Clear message input
    document.getElementById('message').value = '';
}

// Update send status display
function updateSendStatus(data) {
    const statusDiv = document.getElementById('send-status');
    
    if (data.success) {
        statusDiv.innerHTML = `
            <div style="color: #28a745;">
                <i class="fas fa-check-circle"></i>
                Message sent successfully!
                <small>Topic: ${data.topic}, Partition: ${data.partition}, Offset: ${data.offset}</small>
            </div>
        `;
    } else {
        statusDiv.innerHTML = `
            <div style="color: #dc3545;">
                <i class="fas fa-exclamation-circle"></i>
                Failed to send message: ${data.error}
            </div>
        `;
    }

    // Clear status after 5 seconds
    setTimeout(() => {
        statusDiv.innerHTML = '';
    }, 5000);
}

// Add message to UI
function addMessageToUI(data) {
    // Remove "no messages" placeholder if present
    const noMessages = document.querySelector('.no-messages');
    if (noMessages) {
        noMessages.remove();
    }

    // Create message element
    const messageElement = document.createElement('div');
    messageElement.className = 'message-item';
    
    const time = new Date(data.timestamp).toLocaleTimeString();
    
    messageElement.innerHTML = `
        <div class="message-header">
            <span class="message-sender">${data.sender}</span>
            <span class="message-time">${time}</span>
        </div>
        <div class="message-content">${data.message}</div>
        <div class="message-footer">
            <span class="message-category category-${data.category}">${data.category.toUpperCase()}</span>
            <span>Value: ${data.value}</span>
        </div>
    `;

    // Add to container (at the top)
    messagesContainer.prepend(messageElement);

    // Update message count
    stats.total++;
    messageCount.textContent = stats.total;

    // Limit messages to 100
    if (messagesContainer.children.length > 100) {
        messagesContainer.removeChild(messagesContainer.lastChild);
    }
}

// Update statistics
function updateStats(category) {
    stats[category]++;
    
    // Update UI
    document.getElementById('info-count').textContent = stats.info;
    document.getElementById('alert-count').textContent = stats.alert;
    document.getElementById('warning-count').textContent = stats.warning;
    document.getElementById('success-count').textContent = stats.success;
}

// Update chart
function updateChart() {
    const now = new Date();
    const timeLabel = now.getHours() + ':' + now.getMinutes().toString().padStart(2, '0');
    
    messageChart.data.labels.push(timeLabel);
    messageChart.data.datasets[0].data.push(1);
    
    // Keep only last 20 data points
    if (messageChart.data.labels.length > 20) {
        messageChart.data.labels.shift();
        messageChart.data.datasets[0].data.shift();
    }
    
    messageChart.update();
}

// Clear all messages
function clearMessages() {
    messagesContainer.innerHTML = `
        <div class="no-messages">
            <i class="fas fa-inbox"></i>
            <p>No messages yet. Send a message to see it here!</p>
        </div>
    `;
    stats.total = 0;
    messageCount.textContent = '0';
}

// Toggle pause state
function togglePause() {
    isPaused = !isPaused;
    const icon = pauseBtn.querySelector('i');
    const text = pauseBtn.querySelector('span');
    
    if (isPaused) {
        icon.className = 'fas fa-play';
        text.textContent = ' Resume';
        pauseBtn.classList.add('resumed');
    } else {
        icon.className = 'fas fa-pause';
        text.textContent = ' Pause';
        pauseBtn.classList.remove('resumed');
    }
}

// Update the checkSystemStatus function in static/script.js
async function checkSystemStatus() {
    try {
        // Check Elasticsearch (port 9201)
        const esResponse = await fetch('http://localhost:9201');
        if (esResponse.ok) {
            updateIndicator('es-indicator', true, 'Running');
        } else {
            updateIndicator('es-indicator', false, 'Not Responding');
        }
    } catch (error) {
        updateIndicator('es-indicator', false, 'Offline');
    }

    try {
        // Check Kibana (port 5602)
        const kibanaResponse = await fetch('http://localhost:5602');
        if (kibanaResponse.ok) {
            updateIndicator('kibana-indicator', true, 'Running');
        } else {
            updateIndicator('kibana-indicator', false, 'Not Responding');
        }
    } catch (error) {
        updateIndicator('kibana-indicator', false, 'Offline');
    }
    
    // Add Kafka status check through our dashboard
    try {
        const kafkaResponse = await fetch('http://localhost:5001/api/health');
        if (kafkaResponse.ok) {
            updateIndicator('kafka-indicator', true, 'Running');
        } else {
            updateIndicator('kafka-indicator', false, 'Not Responding');
        }
    } catch (error) {
        updateIndicator('kafka-indicator', false, 'Offline');
    }
}

// Update status indicator
function updateIndicator(elementId, isActive, text) {
    const element = document.getElementById(elementId);
    const icon = element.querySelector('i');
    
    if (isActive) {
        element.classList.remove('inactive');
        element.classList.add('active');
        icon.style.color = '#28a745';
    } else {
        element.classList.remove('active');
        element.classList.add('inactive');
        icon.style.color = '#dc3545';
    }
    
    // Update text (remove icon and existing text)
    const span = element.querySelector('span:not(.fas)');
    if (span) {
        span.textContent = text;
    } else {
        // If no span exists, create one
        const textSpan = document.createElement('span');
        textSpan.textContent = text;
        element.appendChild(textSpan);
    }
}