import time
import requests
import random
import threading

def makeRandomRequest():
        response=requests.get("http://localhost:30000/discover")
        print(response)
        names=response.json()
        random_key = random.choice(list(names.keys()))
        url="http://localhost:30000/download/"+names[random_key]
        print(url)
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=131072): 
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk: 
                continue
        

        print("fatto")
if __name__=="__main__":
    #makeRandomRequest()
    while True:
        threads=[]
        for i in range(2):
            thread = threading.Thread(target=makeRandomRequest)
            threads.append(thread)
            thread.start()
            time.sleep(3)

        for i in range(2):
            threads[i].join()
        
        time.sleep(3)