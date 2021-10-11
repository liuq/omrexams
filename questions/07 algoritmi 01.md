# Algoritmi /01

---

## Il seguente segmento di codice deve calcolare l'elevazione a potenza $y = x^n$ mediante moltiplicazioni successive. Si indichi la sostituzione corretta delle due istruzioni contrassegnate da ▲ e ★.

```
cnt <- 0;
y <- 1;
while ( %*▲*) ) 
{
   %*★*)
   cnt <- cnt + 1;
}
```


- [x] ▲: `cnt < n`  ★: `y <- y * x;`
- [ ] ▲: `cnt < n`  ★: `y <- y * (x + 1);`
- [ ] ▲: `cnt <= n` ★: `y <- y * (x - 1);`
- [ ] ▲: `cnt > n`  ★: `y <- y * x;`
- [ ] ▲: `cnt > n`  ★: `y <- y * (x + 1);`
- [ ] ▲: `cnt >= n` ★: `y <- y * (x - 1);`

---

## Il seguente segmento di codice deve calcolare la moltiplicazione $y = x \cdot n$ mediante somme successive. Si indichi la sostituzione corretta delle due istruzioni contrassegnate da ▲ e ★.

```
cnt <- 0;
y <- 0;
while (  %*▲*)  )
{
   %*★*)
   cnt <- cnt + 1;
}
```

- [x] ▲: `cnt < n`  ★: `y <- y + x;`
- [ ] ▲: `cnt < n`  ★: `y <- y + (x + 1);`
- [ ] ▲: `cnt <= n` ★: `y <- y + (x - 1);`
- [ ] ▲: `cnt > n`  ★: `y <- y + x;`
- [ ] ▲: `cnt > n`  ★: `y <- y + (x + 1);`
- [ ] ▲: `cnt >= n` ★: `y <- y + (x - 1);`

---

## Il seguente segmento di codice deve calcolare il quoziente della divisione intera $y = x / n$ mediante sottrazioni successive. Si indichi la sostituzione corretta delle due istruzioni contrassegnate da ▲ e ★.

```
y <- 0;
t <- x;
while (  %*▲*)  )
{
   %*★*)
   y <- y + 1;
}
```

- [x] ▲: `t >= x`  ★: `t <- t - x;`
- [ ] ▲: `t > x`   ★: `t <- t - x;`
- [ ] ▲: `t >= x`  ★: `t <- t - 1;`
- [ ] ▲: `t > x`   ★: `t <- t - 1;`
- [ ] ▲: `t <= x`  ★: `t <- t - x;`
- [ ] ▲: `t <= x`  ★: `t <- t - 1;`

---

## Il seguente segmento di codice deve calcolare il resto della divisione intera $y = x / n$ mediante sottrazioni successive. Si indichi la sostituzione corretta delle due istruzioni contrassegnate da ▲ e ★.

```
y <- 0;
r <- x;
while (  %*▲*)  )
{
   %*★*)
}
```

- [x] ▲: `r >= x`  ★: `r <- r - x;`
- [ ] ▲: `r > x`   ★: `r <- r - x;`
- [ ] ▲: `r >= x`  ★: `r <- r - 1;`
- [ ] ▲: `r > x`   ★: `r <- r - 1;`
- [ ] ▲: `r <= x`  ★: `r <- r - x;`
- [ ] ▲: `r <= x`  ★: `r <- r - 1;`

