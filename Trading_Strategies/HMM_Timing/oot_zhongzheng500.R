source('gmmhmm.R')
test_oot3 <- function() {
  data <- read.csv("data/NAV_5ETFs_updated.csv")
  benchmark <- na.omit(as.xts(data[, 2:6], order.by=strptime(data[,1], format="%Y/%m/%d", tz="")))
  benchmark_ret <- na.omit(Return.calculate(benchmark, method = "discrete"))
  
  zz500 <- benchmark[, 1]
  hs300 <- benchmark[, 2]
  spx <- benchmark[, 3]
  gold <- benchmark[, 4]
  hengsheng <- benchmark[, 5]
  
  ret_zz500_d <-  TTR::ROC(zz500, n=1, "discrete")
  ret_zz500_2d <- TTR::ROC(zz500, n=2, "discrete")
  ret_zz500_2d <- na.omit(zz500 / lag(zz500, 2) - 1)
  ret_zz500_5d <- na.omit(zz500 / lag(zz500, 5) - 1)
  ret_zz500_20d <- na.omit(zz500 / lag(zz500, 10) - 1)
  
  ret_hs300_d <- na.omit(hs300 / lag(hs300, 1) - 1)
  ret_hs300_2d <- na.omit(hs300 / lag(hs300, 2) - 1)
  ret_hs300_5d <- na.omit(hs300 / lag(hs300, 5) - 1)
  ret_hs300_20d <- na.omit(hs300 / lag(hs300, 20) - 1)
  
  
  zz500_w <- zz500[endpoints(zz500, on = "weeks")]
  hs500_w <- hs300[endpoints(hs300, on = "weeks")]
  
  ret_zz500_w <- na.omit(zz500_w / lag(zz500_w, 1) - 1)
  ret_zz500_w_5d <- na.omit(zz500_w / lag(zz500_w, 5) - 1)
  
  ret_zz500_spread <- ret_zz500_d - lag(ret_zz500_d, 1);
  
  
  
  source("gmmhmm.R")
  data_oot3 <- cbind.xts( TTR::ROC(zz500, n = 1),
                          TTR::ROC(zz500, n = 2), 
                          TTR::ROC(hs300, n = 2)
  )
  data_oot3 <- na.omit(data_oot3[is.infinite(data_oot3[,1]) == FALSE]);
  #ret <- gmmhmm2(dataset=data_oot3, ret_target=ret_zz500_d[index(data_oot3)], n_start=1000, n_state=5)
  
  dataset=data_oot3
  ret_target=ret_zz500_d[index(data_oot3)]
  n_start=1000
  n_state=5
  
  n <- nrow(dataset) 
  ret_s1 <- ret_target * 0;
  probabilty_regimes <- {}
  sharpe_regimes <- {}
  
  for (i in n_start:(n-1)) {
    data_training <- dataset[(i - n_start + 1):i,];
    
    #### Using Mixture Model to determine the optimal number of regimes and the settings under 
    #### each regime
    if (n_state == 0) {
      mm_model <- Mclust(data_training) }
    else {
      mm_model <- Mclust(data_training, G = n_state)}
    mm_output <- summary(mm_model)
    
    #### creating the HMM model
    J <- mm_output$G
    print(paste("Nr of Regimes ", J))
    initial <- rep(1/J, J)
    P <- matrix(rep(1/J, J*J), nrow=J)
    mean <- list()
    vcv <- list()
    for (j in 1:J){
      mean[[j]] <- mm_output$mean[, j]
      vcv[[j]] <- mm_output$variance[,,j]
    }
    b <- list()
    b$mu <- mean
    b$sigma <- vcv
    
    #### training HMM model
    
    hmm_model <- hmmspec(init=initial, trans=P, parms.emission = b, dens.emission =dmvnorm.hsmm)
    hmm_fitted <- hmmfit(data_training, hmm_model, mstep = mstep.mvnorm)
    print("hmm fitting")
    #### Predict future regime
    regime <- tail(hmm_fitted$yhat, 1);
    
    ############################################################
    #### In the training set, the regimes and returns
    yhat_train <- as.xts(hmm_fitted$yhat, order.by = index(data_training), tzone=tzone(data_training))
    ret_training_regime <- list()
    for (k in 1:J) {
      ret_training_regime[[k]] <- data_training[,1] * (yhat_train == k)
    }
    ret_training_regime <- do.call(cbind, ret_training_regime)
    
    
    ### calculate the risk measures 
    sharpe_training_regime_vol <- SharpeRatio(ret_training_regime)[1,]
    max_sharpe_regime <- match(max(sharpe_training_regime_vol), sharpe_training_regime_vol)
    #calmar_training_regime <- CalmarRatio(ret_training_regime)
    #max_calmar_regime <- match(max(calmar_training_regime), calmar_training_regime)
    #sortino_training_regime <- SortinoRatio(ret_training_regime)
    #max_sortino_regime <- match(max(sortino_training_regime), sortino_training_regime)
    ret_training_regime <- mean.geometric(ret_training_regime)
    
    max_order = sort(sharpe_training_regime_vol, index.return=TRUE, decreasing=TRUE)
    max_order = max_order$ix
    
    top_regime1 <- max_order[1];
    top_regime2 <- max_order[2];
    
    ret_avg_regime1 <- ret_training_regime[top_regime1]
    ret_avg_regime2 <- ret_training_regime[top_regime2]
    
    
    ##################################
    #signal <- gmm_hmm_strategy(data_training, data_test, ret_target);
    
    
    last_ret <- ret_target[i];
    next_ret <- ret_target[i+1];
    
    #selected_ret <- next_ret * (sharpe_training_regime_vol[regime] > 0)
    
    selected_ret <- next_ret * ((regime == top_regime1 & ret_avg_regime1 > 0) | 
                                  (regime == top_regime2 & ret_avg_regime2 > 0))
    #selected_ret <- next_ret * ((regime == top_regime1 & ret_avg_regime1 > 0) )
    
    #selected_ret <- next_ret * (regime == top_regime1 | regime == top_regime2)
    #selected_ret <- next_ret * (regime == top_regime1)
    ret_s1[i+1] <- selected_ret
    
    print(paste("target regime = ", top_regime1));
    print(paste("target regime = ", top_regime2));
    print(paste("current regime = ", regime, ": date = ", as.character(index(ret_target[i]))));
    print(paste("prev ret =", last_ret, 
                ": next ret =", next_ret, ": selected_ret = ", selected_ret));
    print(paste("cumulative ret=", sum(ret_s1)))
    
    if (i >= (n_start+10)){
      ret_c <- cbind(ret_s1[(n_start):(i+1)], ret_target[(n_start):(i+1)])
      charts.PerformanceSummary(ret_c)
      
      #save(ret_c, "ret_c.data")
      
    }
    print(paste("i=", i))
    
    ###### collecting probability and return info
    probabilty_regimes <- rbind(probabilty_regimes, tail(hmm_fitted$p, 1))
    sharpe_regimes <- rbind(sharpe_regimes, sharpe_training_regime_vol)
    
  }
  
  ret_c <- cbind(ret_s1[n_start:n,], ret_target[n_start:n,])
  probabilty_regimes <- rbind(probabilty_regimes, 0)
  probabilty_regimes <- as.xts(probabilty_regimes, order.by=index(ret_c))
  sharpe_regimes <- rbind(sharpe_regimes, 0)
  sharpe_regimes <- as.xts(sharpe_regimes, order.by=index(ret_c))
  
  output <- list()
  output[['oot_ret']] <- ret_c
  output[['predict_prob']] <- probabilty_regimes
  output[['sharpe_regimes']] <- sharpe_regimes
  #rbind(table.AnnualizedReturns(ret_c), maxDrawdown(ret_c), CalmarRatio(ret_c))
  return(output)
  
  
  
}

output <- test_oot3()
write.csv(as.data.frame(output$oot_ret), 'oot_ret.csv')
write.csv(as.data.frame(output$predict_prob), 'oot_predict_prob.csv')
write.csv(as.data.frame(output$sharpe_regimes), 'oot_sharpe.csv')
