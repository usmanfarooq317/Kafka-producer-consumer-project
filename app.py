from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import json
from datetime import datetime, timezone
import threading
import time
import logging
from kafka import KafkaProducer, KafkaConsumer
from elasticsearch import Elasticsearch

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
socketio = SocketIO(app, cors_allowed_origins="*")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka setup
KAFKA_BROKER = 'kafka:9092'
TOPIC = 'dashboard-messages'

# Elasticsearch setup
es = Elasticsearch(['http://elasticsearch:9200'])

class KafkaManager:
    def __init__(self):
        self.producer = None
        self.consumer = None
        self.running = False
        
    def init_producer(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                request_timeout_ms=10000
            )
            logger.info("Kafka producer initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize producer: {e}")
            return False
    
    def send_to_elasticsearch(self, data):
        """Send data directly to Elasticsearch"""
        try:
            # Create index name with date
            index_name = f"kafka-dashboard-{datetime.now().strftime('%Y.%m.%d')}"
            
            # Index the document
            response = es.index(
                index=index_name,
                document=data
            )
            logger.info(f"Data sent to Elasticsearch: {response['_id']}")
            return response
        except Exception as e:
            logger.error(f"Failed to send to Elasticsearch: {e}")
            return None
            
    def send_message(self, data):
        try:
            if not self.producer:
                if not self.init_producer():
                    return {'success': False, 'error': 'Failed to connect to Kafka'}
            
            data['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            # Send to Kafka
            future = self.producer.send(TOPIC, value=data)
            result = future.get(timeout=10)
            
            # Also send directly to Elasticsearch as backup
            es_result = self.send_to_elasticsearch(data)
            
            # Broadcast to all connected clients
            socketio.emit('new_message', data)
            
            return {
                'success': True,
                'topic': result.topic,
                'partition': result.partition,
                'offset': result.offset,
                'elasticsearch_id': es_result['_id'] if es_result else None
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
                    # Broadcast new message to all clients
                    socketio.emit('new_message', data)
                    
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                
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
    # Check all services
    kafka_status = 'connected' if kafka_manager.producer else 'disconnected'
    
    try:
        es_info = es.info()
        elasticsearch_status = 'connected'
    except:
        elasticsearch_status = 'disconnected'
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'kafka': kafka_status,
        'elasticsearch': elasticsearch_status,
        'services': ['kafka', 'elasticsearch', 'kibana', 'dashboard']
    })

@app.route('/api/elasticsearch/indices')
def list_indices():
    """List all indices in Elasticsearch"""
    try:
        indices = es.cat.indices(format='json')
        return jsonify({'indices': indices})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/elasticsearch/search')
def search_messages():
    """Search messages in Elasticsearch"""
    try:
        response = es.search(
            index="kafka-dashboard-*",
            body={
                "query": {
                    "match_all": {}
                },
                "sort": [
                    {
                        "timestamp": {
                            "order": "desc"
                        }
                    }
                ],
                "size": 50
            }
        )
        return jsonify(response['hits'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'connected', 'message': 'Welcome to Kafka Dashboard'})

@socketio.on('send_message')
def handle_message(data):
    if 'message' not in data or not data['message'].strip():
        emit('send_status', {'success': False, 'error': 'Message is required'})
        return
    
    if 'sender' not in data:
        data['sender'] = 'Anonymous'
    
    if 'category' not in data:
        data['category'] = 'info'
    
    result = kafka_manager.send_message(data)
    emit('send_status', result)

if __name__ == '__main__':
    # Wait for services to be ready
    logger.info("Waiting for services to start...")
    time.sleep(10)
    
    # Create Elasticsearch index if it doesn't exist
    try:
        index_name = f"kafka-dashboard-{datetime.now().strftime('%Y.%m.%d')}"
        if not es.indices.exists(index=index_name):
            es.indices.create(index=index_name)
            logger.info(f"Created Elasticsearch index: {index_name}")
    except Exception as e:
        logger.error(f"Failed to create Elasticsearch index: {e}")
    
    # Start consumer in background
    kafka_manager.start_consumer()
    
    # Start Flask app
    logger.info("Starting Kafka Dashboard on http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)