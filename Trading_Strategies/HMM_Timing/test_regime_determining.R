source("gmmhmm.R")


## 测试中证500
########################################################################
## 0. 读取指数数据
load_data <- function()
{
  data <- read.csv("data/Index_3.csv")
  benchmark <- as.xts(data[, 2:4], order.by=strptime(data[,1], format="%Y/%m/%d", tz=""))
  benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))
  
  return (benchmark);
}


###########################################################################
### casd2: 5个市场状态
benchmark <- load_data()
benchmark_ret <- Return.calculate(benchmark, method="discrete")

data_case2 <- benchmark_ret
data_case2 <- na.omit(data_case2)

gmm <- gmm_training(data_training = data_case2, nstate = 0)
hmm <- hmm_training(gmm, data_case2, data_case2, data_case2[, 1])

ret_regimes <- cbind.xts(hmm$hmm_ret_regime, data_case2)
charts.PerformanceSummary(ret_regimes)
table.Stats(ret_regimes)
rbind(table.AnnualizedReturns(ret_regimes), table.Distributions(ret_regimes), maxDrawdown(ret_regimes))


#################################################################################


source('gmmhmm.R')
source('mysql.R')

#fund_codes <- c(160119)
fund_codes <- c(000051, 160119)
start_date <- '2010-01-01'
end_date <- '2015-10-13'
res <- mysql_fund_values(fund_codes, start_date, end_date) 
#res <- res[1:1404]


res_weekly <- res[endpoints(res, on = "weeks")]
#ret_weekly <- TTR::ROC(res_weekly, 1)
hmm <- regime_gmmhmm(res, 1, 3)

res_total <- na.omit(cbind.xts(hmm$hmm_ret_regime, ROC(res_weekly, 1)))
charts.PerformanceSummary(res_total)
 


