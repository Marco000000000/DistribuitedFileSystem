

# Istruzioni per il deploy:

1. Scaricare [Docker Desktop](https://www.docker.com/products/docker-desktop) dal sito ufficiale ed installare l'ambiente Kubernetes associato.

2. Una volta scaricato il progetto, utilizzare il comando:
   ```bash
   docker-compose build
   ```
oppure, se si utilizza Linux e non è stato attivato l'alias docker-compose, utilizzare il comando:

   ```bash
   docker compose build 
   ```
3.Successivamente, lanciare il comando:

   ```bash
   kubectl apply -f startall.yaml ```
```
 ## Descrizione del sistema
   Il progetto realizzato implementa un file system distribuito che supporta varie operazioni su diverse tipologie di file.
   L’obiettivo che il sistema si pone è la massimizzazione del throughput in download.
   A questo scopo, durante l’operazione iniziale di upload di un file esterno, il flusso in ingresso viene parallelamente diviso tra gruppi di n macchine interne, chiamate “fileSystems”.
   Questo ha permesso di avere uno scaling sui dati oltre che orizzontalmente.
   Durante la successiva operazione di download sui tre flussi viene applicato l’interleaving allo scopo di ricostruire il file iniziale.
   A causa di ciò il throughput tende a salire, ma, allo stesso tempo, aumenta anche la latenza, poiché per l’invio del file è necessario aspettare il flusso trasmesso dal fileSystem più lento.
   Attenzioneremo in seguito la gestione della latenza massima con modelli predittivi ARIMA. 
   Per la comunicazione tra i vari attori del nostro sistema è stata impiegata, quasi nella totalità dei casi, la comunicazione indiretta tramite broker Kafka poiché essa fornisce importanti funzionalità come la possibilità di inviare a vari attori lo stesso messaggio oppure fornire in Round Robin una serie di richieste ad un gruppo di macchine, allo stesso tempo fornisce un meccanismo di garanzia della ricezione dei messaggi tramite un semplice meccanismo di commit e retain.
   Per sopperire ai cambiamenti di traffico in download e cercare di mantenere un throughput che permetta una buona usabilità del sistema sono state utilizzate le api dell’orchestratore Kubernetes cercando di scalare orizzontalmente utilizzando previsioni basate su modelli predittivi ARIMA.
   In aggiunta è stato implementato un sistema di online learning per aggiornare i modelli predittivi ogni 10 minuti.

