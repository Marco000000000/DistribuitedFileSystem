import time
import requests
import random
import threading

def makeRandomRequest():
        response=requests.get("http://192.168.1.128:30000/discover")
        print(response)
        names=response.json()
        random_key = random.choice(list(names.keys()))
        url="http://192.168.1.128:30000/download/"+names[random_key]
        print(url)
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192): 
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk: 
                print(chunk)
        

        print("fatto")
if __name__=="__main__":
    #makeRandomRequest()
    while True:
        threads=[]
        for i in range(3):
            thread = threading.Thread(target=makeRandomRequest)
            threads.append(thread)
            thread.start()
            time.sleep(2)

        
        
        time.sleep(4)