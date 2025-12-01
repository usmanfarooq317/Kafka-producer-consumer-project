from kafka import KafkaProducer
import json
import os
from dotenv import load_dotenv
import logging
import time

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaMessageProducer:
    def __init__(self, max_retries=5, retry_delay=5):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
        self.topic = os.getenv('KAFKA_TOPIC', 'dashboard-messages')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.producer = None
        
        self._initialize_producer()
        
    def _initialize_producer(self):
        """Initialize Kafka producer with retry logic"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries} to connect to Kafka at {self.bootstrap_servers}")
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all',
                    retries=3,
                    request_timeout_ms=10000,
                    max_block_ms=10000,
                    api_version_auto_timeout_ms=30000
                )
                
                # Test connection
                self.producer.list_topics(timeout=10)
                logger.info(f"Producer connected to {self.bootstrap_servers}")
                return
                
            except Exception as e:
                logger.error(f"Failed to connect to Kafka (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error("Max retries reached. Could not connect to Kafka.")
                    raise
    
    def send_message(self, message_data):
        """Send message to Kafka topic"""
        try:
            if not self.producer:
                self._initialize_producer()
            
            # Add timestamp and metadata
            message_with_metadata = {
                'timestamp': message_data.get('timestamp'),
                'message': message_data.get('message'),
                'sender': message_data.get('sender', 'web-frontend'),
                'category': message_data.get('category', 'general'),
                'value': message_data.get('value', 0)
            }
            
            future = self.producer.send(
                self.topic,
                value=message_with_metadata
            )
            
            # Block until the message is sent
            result = future.get(timeout=10)
            logger.info(f"Message sent to {self.topic}: {message_with_metadata}")
            return {
                'success': True,
                'topic': result.topic,
                'partition': result.partition,
                'offset': result.offset
            }
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            # Try to reinitialize producer on error
            try:
                self._initialize_producer()
            except:
                pass
            return {'success': False, 'error': str(e)}
    
    def close(self):
        """Close producer connection"""
        if self.producer:
            self.producer.close()

# Singleton instance
producer_instance = KafkaMessageProducer()