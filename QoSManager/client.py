import requests
import random
import threading

def makeRandomRequest():
        response=requests.get("http://192.168.1.128:30000/discover")

        names=response.json()
        lenght=len(names)
        random_key = random.choice(list(names.keys()))

        print("http://192.168.1.128:30000/download/"+random_key)
        response=requests.get("http://192.168.1.128:30000/download/"+random_key)
        if response.status_code == 200:
            for chunk in response.iter_content(chunk_size=131072):  # Adjust the chunk size as needed
                pass
if __name__=="__main__":
    while True:
        threads=[]
        for i in range(10):
            thread = threading.Thread(target=makeRandomRequest)
            threads.append(thread)
            thread.start()

        for i in range(10):
            threads[i].join()