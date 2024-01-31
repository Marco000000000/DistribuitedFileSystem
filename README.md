#Istruzioni per il deploy:
Scaricare docker Desktop dal sito ufficiale ed installare l'ambiente kubernetes associato.
Una volta scaricato il progetto usare il comando :
`docker-compose build`
o se su linux e non si è attivato il l'alias docker-compose usare il comando:
`docker compose build`
A questo punto lanciare il comando
`kubectl apply -f startall.yaml` 
