library(TTR)
library(PerformanceAnalytics)
library(xts)
library(gdata)
library(quantmod)

###### loading data
data <- read.csv('data/index_shanghai.csv')
bm_shanghai <- na.omit(as.xts(data[, 2:6], order.by=strptime(data[,1], format="%Y-%m-%d", tz="")))
data <- read.csv('data/index_shenzhen.csv')
bm_shenzhen <- na.omit(as.xts(data[, 2:6], order.by=strptime(data[,1], format="%Y/%m/%d", tz="")))

price <- na.omit(cbind.xts(bm_shanghai[, 4], bm_shenzhen[, 4]))
colnames(price) <- c("shanghai", "shenzhen")

ret_d <- na.omit(ROC(price, n=1, type = "continuous"))


######  Hurst Index
###### 计算指数（上海）在不同的周期n下， 全局的Hurst指数。
## 最大Hurst指数所在的周期n，就是该市场指数的逆转周期。 
source("Hurst.R")
test_data <- ret_d['2013-01-03/2015-10-01']$shenzhen
price_data <- price$shanghai


n <- c(10:1200)
rs_array <- data.frame(cbind(n, rep(0, length(n))))

for (i in 1:length(n) ) {
  print(i)
  hurst <- GlobalHurst(test_data, n[i])
  rs_array[i, 2] <- hurst$RS/hurst$N;
  #plot(rs_array)
}
plot(rs_array,type='l')

###### Rolling Window Hurst
source("Hurst.R")
k <- 20
hurst_slow <- rollapply(test_data, width = k, FUN = RS1)
exp_hurst_slow <- log(ExpectedRS(k)) / log(k)
l <- 150
hurst_fast <- rollapply(test_data, width = l, FUN = RS1)
exp_hurst_fast <- log(ExpectedRS(l)) / log(l)

tzone(hurst_fast) <- Sys.getenv("TZ")
tzone(hurst_slow) <- Sys.getenv("TZ")

#####
layout(c(1,2,3))
plot(hurst_fast, type='l')
plot(hurst_slow, type='l')
plot(price_data[index(test_data)])



#### Trading signal
#### 1. 连续5天hurst < E(H)
k <- 100
######################################################

hurst_slow <- rollapply(test_data, width = k, FUN = RS1)
exp_hurst_slow <- log(ExpectedRS(k)) / log(k)

signal <- ((hurst_slow < exp_hurst_slow) + 
          (lag(hurst_slow, 1) < exp_hurst_slow) +
          (lag(hurst_slow, 2) < exp_hurst_slow) +
          (lag(hurst_slow, 3) < exp_hurst_slow) + 
          (lag(hurst_slow, 4) < exp_hurst_slow))
signal <- na.omit(signal == 0) * 1



#signal <- na.omit((hurst_slow < exp_hurst_slow) * 1)
trend <- (price_data > SMA(price_data, k)) * 2 - 1
position <- trend * 0 + 1;





info <- na.omit(cbind.xts(signal, trend, position))
colnames(info) <- c('signal', 'trend', 'position')

#### trade backtesting
case = 2
info$position[1] <- 1;
for (i in c(1:(nrow(info)-1))) {
  if (info$signal[i] == 1) {
    if (case == 1) {
      if (info$trend[i] == 1 & (info$position[i] == 1) ) {
        info$position[i+1] = 0
      }
      if (info$trend[i] == -1 & (info$position[i] == 0)) {
        info$position[i+1] = 1 
      }
    }
    if (case == 2) {
      if (info$trend[i] == 1) {
        info$position[i+1] = 0
      }
      if (info$trend[i] == 0) {
        info$position[i+1] = 1 
      }
      
    }
    
    
  }
}


ret <- cbind(info$position * ret_d$shanghai, ret_d$shanghai)
charts.PerformanceSummary(ret)

hurst_20 <- na.omit(rollapply(ret, width = 20, FUN=RS1))
hurst_40 <- na.omit(rollapply(ret, width = 40, FUN=RS1))
hurst_100 <- na.omit(rollapply(ret, width = 100, FUN=RS1))
hurst_200 <- na.omit(rollapply(ret, width = 200, FUN=RS1))
hurst_400 <- na.omit(rollapply(ret, width = 400, FUN=RS1))
hurst_600 <- na.omit(rollapply(ret, width = 600, FUN=RS1))

## Using SVM to analysis the data
######################################
data_ml <- price$shanghai[endpoints(price$shanghai, on='days')]
#data_ml <- price$shenzhen
colnames(data_ml) <- c('shanghai')
ret_5d <- ROC(data_ml,  n = 5)
ret_d <- ROC(data_ml, n = 1)
ret <- ROC(data_ml, n = 1)
ret_sma <- ROC(EMA(data_ml, n=2), n = 1)
#ret_category <- ret * 0 + (
#   (ret > quantile(ret, 0.6)) * 1
#   + (ret < quantile(ret, 0.4)) * -1)
ret_category <- (na.omit(ret) > 0) * 1
#ret_category <- ret_category + (na.omit(ret) < 0)*-1
ret_category <- lag(ret_category, -1)
#ret_category <- ret*0 ;
#ret_category[ret > quantile(ret, 0.5)] <- 1
#ret_category[ret < quantile(ret, 0.5)] <- 0
#ret_cateogry <- na.omit(lag(ret_category, 1))
 
data <- ret_category
data <- cbind.xts(data, data_ml)
data <- cbind.xts(data, SMA(data_ml, 3))
data <- cbind.xts(data, SMA(data_ml, 5))
data <- cbind.xts(data, SMA(data_ml, 10))
data <- cbind.xts(data, ret)
data <- cbind.xts(data, ret_sma)
#data <- cbind.xts(data, ret)


#data <- cbind.xts(data, hurst_20)
#data <- cbind.xts(data, hurst_40)
#data <- cbind.xts(data, hurst_100)
#data <- cbind.xts(data, hurst_200)
#data <- cbind.xts(data, hurst_400)
#data <- cbind.xts(data, hurst_600)
data <- cbind.xts(data, SMA(hurst_20, 20))
data <- cbind.xts(data, SMA(hurst_40, 20))
data <- cbind.xts(data, SMA(hurst_100, 20))
data <- cbind.xts(data, SMA(hurst_200, 20))
data <- cbind.xts(data, SMA(hurst_400, 20))

data <- cbind.xts(data, RSI(data_ml))
macd <- MACD(data_ml)
data <- cbind.xts(data, macd$macd)
data <- cbind.xts(data, macd$signal)
data <- as.data.frame(na.omit(data))
data[,1] <- as.factor(data[,1])



nrows <- nrow(data)
n_sep <- as.integer(nrows*0.8)
data_test <- na.omit(data[n_sep:nrows, ])
data <- na.omit(data[1:n_sep, ])
library("rattle")
rattle()

source('rattle_log.R')
pred <- predict(crs$ksvm, newdata = na.omit(data_test))
pred <- as.data.frame(na.omit(pred))
pred[,1] <- as.numeric(pred[,1]) * 2 - 3
pred <- as.xts(pred, order.by=strptime(row.names(data_test), format = '%Y-%m-%d'))

actual <- as.xts(as.numeric(data_test[,1]) - 1, 
                 order.by=strptime(row.names(data_test), format = '%Y-%m-%d'))
output_pred <- cbind(pred, actual)

output_ret <- na.omit(cbind(
#         lag(pred, 1) * ret_d, 
          lag(pred == 1, 1) * ret_d, 
          lag(pred == 0, 1) * -ret_d, 
          ret_d))
tzone(output_ret) <- Sys.getenv("TZ")

charts.PerformanceSummary(output_ret)



