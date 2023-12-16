from confluent_kafka import Producer
from faker import Faker
import json
import time
import logging
import random

# Creazione di un oggetto Faker che genera dati casuali
fake=Faker()


# Creazione di un logger

# Creazione Producer
print('Il produttore è stato avviato...')




# Testing        
if __name__ ==  '__main__':
    for i in range(10):
        data={
           'user_id': fake.random_int(min=20000, max=100000),
           'user_name':fake.name(),
           'user_address':fake.street_address() + ' | ' + fake.city() + ' | ' + fake.country_code(),
           'platform': random.choice(['Mobile', 'Laptop', 'Tablet']),
           'signup_at': str(fake.date_time_this_month())    
           }
        m=json.dumps(data)
        p.poll(1)
        p.produce('user-tracker', m.encode('utf-8'),callback=receipt)
        p.flush()
        time.sleep(3)