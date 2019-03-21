# Reti

---

## La parte più a sinistra dell’URL `http://www.mypage.org/mypage.html` identifica:

- [x] il protocollo da utilizzare per il recupero del documento
- [ ] la cartella contenente il documento
- [ ] nessuna delle opzioni elencate

---

## Un host in Internet è identificato da:

- [x] indirizzo IP
- [ ] protocollo TCP
- [ ] indirizzo email	

---

## Qual è il ruolo del servizio DNS

- [x] traduce gli indirizzi mnemonici in indirizzi IP
- [ ] invia i pacchetti dei dati da un punto della rete al successivo
- [ ] definisce i percorsi che devono essere seguiti dalle comunicazioni

---

## Un router di Internet:

- [x] mantiene le informazioni necessarie per decidere dove instradare i pacchetti di dati   
- [ ] fornisce l'associazione tra nome di dominio e indirizzo IP
- [ ] si occupa di creare un canale di trasmissione dedicato, temporaneo, tra sorgente e destinatario del trasferimento dati

---

## Quali di questi sono *indirizzi IP* validi:

- [x] 127.102.7.21 
- [ ] 328.95.127
- [ ] diegm.uniud.it

---

## Memorizzare le informazioni per un possibile riutilizzo si dice

- [x] caching	
- [ ] hopping	
- [ ] serving	

---

## Che tipologia di comunicazione prevede l’invio e la ricezione di informazioni in momenti diversi?

- [ ] sincrona	
- [x] asincrona	
- [ ] DNS	

---

## In quale delle seguenti tipologie di comunicazione il mittente e il destinatario sono contemporaneamente attivi?

- [x] sincrona	
- [ ] asincrona	
- [ ] veloce	

---

## Internet è sufficientemente veloce da simulare una comunicazione

- [x] sincrona	
- [ ] asincrona		
- [ ] LAN

---

## Internet e World Wide Web sono nomi diversi della stessa cosa

- [ ] vero	
- [x] falso
- [ ] Internet un tempo si chiamava World Wide Web	

---

## Una comunicazione multicast

- [ ] è inviata a molte persone senza essere indirizzata a nessuno in particolare
- [x] è inviata a un sottoinsieme determinato di persone, non a tutte
- [ ] è inviata ad un solo destinatario

---

## Una comunicazione broadcast

- [x] è inviata a molte persone senza essere indirizzata a nessuno in particolare
- [ ] è inviata a un sottoinsieme particolare di persone, non a tutte
- [ ] è inviata ad un solo destinatario

---

## Una comunicazione point-to-point

- [ ] è inviata a molte persone senza essere indirizzata a nessuno in particolare
- [ ] è inviata a un sottoinsieme particolare di persone, non a tutte
- [x] è inviata ad un solo destinatario

---

## Un esempio di comunicazione point-to-point

- [x] il telefono o Skype
- [ ] la radio o la televisione
- [ ] delle riviste specializzate

---

## Un esempio di comunicazione broadcast

- [ ] il telefono o Skype
- [x] la radio o la televisione
- [ ] delle riviste specializzate

---

## Un esempio di comunicazione multicast

- [ ] il telefono o Skype
- [ ] la radio o la televisione
- [x] delle riviste specializzate

---

## La comunicazione via internet

- [x] è asincrona e point-to-point
- [ ] è sincrona e in broadcast
- [ ] collega fisicamente i computer

---

## Nel paradigma client-server

- [x] il client richiede un servizio
- [x] il server fornisce un servizio 
- [ ] il collegamento viene mantenuto per soddisfare richieste successive

---

## Per ottenere l'illusione di una connessione continua, il protocollo `http`

- [x] utilizza i *cookie*, piccoli file che codificano la storia delle interazioni precedenti
- [ ] invia i dati al DNS per la loro elaborazione
- [ ] forza i pacchetti IP ad arrivare nell'ordine giusto

---

## Un pacchetto IP

- [x] è come una cartolina che contiene gli indirizzi del mittente, del destinatario, un messaggio (payload) e un numero di sequenza
- [x] può essere instradato su un percorso diverso da quello dei suoi predecessori
- [ ] realizza una connessione continua tra due host

---

## L'istradamento dei pacchetti nella rete Internet

- [x] può seguire percorsi diversi a seconda della disponibilità e della congestione di router e switch
- [ ] deve avvenire sempre attraverso lo stesso percorso, determinato a priori
- [x] non garantisce che l'ordine di arrivo dei pacchetti sia lo stesso con i quali sono stati spediti

---

## L'istradamento dei pacchetti nella rete Internet

- [ ] deve avvenire sempre attraverso lo stesso percorso, determinato a priori
- [x] non garantisce che l'ordine di arrivo dei pacchetti sia lo stesso con i quali sono stati spediti
- [x] può fallire, in tal caso il protocollo TCP/IP ne richiederà nuovamente l'invio

---

## Una rete locale (LAN)

- [ ] è una rete progettata per inviare informazioni tra località molto distanti
- [x] è costituita da un insieme di computer vicini
- [x] è collegata da un unico canale di comunicazione

---

## Nella rete Ethernet

- [ ] è presente un sistema di controllo centralizzato che decide quando ciascuna macchina può comunicare
- [x] tutti i computer collegati alla rete accedono al contenuto della comunicazione
- [x] nel caso di più comunicazioni contemporanee, ciascuna macchina attende per un periodo di tempo casuale prima di riprovare a trasmettere

---

## Nella rete Ethernet

- [ ] ciascun emittente invia i dati ad intervalli di tempo regolari
- [x] tutti i computer collegati alla rete accedono al contenuto della comunicazione
- [x] non c'è un controllo centralizzato o una pianificazione degli invii

---

## Il nome di dominio 

- [x] è una codifica mnemonica utilizzata per riferirsi ad uno specifica macchina collegata su Internet
- [x] fa riferimento ad una struttura gerarchica di denominazione 
- [ ] è costituito da una sequenza di quattro valori numerici di un byte separati da punti

---

## I domini di primo livello

- [x] originariamente erano 7: `.com`, `.edu`, `.gov`, `.int`, `.mil`, `.net`
- [x] includono una serie di domini nazionali mnemonici di due lettere
- [ ] debbono sempre iniziare con la stringa `www`, altrimenti non sono validi

---

## Un root name server

- [ ] per comunicare utilizza il protocollo `http`
- [x] è una delle 13 macchine che conoscono gli indirizzi IP dei domini di primo livello
- [ ] contiene dei dati precaricati per l'instradamento dei pacchetti

---

## Il world wide web

- [x] è un servizio di rete distinto dalla rete Internet
- [x] è costituito da un insieme di server web collegati a Internet che inviano file ai browser
- [ ] già esisteva quando fu realizzata la rete Internet

---

## Un URL è composto da

- [ ] stringa `www`, percorso del file, nome host
- [ ] schema o protocollo, percorso del file, nome dominio
- [x] schema o protocollo, hostname, percorso del file

---

## Una pagina web

- [ ] è realizzata attraverso degli strumenti WYSIWYG (What You See Is What You Get)
- [x] è un ipertesto
- [x] viene strutturata attraverso la marcatura
