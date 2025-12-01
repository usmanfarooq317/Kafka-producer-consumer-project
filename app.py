from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import json
from datetime import datetime
import threading
import time
import logging
from kafka import KafkaProducer, KafkaConsumer
import atexit

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
        max_retries = 5
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt+1}/{max_retries} to connect to Kafka...")
                self.producer = KafkaProducer(
                    bootstrap_servers=KAFKA_BROKER,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    request_timeout_ms=10000
                )
                # Test connection
                self.producer.list_topics(timeout=10)
                logger.info("Kafka producer initialized successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize producer (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return False
            
    def send_message(self, data):
        try:
            if not self.producer:
                if not self.init_producer():
                    return {'success': False, 'error': 'Failed to connect to Kafka'}
            
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
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    logger.info(f"Attempt {attempt+1}/{max_retries} to start consumer...")
                    self.consumer = KafkaConsumer(
                        TOPIC,
                        bootstrap_servers=KAFKA_BROKER,
                        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                        auto_offset_reset='latest',
                        group_id='dashboard-group',
                        request_timeout_ms=10000
                    )
                    
                    self.running = True
                    logger.info("Kafka consumer started successfully")
                    
                    for message in self.consumer:
                        if not self.running:
                            break
                        data = message.value
                        socketio.emit('new_message', data)
                    break
                    
                except Exception as e:
                    logger.error(f"Consumer error (attempt {attempt+1}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(5)
                    else:
                        logger.error("Max retries reached for consumer")
                        break
                
        self.consumer_thread = threading.Thread(target=consume, daemon=True)
        self.consumer_thread.start()
    
    def stop(self):
        self.running = False
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        logger.info("Kafka manager stopped")

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
        'services': ['kafka', 'elasticsearch', 'kibana', 'dashboard']
    })

@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'connected', 'timestamp': datetime.now().isoformat()})

@socketio.on('send_message')
def handle_message(data):
    result = kafka_manager.send_message(data)
    emit('send_status', result)

def cleanup():
    kafka_manager.stop()

atexit.register(cleanup)

if __name__ == '__main__':
    # Wait for Kafka to be ready
    logger.info("Waiting for Kafka to be ready...")
    time.sleep(10)
    
    # Start consumer in background
    kafka_manager.start_consumer()
    
    # Start Flask app
    logger.info("Starting Flask app on http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)