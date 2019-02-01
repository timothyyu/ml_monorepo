source("gmmhmm.R")


## 测试中证500
########################################################################
## 0. 读取指数数据
data <- read.csv("data/NAV_5ETFs.csv")
zz500 <- as.xts(data[, 2], order.by=strptime(data[, 1], format="%Y-%m-%d", tz=""))
zz500 <- na.omit(cbind(zz500, Return.calculate(zz500)))
benchmark <- as.xts(data[, 2:6], order.by=strptime(data[,1], format="%Y-%m-%d", tz=""))
benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))
colnames(zz500) <- c('zz500', 'zz500.ret')


## 1. 对中证500日回报进行分析
layout(rbind(c(1,2), c(3,4)))
chart.Histogram(zz500$zz500.ret, main = "Density", breaks=40, methods = c("add.density", "add.normal"))
chart.Histogram(zz500$zz500.ret, main = "Risk Measures", methods = c("add.risk"))
chart.QQPlot(zz500$zz500.ret)
table.Stats(zz500$zz500.ret)


## 2. 利用HMM模型来分析
### 2.1 对单一指数的分析

## case1 : 2个市场状态
data_case1 <- zz500$zz500.ret
gmm <- gmm_training(data_training = data_case1, nstate = 2)
hmm <- hmm_training(gmm, data_case1, data_case1)

ret_regime1 <- hmm$hmm_ret_regime[,1]
ret_regime1 <- ret_regime1[ret_regime1 != 0]
ret_regime2 <- hmm$hmm_ret_regime[,2]
ret_regime2 <- ret_regime2[ret_regime2 != 0]

### 第一个图
layout(rbind(c(1,2),c(3,4)))
plot.xts(zz500$zz500)
points(zz500$zz500[hmm$hmm_yhat==1], pch=20, col="black")
chart.Histogram(ret_regime1, main = "Density", breaks=40, methods = c("add.density", "add.normal"))
chart.Histogram(ret_regime1, main = "Risk Measures", methods = c("add.risk"))
chart.QQPlot(ret_regime1)

layout(rbind(c(1,2),c(3,4)))
plot.xts(zz500$zz500)
points(zz500$zz500[hmm$hmm_yhat==2], pch=20, col="red")
chart.Histogram(ret_regime2, main = "Density", breaks=40, methods = c("add.density", "add.normal"))
chart.Histogram(ret_regime2, main = "Risk Measures", methods = c("add.risk"))
chart.QQPlot(ret_regime2)


ret_regimes <- cbind.xts(hmm$hmm_ret_regime, zz500$zz500.ret)
ret_regimes[is.na(ret_regimes)] <- 0
colnames(ret_regimes) <- c("regime 1", "regime 2", "zz500")
charts.PerformanceSummary(ret_regimes)

table.Stats(ret_regimes)
table.AnnualizedReturns(ret_regimes)


### casd2: 5个市场状态
data_case2 <- zz500$zz500.ret
gmm <- gmm_training(data_training = data_case2, nstate = 5)
hmm <- hmm_training(gmm, data_case2, data_case2)

ret_regimes <- cbind.xts(hmm$hmm_ret_regime, zz500$zz500.ret)
charts.PerformanceSummary(ret_regimes)
table.Stats(ret_regimes)
rbind(table.AnnualizedReturns(ret_regimes), table.Distributions(ret_regimes), maxDrawdown(ret_regimes))


### case3 : 通过单一指数， 构建复杂的训练数据集
data_case3 <- cbind.xts(zz500$zz500.ret, lag(zz500$zz500.ret, 1), lag(zz500$zz500.ret, 5));
rsi <- TTR::RSI(zz500$zz500.ret) / 100 # normalize the data
macd <- TTR::MACD(zz500$zz500.ret)
#data_case3 <- na.omit(cbind.xts(data_case3, rsi, macd))
colnames(data_case3) <- c("ret", "ret1d", "ret5d")
data_case3 <- na.omit(data_case3)


gmm <- gmm_training(data_training = data_case3, nstate=3)
hmm <- hmm_training1(gmm, data_case3, data_case3[,1])


charts.PerformanceSummary(hmm$hmm_ret_regime)
table.Stats(hmm$hmm_ret_regime)
table.AnnualizedReturns(hmm$hmm_ret_regime)


## out-of-sample test for 中证500
#######################################
source("gmmhmm.R")
test_oot1 <- function() {
  data_oot <- cbind.xts(benchmark_ret[, c(1, 2, 5)], lag(benchmark_ret[,1], 1), lag(benchmark_ret[, 1], 5));
  data_oot <- na.omit(data_oot)
  gmmhmm(dataset = data_oot, ret_target = benchmark_ret[, 1], n_start = 1000, n_state = 5)
}

test_oot2 <- function() {
  ema2 <- TTR::EMA(benchmark[,1], 2);
  data_oot <- cbind.xts(benchmark_ret[, c(1, 2, 5)],  Return.calculate(ema2), lag(benchmark_ret[,1], 1), lag(benchmark_ret[, 1], 5));
  data_oot <- na.omit(data_oot)
  ret <- gmmhmm(dataset = data_oot, ret_target = benchmark_ret[, 1], n_start = 1000, n_state = 5)
  write.csv(ret, 'data/oo2_output.csv')
}

