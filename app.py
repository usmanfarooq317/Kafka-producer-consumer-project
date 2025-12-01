from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import json
from datetime import datetime
import threading
import time
import logging
from kafka import KafkaProducer, KafkaConsumer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
socketio = SocketIO(app, cors_allowed_origins="*")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka setup
KAFKA_BROKER = 'kafka:9092'
TOPIC = 'dashboard-messages'

class KafkaManager:
    def __init__(self):
        self.producer = None
        self.consumer = None
        self.running = False
        
    def init_producer(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logger.info("Kafka producer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize producer: {e}")
            
    def send_message(self, data):
        try:
            if not self.producer:
                self.init_producer()
            
            data['timestamp'] = datetime.now().isoformat()
            future = self.producer.send(TOPIC, value=data)
            result = future.get(timeout=10)
            
            socketio.emit('new_message', data)
            return {
                'success': True,
                'topic': result.topic,
                'partition': result.partition,
                'offset': result.offset
            }
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {'success': False, 'error': str(e)}
    
    def start_consumer(self):
        def consume():
            try:
                self.consumer = KafkaConsumer(
                    TOPIC,
                    bootstrap_servers=KAFKA_BROKER,
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    auto_offset_reset='latest',
                    group_id='dashboard-group'
                )
                
                self.running = True
                logger.info("Kafka consumer started")
                
                for message in self.consumer:
                    if not self.running:
                        break
                    data = message.value
                    socketio.emit('new_message', data)
                    
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                
        self.consumer_thread = threading.Thread(target=consume, daemon=True)
        self.consumer_thread.start()
    
    def stop_consumer(self):
        self.running = False
        if self.consumer:
            self.consumer.close()
        logger.info("Kafka consumer stopped")

kafka_manager = KafkaManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'kafka': 'connected',
        'services': ['kafka', 'elasticsearch', 'kibana']
    })

@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'connected'})

@socketio.on('send_message')
def handle_message(data):
    result = kafka_manager.send_message(data)
    emit('send_status', result)

if __name__ == '__main__':
    # Start consumer in background
    time.sleep(5)  # Wait for Kafka to be ready
    kafka_manager.start_consumer()
    
    # Start Flask app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)