# Rappresentazione dei dati multimediali

---

## Il *campionamento* di un segnale consiste nel

- [x] prenderne misure ad intervalli regolari 
- [ ] rappresentarne l'intensità con un insieme finito di valori
- [ ] scomporlo in una serie di segnali sinusoidali

---

## La *quantizzazione* di un segnale consiste nel

- [x] rappresentarne l'intensità con un insieme finito di valori
- [ ] prenderne misure ad intervalli regolari 
- [ ] scomporlo in una serie di segnali sinusoidali

---

## Quanti *colori* si possono rappresentare con *8 bit*?

- [x] 256
- [ ] 8
- [ ] circa 16 milioni

---

## Quanti *colori* si possono rappresentare con *tre canali colore ciascuno ad 8 bit*?

- [ ] 3
- [ ] 256
- [x] circa 16 milioni

---

## Il *modello di colore CMY* è un modello

- [x] sottrattivo, usato nella stampa
- [ ] additivo, usato nei display
- [ ] illuminativo, usato nella televisione

---

## Il *modello di colore RGB* è un modello

- [x] additivo, usato nei display
- [ ] sottrattivo, usato nella stampa
- [x] additivo, usato nel web

---

## Un'*immagine bitmap* è descritta da

- [x] una matrice di pixel
- [ ] primitive grafiche
- [ ] vettori di moto

---

## Il *bianco*, nel modello di colori RGB

- [x] si ottiene come somma dei tre canali rosso, verde e blu alla massima intensità
- [ ] è dato dall'assenza degli altri tre colori
- [ ] viene assorbito dal display

---

## Il *nero*, nel modello di colori RGB

- [ ] si ottiene come somma dei tre canali rosso, verde e blu alla massima intensità
- [x] è dato dall'assenza di intensità di tutti e tre i canali
- [ ] viene assorbito dal display

---

## Per *schiarire* un'immagine

- [x] viene aggiunta intensità ai tre canali RGB attraverso una somma di un valore costante
- [x] è possibile che una o tutte le componenti RGB giungano al valore massimo possibile (saturazione)
- [ ] trasformiamo in bianco alcuni pixel a caso dell'immagine

---

## Per *scurire* un'immagine

- [x] viene tolta intensità ai tre canali RGB attraverso una differenza con un valore costante
- [x] è possibile che una o tutte le componenti RGB giungano al valore minimo possibile 
- [ ] trasformiamo in nero alcuni pixel a caso dell'immagine

---

## Un'immagine, a livelli di grigio, è *ben contrastata*

- [x] quando il diagramma dei livelli di grigio (istogramma) si distribuisce lungo tutta la gamma di possibili valori compresi fra 0 e 255
- [ ] quando contiene tanti pixel neri rispetto a quelli bianchi
- [ ] quando i colori sono piatti e uniformi

---

## Il *campionamento* di un suono in *qualità CD* avviene a *44.100Hz*

- [x] perché per il teorema di Nyquist, ciò consente di rappresentare esattamente tutti i suoni percepibili dall'orecchio umano
- [ ] il numero è stato scelto arbitrariamente, in modo da poter contenere esattamente un'ora di registrazione su un CD
- [ ] deriva dal numero di solchi sul disco di cera usato in origine da Thomas Edison

---

## Nel processo di *conversione Analogico/Digitale* per il suono

- [x] si trasforma l'onda sonora in onda elettrica e successivamente si converte il suono in digitale campionando l'onda continua ad intervalli regolari
- [ ] i dati vengono convertiti in valori decimali direttamente dal trasduttore
- [x] si perde l'informazione sonora relativa alle frequenze che sono la metà della frequenza di campionamento

---

## La *conversione Digitale/Analogica* per il suono

- [x] trasforma i valori digitali in un'onda elettrica che poi viene convertita in un'onda sonora dall'altoparlante
- [ ] converte i dati in valori binari in modo da poterli emettere attraverso l'altoparlante
- [ ] è in grado di ricostruire interamente il segnale originale

---

## La *compressione* **senza perdita** di informazione (*lossless*)

- [x] consente di ricostruire interamente il contenuto originario del dato di partenza
- [x] la codifica run-length del formato immagine GIF ne è un esempio
- [ ] aumenta la dimensione del file

---

## La *compressione* **con perdita** di informazione (*lossy*)

- [ ] consente di ricostruire interamente il contenuto originario del dato di partenza
- [x] può basarsi sull'osservazione che alcune caratteristiche dell'informazione sono poco sensibili ai sensi (ad es. la crominanza per la vista, alcune frequenze per l'udito)
- [x] garantisce un notevole risparmio di spazio

---

## Il *formato GIF*

- [x] è un formato immagine che usa la codifica run-length per la compressione
- [x] consente un numero limitato di colori, rappresentati in una tabella
- [ ] aumenta la dimensione del file

---

## Lo schema di compressione del *formato MPEG*

- [x] si basa sull'osservazione che due  immagini consecutive in un video differiscano di poco
- [x] registra solamente le differenze fra fotogrammi
- [ ] usa una codifica run-length

---

## Una sequenza di bit

- [x] può rappresentare informazione diversa a seconda dell'interpretazione che associamo loro attraverso i programmi
- [ ] rappresenta solamente un numero binario
- [x] è manipolabile ed elaborabile attraverso operazioni aritmetiche (e logiche) sui singoli bit