source("gmmhmm.R")


## 测试中证500
########################################################################
## 0. 读取指数数据
load_data <- function()
{
  data <- read.csv("data/NAV_5ETFs_updated.csv")
  benchmark <- na.omit(as.xts(data[, 2:6], order.by=strptime(data[,1], format="%Y/%m/%d", tz="")))
  benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))
  
  d <- list();
  d[[1]] <- benchmark;
  d[[2]] <- benchmark_ret;
  return (d);
}


## out-of-sample test for 中证500
#######################################
source("gmmhmm.R")
test_oot1 <- function() {
  data_oot <- cbind.xts(benchmark_ret[, c(1, 2, 5)], lag(benchmark_ret[,1], 1), lag(benchmark_ret[, 1], 5));
  data_oot <- na.omit(data_oot)
  gmmhmm(dataset = data_oot, ret_target = benchmark_ret[, 1], n_start = 500, n_state = 3)
}

test_oot2 <- function() {
  ret_zz500 <- benchmark_ret[, 1]
  ret_hs300 <- benchmark_ret[, 2]
  ret_hengsheng <- benchmark_ret[, 5]
  
  ema2 <- TTR::EMA(benchmark[,1], 2);
  ema5 <- TTR::EMA(benchmark[,1], 5);
  data_oot <- cbind.xts(ret_zz500, ret_zz500 - ret_hs300, ret_zz500 - ret_hengsheng,
              Return.calculate(ema2),  Return.calculate(ema5),
   #           Return.calculate(TTR::EMA(benchmark[, 2]), 2),
              lag(ret_zz500, 1), lag(ret_zz500, 5));
  data_oot <- na.omit(data_oot)
  ret <- gmmhmm(dataset = data_oot, ret_target = benchmark_ret[, 1], n_start = 1000, n_state = 5)
  write.csv(as.data.frame(ret), 'test_results/oot2.csv')
}

test_oot3 <- function() {
  ret_zz500 <- benchmark_ret[, 1]
  ret_hs300 <- benchmark_ret[, 2]
  ret_hengsheng <- benchmark_ret[, 5]
  
  ret_zz500_ema2 <- Return.calculate(TTR::EMA(benchmark[,1], 2))
  ret_zz500_ema5 <- Return.calculate(TTR::EMA(benchmark[,1], 5))
  ret_hs300_ema2 <- Return.calculate(TTR::EMA(benchmark[,2], 2))
  ret_hs300_ema5 <- Return.calculate(TTR::EMA(benchmark[,2], 5))
  
  
  data_oot3 <- cbind.xts(ret_zz500, ret_zz500 - ret_hs300, ret_zz500 - ret_hengsheng,
                        ret_zz500_ema2, ret_zz500_ema5,
                        ret_zz500_ema2 - ret_hs300_ema2,
                        #           Return.calculate(TTR::EMA(benchmark[, 2]), 2),
                        lag(ret_zz500, 1), lag(ret_zz500, 5));  
  data_oot3 <- na.omit(data_oot3)
  ret_oot3 <- gmmhmm(dataset = data_oot3, ret_target = data_oot3[, 1], n_start = 1000, n_state = 5)
  rbind(table.AnnualizedReturns(ret_oot3), SharpeRatio(ret_oot3), maxDrawdown(ret_oot3))
  write.csv(as.data.frame(ret), 'test_results/oot3.csv')
}

## 使用最新的数据（截止到2015年10月的
source("gmmhmm.R")
test_oot4 <- function() {
  data <- read.csv("data/Index_3.csv")
  benchmark <- as.xts(data[, 2:4], order.by=strptime(data[,1], format="%Y/%m/%d", tz=""))
  benchmark_w <- benchmark[endpoints(benchmark, on = "weeks")]
  benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))
  benchmark_ret_w <- na.omit(Return.calculate(benchmark_w, method="discrete"))
  
  ret_zz500 <- benchmark_ret[, 1]
  ret_hs300 <- benchmark_ret[, 2]
  ret_hengsheng <- benchmark_ret[, 3]
  
  ret_zz500_ema2 <- Return.calculate(TTR::EMA(benchmark[,1], 2))
  ret_zz500_ema5 <- Return.calculate(TTR::EMA(benchmark[,1], 5))
  ret_hs300_ema2 <- Return.calculate(TTR::EMA(benchmark[,2], 2))
  ret_hs300_ema5 <- Return.calculate(TTR::EMA(benchmark[,2], 5))
  
  rsi <- TTR::RSI(ret_zz500 - ret_hs300);
  macd <- TTR::MACD(ret_zz500 - ret_hs300);
  
  data_oot4 <- cbind.xts(ret_zz500 , ret_hs300 #ret_hs300 - ret_hengsheng,
                         #ret_hs300_ema2, ret_hs300_ema5, ret_zz500_ema2
                         #           Return.calculate(TTR::EMA(benchmark[, 2]), 2),
                         # rsi, macd$macd - macd$signal
                         );  
  data_oot4 <- na.omit(data_oot4)
  ret_oot4 <- gmmhmm(dataset = data_oot4, ret_target = data_oot4[, 1], n_start = 1500, n_state = 5)
  rbind(table.AnnualizedReturns(ret_oot4), SharpeRatio(ret_oot4), maxDrawdown(ret_oot4))
  write.csv(as.data.frame(ret), 'test_results/oot4.csv')
  
  
}

## 测试5分钟股指期货
source("gmmhmm.R")
test_oot5 <- function() {
  data <- read.csv("data/Future_5min.csv")
  benchmark <- na.omit(as.xts(data[, 2:4], order.by=strptime(data[,1], format="%Y/%m/%d %H:%M", tz="")))
  benchmark_w <- benchmark[endpoints(benchmark, on = "weeks")]
  benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))
  benchmark_ret_w <- na.omit(Return.calculate(benchmark_w, method="discrete"))
  
  ret_hs300 <- benchmark_ret[, 1]
  ret_zz500 <- benchmark_ret[, 2]
  ret_sz50 <- benchmark_ret[, 3]
  
  ret_hs300_ema2 <- Return.calculate(TTR::EMA(benchmark[,1], 2))
  ret_hs300_ema5 <- Return.calculate(TTR::EMA(benchmark[,1], 5))
  ret_zz500_ema2 <- Return.calculate(TTR::EMA(benchmark[,2], 2))
  ret_zz500_ema5 <- Return.calculate(TTR::EMA(benchmark[,2], 5))
  
  rsi <- TTR::RSI(ret_zz500 - ret_hs300);
  macd <- TTR::MACD(ret_zz500 - ret_hs300);
  
  data_oot4 <- na.omit(cbind.xts(ret_zz500, ret_zz500 - ret_hs300, ret_zz500 - ret_hengsheng,
                         ret_zz500_ema2, ret_zz500_ema5
                         #           Return.calculate(TTR::EMA(benchmark[, 2]), 2),
                         ))
  data_oot4 <- na.omit(data_oot4)
  ret_oot4 <- gmmhmm1(dataset = data_oot4, ret_target = data_oot4[, 1], n_start = 2000, n_state = 0)
  rbind(table.AnnualizedReturns(ret_oot4), SharpeRatio(ret_oot4), maxDrawdown(ret_oot4))
  write.csv(as.data.frame(ret), 'test_results/oot5.csv')
  
  
}



##########################################################################
###  利用全新的指数数据
### Test 1: HS300
##########################################################################
source("gmmhmm.R")
test_new1 <- function() {
  data <- read.csv("data/Index_3.csv")
  benchmark <- as.xts(data[, 2:4], order.by=strptime(data[,1], format="%Y/%m/%d", tz=""))
  benchmark_w <- benchmark[endpoints(benchmark, on = "weeks")]
  benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))
  benchmark_ret_w <- na.omit(Return.calculate(benchmark_w, method="discrete"))
  
  ret_zz500 <- benchmark_ret[, 1]
  ret_hs300 <- benchmark_ret[, 2]
  ret_hengsheng <- benchmark_ret[, 3]
  
  ret_zz500_ema2 <- Return.calculate(TTR::EMA(benchmark[,1], 2))
  ret_zz500_ema5 <- Return.calculate(TTR::EMA(benchmark[,1], 5))
  ret_hs300_ema2 <- Return.calculate(TTR::EMA(benchmark[,2], 2))
  ret_hs300_ema5 <- Return.calculate(TTR::EMA(benchmark[,2], 5))
  
  rsi <- TTR::RSI(ret_zz500 - ret_hs300);
  macd <- TTR::MACD(ret_zz500 - ret_hs300);
  
  data_new1 <- cbind.xts(ret_hs300 #ret_hs300 - ret_hengsheng,
                         #ret_hs300_ema2, ret_hs300_ema5, ret_zz500_ema2
                         #           Return.calculate(TTR::EMA(benchmark[, 2]), 2),
                         # rsi, macd$macd - macd$signal
  );  
  data_new1 <- na.omit(data_new1)
  ret_new1 <- gmmhmm(dataset = data_new1, ret_target = data_new1[, 1], n_start = 1500, n_state = 5)
  rbind(table.AnnualizedReturns(ret_new1), SharpeRatio(ret_new1), maxDrawdown(ret_new1))
  write.csv(as.data.frame(ret_new1), 'test_results/new1.csv')
}
test_new1()


### Test 2: HS300
##########################################################################
source("gmmhmm.R")
test_new2 <- function() {
  data <- read.csv("data/Index_3.csv")
  benchmark <- as.xts(data[, 2:4], order.by=strptime(data[,1], format="%Y/%m/%d", tz=""))
  benchmark_w <- benchmark[endpoints(benchmark, on = "weeks")]
  benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))
  benchmark_ret_w <- na.omit(Return.calculate(benchmark_w, method="discrete"))
  
  ret_zz500 <- benchmark_ret[, 1]
  ret_hs300 <- benchmark_ret[, 2]
  ret_hengsheng <- benchmark_ret[, 3]
  
  ret_zz500_ema2 <- Return.calculate(TTR::EMA(benchmark[,1], 2))
  ret_zz500_ema5 <- Return.calculate(TTR::EMA(benchmark[,1], 5))
  ret_hs300_ema2 <- Return.calculate(TTR::EMA(benchmark[,2], 2))
  ret_hs300_ema5 <- Return.calculate(TTR::EMA(benchmark[,2], 5))
  
  rsi <- TTR::RSI(ret_zz500 - ret_hs300);
  macd <- TTR::MACD(ret_zz500 - ret_hs300);
  
  data_new2 <- cbind.xts(ret_hs300, ret_hs300_ema2, ret_hs300_ema5 #ret_hs300 - ret_hengsheng,
                         #ret_hs300_ema2, ret_hs300_ema5, ret_zz500_ema2
                         #           Return.calculate(TTR::EMA(benchmark[, 2]), 2),
                         # rsi, macd$macd - macd$signal
  );  
  data_new2 <- na.omit(data_new2)
  ret_new2 <- gmmhmm(dataset = data_new2, ret_target = data_new2[, 1], n_start = 1500, n_state = 5)
  rbind(table.AnnualizedReturns(ret_new2), SharpeRatio(ret_new2), maxDrawdown(ret_new2))
  write.csv(as.data.frame(ret_new2), 'test_results/new2.csv')
  return (ret_new2);
}
ret <- test_new2()

### Test 3: HS300, HS300 EMA, RSI
##########################################################################
test_new3 <- function() {
  source("gmmhmm.R")
  data <- read.csv("data/Index_3.csv")
  benchmark <- as.xts(data[, 2:4], order.by=strptime(data[,1], format="%Y/%m/%d", tz=""))
  benchmark_w <- benchmark[endpoints(benchmark, on = "weeks")]
  benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))
  benchmark_ret_w <- na.omit(Return.calculate(benchmark_w, method="discrete"))
  
  ret_zz500 <- benchmark_ret[, 1]
  ret_hs300 <- benchmark_ret[, 2]
  ret_hengsheng <- benchmark_ret[, 3]
  
  ret_zz500_ema2 <- Return.calculate(TTR::EMA(benchmark[,1], 2))
  ret_zz500_ema5 <- Return.calculate(TTR::EMA(benchmark[,1], 5))
  ret_hs300_ema2 <- Return.calculate(TTR::EMA(benchmark[,2], 2))
  ret_hs300_ema5 <- Return.calculate(TTR::EMA(benchmark[,2], 5))
  
  rsi <- TTR::RSI(ret_zz500 - ret_hs300);
  macd <- TTR::MACD(ret_zz500 - ret_hs300);
  
  data_new3 <- cbind.xts(ret_hs300, ret_hs300_ema2, ret_hs300_ema5, #ret_hs300 - ret_hengsheng,
                         #ret_hs300_ema2, ret_hs300_ema5, ret_zz500_ema2
                         #           Return.calculate(TTR::EMA(benchmark[, 2]), 2),
                         rsi/100 #, macd$macd - macd$signal
  );  
  data_new3 <- na.omit(data_new3)
  ret_new3 <- gmmhmm(dataset = data_new3, ret_target = data_new3[, 1], n_start = 1500, n_state = 5)
  rbind(table.AnnualizedReturns(ret_new3), SharpeRatio(ret_new3), maxDrawdown(ret_new3))
  write.csv(as.data.frame(ret_new3), 'test_results/new3.csv')
}
ret <- test_new3()

### Test 4: HS300, HS300 EMA, ZZ500, ZZ500 EMA
##########################################################################
test_new4 <- function() {
  source("gmmhmm.R")
  data <- read.csv("data/Index_3.csv")
  benchmark <- as.xts(data[, 2:4], order.by=strptime(data[,1], format="%Y/%m/%d", tz=""))
  benchmark_w <- benchmark[endpoints(benchmark, on = "weeks")]
  benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))
  benchmark_ret_w <- na.omit(Return.calculate(benchmark_w, method="discrete"))
  
  ret_zz500 <- benchmark_ret[, 1]
  ret_hs300 <- benchmark_ret[, 2]
  ret_hengsheng <- benchmark_ret[, 3]
  
  ret_zz500_ema2 <- Return.calculate(TTR::EMA(benchmark[,1], 2))
  ret_zz500_ema5 <- Return.calculate(TTR::EMA(benchmark[,1], 5))
  ret_hs300_ema2 <- Return.calculate(TTR::EMA(benchmark[,2], 2))
  ret_hs300_ema5 <- Return.calculate(TTR::EMA(benchmark[,2], 5))
  
  rsi_hs300 <- TTR::RSI(ret_hs300);
  macd <- TTR::MACD(ret_zz500 - ret_hs300);
  
  data_new4 <- cbind.xts(ret_hs300, ret_hs300_ema2, ret_hs300_ema5,
                         
                         #ret_hs300 - ret_hengsheng,
                         #ret_hs300_ema2, ret_hs300_ema5, ret_zz500_ema2
                         #           Return.calculate(TTR::EMA(benchmark[, 2]), 2),
                         rsi_hs300/100 #, macd$macd - macd$signal
  );  
  data_new4 <- na.omit(data_new4)
  ret_new4 <- gmmhmm(dataset = data_new4, ret_target = data_new4[, 1], n_start = 500, n_state = 0)
  rbind(table.AnnualizedReturns(ret_new4), SharpeRatio(ret_new4), maxDrawdown(ret_new4))
  write.csv(as.data.frame(ret_new4), 'test_results/new4.csv')
}
ret <- test_new4()


### Test 5＃: HS300, HS300 EMA, ZZ500, ZZ500 EMA
##########################################################################
test_new4 <- function() {
  source("gmmhmm.R")
  data <- read.csv("data/Index_3.csv")
  benchmark <- as.xts(data[, 2:4], order.by=strptime(data[,1], format="%Y/%m/%d", tz=""))
  benchmark_w <- benchmark[endpoints(benchmark, on = "weeks")]
  benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))
  benchmark_ret_w <- na.omit(Return.calculate(benchmark_w, method="discrete"))
  
  ret_zz500 <- benchmark_ret[, 1]
  ret_hs300 <- benchmark_ret[, 2]
  #ret_hengsheng <- benchmark_ret[, 3]
  
 
  
  ret_zz500_ema2 <- Return.calculate(TTR::EMA(benchmark[,1], 2))
  ret_zz500_ema5 <- Return.calculate(TTR::EMA(benchmark[,1], 5))
  ret_hs300_ema2 <- Return.calculate(TTR::EMA(benchmark[,2], 2))
  ret_hs300_ema5 <- Return.calculate(TTR::EMA(benchmark[,2], 5))
  ret_hs300_ema20 <- Return.calculate(TTR::EMA(benchmark[,2], 20))
  ret_hs300_ema50 <- Return.calculate(TTR::EMA(benchmark[,2], 50))
  ret_hs300_ema100 <- Return.calculate(TTR::EMA(benchmark[,2], 100))
  
  rsi_hs300 <- TTR::RSI(ret_hs300);
  macd <- TTR::MACD(ret_zz500 - ret_hs300);
  
  data_new4 <- cbind.xts(ret_hs300, ret_hs300_ema2, ret_hs300_ema5, 
                         ret_hs300_ema20,ret_hs300_ema50, ret_hs300_ema100
                         
                         #ret_hs300 - ret_hengsheng,
                         #ret_hs300_ema2, ret_hs300_ema5, ret_zz500_ema2
                         #           Return.calculate(TTR::EMA(benchmark[, 2]), 2),
                         # rsi_hs300/100 #, macd$macd - macd$signal
  );  
  data_new4 <- na.omit(data_new4) 
  ret_new4 <- gmmhmm(dataset = data_new4, ret_target = data_new4[,2], n_start = 2000, n_state = 5)
                                                                                                                                                  
  erbind(table.AnnualizedReturns(ret_new4), SharpeRatio(ret_new4), maxDrawdown(ret_new4))
  write.csv(as.data.frame(ret_new4), 'test_results/new4.csv')
}
ret <- test_new4()
