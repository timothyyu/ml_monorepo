source("gmmhmm.R")

### GMM In-sample Test Case
##################################################################################
# 读取数据
data <- read.csv("index_szsh.csv")
benchmark <- as.xts(data[, 2:3], order.by=strptime(data[,1], format = "%m/%d/%y", tz = ""))

# 日和周回报率
ret_benchmark <- na.omit(Return.calculate(benchmark, method = "discrete"))
ret_benchmark_weeklys <- na.omit(Return.calculate(benchmark[endpoints(benchmark,on =  "weeks")]), method = "discrete")
# 5日和10日回报率， 5日回报率与周回报率不同（5日回报率为当日与5日前回报率， 每日均有）
ret_benchmark_5d <- na.omit(benchmark / lag(benchmark, 5) - 1) 
ret_benchmark_10d <- na.omit(benchmark / lag(benchmark, 10) - 1)

# 测试1: 准备训练GMM的数据, 使用上海指数
dataset_full_case1 <- na.omit(cbind(ret_benchmark[, 1], lag(ret_benchmark[, 1], 1), 
                                    lag(ret_benchmark[, 1], 2), ret_benchmark_5d[, 1],
                                    lag(ret_benchmark_5d[,1], 1)))

start_nr <- 4000;
end_nr <- nrow(dataset_full_case1);
dataset_train_case1 <- dataset_full_case1[start_nr:end_nr]
benchmark_train_case1 <- benchmark[,1][start_nr:end_nr]
ret_train_case1 <- ret_benchmark[,1][start_nr:end_nr]
gmm_insample_test(dataset_train_case1, benchmark_train_case1, ret_train_case1)

### DataAdapter
#########################################################
require(RMySQL)
DBConnector <- function(){
  db <- list();
  db$host <- "127.0.0.1"
  db$username <- "root"
  
  return(dbConnect(RMySQL::MySQL(), host = db$host, 
                    user = db$username))
  
}

GmmStrategy_DataAdapter <- function(){
  dbcon <- DBConnector();
  strategy_db <- list();
  strategy_db$db_name <- "stocks"
  strategy_db$db_table <- "strategy_position"
  
  
  
  
}
