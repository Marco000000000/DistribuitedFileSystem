from confluent_kafka import Producer

def delivery_report(err, msg):
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

conf = {'bootstrap.servers': 'localhost:9092'}

producer = Producer(conf)

# Produce a message to the 'example-topic' topic
producer.produce('FirstCall', key='key', value='Hello, Kafka!', callback=delivery_report)

# Wait for any outstanding messages to be delivered and delivery reports to be received.
producer.flush()
