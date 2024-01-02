import mysql.connector
import time

def mysql_custom_connect(conf):
    while True:
        try:

            db = mysql.connector.connect(**conf)

            if db.is_connected():
                print("Connected to MySQL database")
                return db
        except mysql.connector.Error as err:
            print("Something went wrong: {}".format(err))
        
        print("Trying again...")
        time.sleep(5)

if __name__ == '__main__':
    
    conf = {
            'host':'db',
            'port':3306,
            'database':'ds_filesystem',
            'user':'root',
            'password':'giovanni'
            }

    db = mysql_custom_connect(conf)

    cursor=db.cursor()

    cursor.execute("SELECT * FROM partitions")

    for row in cursor:
        print(row)

    cursor.close()
    db.close()