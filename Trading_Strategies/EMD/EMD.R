library(xts)
library(hht)
library(gdata)

library(Quandl)
library(TTR)

data <- Quandl('CHRIS/SHFE_AU2', type='xts')
settle <- data$Settle

ret <- na.omit(ROC(settle, n=1))

dts <- index(data)
tt <- 1:length(dts)

emd <- Sig2IMF(as.vector(settle), tt)
residue = emd$residue
imfs = emd$imf
signal = emd$original.signal

emd1 <- Sig2IMF(as.vector(settle), 1:length(settle))
imfs <- as.data.frame(emd1$imf)
resi <- as.data.frame(emd1$residue )
colnames(resi) <- 'R'
v7 <- as.xts(imfs$V7, order.by = index(settle))

v7_total <- v7
colnames(v7_total) <- 'target'
for (i in 1:100) {
  v7_total <- cbind(v7_total, lag(v7, i))
}

v7_total <- na.omit(v7_total)

library(rattle)
