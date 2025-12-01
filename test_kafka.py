from kafka import KafkaProducer, KafkaConsumer
import json
import time

def test_kafka():
    print("Testing Kafka connection...")
    
    # Test producer
    try:
        producer = KafkaProducer(
            bootstrap_servers='localhost:29092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("✓ Producer connected successfully")
        
        # Send test message
        test_msg = {'message': 'Test from Python', 'sender': 'test', 'timestamp': time.time()}
        future = producer.send('test-topic', test_msg)
        result = future.get(timeout=10)
        print(f"✓ Message sent successfully (offset: {result.offset})")
        producer.close()
    except Exception as e:
        print(f"✗ Producer failed: {e}")
        return False
    
    # Test consumer
    try:
        consumer = KafkaConsumer(
            'test-topic',
            bootstrap_servers='localhost:29092',
            auto_offset_reset='earliest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        print("✓ Consumer connected successfully")
        consumer.close()
    except Exception as e:
        print(f"✗ Consumer failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    if test_kafka():
        print("\n✅ Kafka is working correctly!")
    else:
        print("\n❌ Kafka test failed")