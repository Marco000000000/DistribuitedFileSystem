from confluent_kafka import AdminClient, NewTopic

admin = AdminClient({'bootstrap.servers': 'localhost:9092'})

admin.create_topics([NewTopic("FirstCall", num_partitions=1, replication_factor=1), NewTopic("FirstCallAck", num_partitions=1, replication_factor=1)])