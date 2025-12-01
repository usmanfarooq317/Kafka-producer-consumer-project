from kafka import KafkaConsumer
import json
import os
from dotenv import load_dotenv
import logging
from threading import Thread
import time

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaMessageConsumer:
    def __init__(self, callback_function=None, max_retries=5, retry_delay=10):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
        self.topic = os.getenv('KAFKA_TOPIC', 'dashboard-messages')
        self.callback = callback_function
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.consumer = None
        self.is_running = False
        self.thread = None
        
    def _initialize_consumer(self):
        """Initialize Kafka consumer with retry logic"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries} to initialize Kafka consumer...")
                self.consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    group_id='dashboard-consumer-group',
                    session_timeout_ms=10000,
                    request_timeout_ms=10000,
                    max_poll_interval_ms=300000
                )
                logger.info(f"Consumer initialized for topic: {self.topic}")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize consumer (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error("Max retries reached. Could not initialize consumer.")
                    return False
    
    def start_consuming(self):
        """Start consuming messages in a separate thread"""
        self.is_running = True
        self.thread = Thread(target=self._consume_messages)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Consumer started for topic: {self.topic}")
    
    def _consume_messages(self):
        """Internal method to consume messages"""
        if not self._initialize_consumer():
            logger.error("Failed to initialize consumer. Exiting consume thread.")
            return
        
        while self.is_running:
            try:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        message_data = message.value
                        message_data['kafka_offset'] = message.offset
                        message_data['kafka_partition'] = message.partition
                        message_data['kafka_topic'] = message.topic
                        
                        logger.info(f"Received message: {message_data}")
                        
                        # Call callback function if provided
                        if self.callback:
                            self.callback(message_data)
                            
            except Exception as e:
                logger.error(f"Error consuming messages: {e}")
                # Try to reinitialize consumer on error
                time.sleep(self.retry_delay)
                if not self._initialize_consumer():
                    logger.error("Failed to reinitialize consumer after error.")
                    break
    
    def stop_consuming(self):
        """Stop consuming messages"""
        self.is_running = False
        if self.consumer:
            self.consumer.close()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Consumer stopped")

# Global consumer instance
consumer_instance = None

def start_consumer(callback):
    """Start the consumer with a callback function"""
    global consumer_instance
    consumer_instance = KafkaMessageConsumer(callback)
    consumer_instance.start_consuming()
    return consumer_instance

def stop_consumer():
    """Stop the consumer"""
    global consumer_instance
    if consumer_instance:
        consumer_instance.stop_consuming()