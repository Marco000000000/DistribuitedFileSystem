from confluent_kafka import Consumer, KafkaException

conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': '1234',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(conf)

# Subscribe to the 'example-topic' topic
consumer.subscribe(['FirstCall'])

try:
    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue
        if msg.error():

            print(msg.error())
            break

        print('Received message: {}'.format(msg.value().decode('utf-8')))

except KeyboardInterrupt:
    pass

finally:
    # Close down consumer to commit final offsets.
    consumer.close()
