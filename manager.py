from confluent_kafka import AdminClient, NewTopic
import mysql.connector

admin = AdminClient({'bootstrap.servers': 'localhost:9092'})

admin.create_topics([NewTopic("FirstCall", num_partitions=1, replication_factor=1), NewTopic("FirstCallAck", num_partitions=1, replication_factor=1)])

db = mysql.connector.connect(
    host = "localhost",
    database = "ds_filesystem",
    user = "admin",
    password = "admin",
    port = 3307
)

cursor = db.cursor()

cursor.execute("SELECT MAX(topic) FROM partitions")

res = cursor.fetchall()

for x in res:
  print(x)