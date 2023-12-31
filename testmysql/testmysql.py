import mysql.connector

conf = {
    'host':'mysql',
    'port':3307,
    'database':'ds_filesystem',
    'user':'root',
    'password':'giovanni'
    }

db = mysql.connector.connect(**conf)

cursor=db.cursor()

cursor.execute("SELECT * FROM partitions")

for row in cursor:
    print(row)

cursor.close()
db.close()

if __name__ == '__main__':
    while True:
        pass