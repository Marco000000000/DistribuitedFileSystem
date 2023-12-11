from confluent_kafka import Consumer
################
c=Consumer({'bootstrap.servers':'localhost:9092','group.id':'python-consumer','auto.offset.reset':'earliest'})
print('Il Consumer è stato avviato...')

print('Topics disponibili da consumare: ', c.list_topics().topics)
c.subscribe(['user-tracker'])


# Testing consumazione dati
if __name__ == '__main__':
    while True:
        msg=c.poll(1.0) #timeout
        if msg is None:
            continue
        if msg.error():
            print('Error: {}'.format(msg.error()))
            continue
        data=msg.value().decode('utf-8')
        print(data)
    c.close()