source("gmmhmm.R")
library(quantmod)

## 测试中证500
########################################################################
## 0. 读取指数数据
#data <- read.csv("data/NAV_5ETFs_updated.csv")
#benchmark <- na.omit(as.xts(data[, 2], order.by=strptime(data[,1], format="%Y/%m/%d", tz="")))
#benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))


############################
## 5 mins
data <- read.csv("data/2.csv", sep = ";")
benchmark <- na.omit(as.xts(data[, 2], order.by=strptime(data[,1], format="%Y/%m/%d %H:%M", tz="")))


######################
## 30 mins
#data <- read.csv("data/4.csv", sep = ";")
#benchmark <- na.omit(as.xts(data[, 2], order.by=strptime(data[,1], format="%y/%m/%d %H:%M", tz="")))

#########################
## 股指期货5min
#data <- read.csv("data/Future_5min.csv")
#benchmark <- na.omit(as.xts(data[, 2], order.by=strptime(data[,1], format="%Y/%m/%d %H:%M", tz="")))

#############################
## SPY
#library(Quandl)
#data <- Quandl('CURRFX/EURUSD', type='xts',collapse = 'daily')
#benchmark <- data[,1]

benchmark_ret <- (benchmark / lag(benchmark, 1)) - 1
benchmark_ret <- na.omit(benchmark_ret)

#benchmark_ret <- benchmark_ret[3000:4000]



signal <- (benchmark_ret > 0)* 1


generatePatterns <- function(testing_ret) {
  signal <- (benchmark_ret > 0)*1
  patterns <- signal * 0
  n = 3
  
  for (i in 1:n) {
    patterns <- patterns + lag(signal, n-i) * 2^(n-i)
  }
  output <- list()
  output$signal <- signal
  output$patterns <- patterns
  return(output)
}

categorizeReturns <- function(rets, signal, patterns, n) {
  total_nr_patterns <- 2^n
  
  for (i in 1:total_nr_patterns) {
    index_group <- signal[patterns == ]
  }
  
}

groups <- list()
signals <- list()
rets_group <- list()
sharpes_group <- list()
count_group <- list()
accuracy_group <- list()
for (k in 1:(2^n )) {
  groups[[k]] <- signal[patterns == (k-1)]
  #groups[[k]] <- signal[patterns == k]
  signals[[k]] <- na.omit(groups[[k]])
  rets_group[[k]] <- benchmark_ret[index(signals[[k]])]
  sharpes_group[[k]] <- mean(rets_group[[k]]) / as.numeric(cov(rets_group[[k]]))
  count_group[[k]] <- length(signals[[k]])
  accuracy_group[[k]] <- sum(signals[[k]]) / count_group[[k]]
}
groups <- do.call(cbind, groups)
groups[is.na(groups)] <- 0
sharpes_group <- do.call(rbind, sharpes_group)
count_group <- do.call(rbind, count_group)
accuracy_group <- do.call(rbind, accuracy_group)

colnames(groups) <- c(1:(2^n))
colMeans(groups)
sharpes_group
#####
head(cbind(signal, patterns, benchmark_ret), 64)
plot(cumprod(1+rets_group[[16]]))


rets <- rets_group[[1]]
for (i in 2:(2^n)) {
  rets <- cbind(rets, rets_group[[i]])
}
rets <- cbind(rets, benchmark_ret )
rets[is.na(rets)] <- 0


ret_target <- rets[,1]
tzone(ret_target) <- Sys.getenv("TZ")
charts.PerformanceSummary(rets[,c(2)])

rets_positive <- rets[, 1] * 0;
tzone(rets_positive) <- Sys.getenv("TZ")
rets_negative <- rets_positive
for (i in 1:(2^n)) {
  if (sharpes_group[i] > 0)
    rets_positive <- rets_positive + rets[, i]
  if (sharpes_group[i] < 0)
    rets_negative <- rets_negative + rets[,i]
}
charts.PerformanceSummary(cbind(rets_positive - rets_negative, rets_positive, -rets_negative, benchmark_ret))

cbind(accuracy_group, sharpes_group)

