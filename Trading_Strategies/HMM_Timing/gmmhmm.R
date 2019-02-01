require(mhsmm)
require(mclust)
require(xts)
require(PortfolioAnalytics)
require(PerformanceAnalytics)
require(TTR)

# GMM Training Model 
# using return data as input data, calibrate n-centroids gaussian mixture model
# and find the most-likely model with the lowerest BIC setup
# input -
#     data_training: the training data set (as Data.Frame )
#     nstate: default = 0. the number of states to specify. If nstate=0, the function will find the 
#             optimal number of nstates. 
# output - gmm model, including 
#     J: (number of centroids)
#     b: (mean, vcv)
#     gmm: (gmm model calibrated)
##########################################################################
gmm_training <- function(data_training, nstate=0) {
  output <- list();
  
  if (nstate == 0) {
    mm_model <- Mclust(data_training);
  }
  else {
    mm_model <- Mclust(data_training, G = nstate)
  }
  mm_output <- summary(mm_model);
  
  ### determine whether training dataset is a single serie or multiples
  n_serie <- ncol(data_training)  
  
  #### creating the HMM model
  J <- mm_output$G
  #print(paste("Nr of Regimes ", J))
  initial <- rep(1/J, J)
  P <- matrix(rep(1/J, J*J), nrow=J)
  
  if (n_serie == 1) {
    mean <- as.numeric(mm_output$mean)
    vcv <- as.numeric(mm_output$variance)
  }
  else
  {
    mean <- list()
    vcv <- list()
    for (j in 1:J){
      mean[[j]] <- mm_output$mean[, j]
      vcv[[j]] <- mm_output$variance[,,j]
    }
  }
  
 
  b <- list()
  b$mu <- mean
  b$sigma <- vcv
  
  output$gmm <- mm_model
  output$b <- b;
  output$J <- J;
  output$initial <- initial;
  output$P <- P;
  output$mean <- mean;
  output$vcv <- vcv;
  return(output);
}



# GMM 交易测试工具
# 这里我们使用GMM做in-the-sample样本内测试。 通过gmm_training方程的帮助， 对测试数据进行分类， 
# 找到最佳的市场状态数，以及各个时间点的市场状态分类。 
# 最后我们将各个市场状态下的回报曲线计算出来。 
##########################################################################
gmm_insample_test <- function(dataset_train, benchmark_train, ret_train) {
  output <- gmm_training(data_training = dataset_train)
  print(paste("regime = ", output$J))
  #output$gmm$classification - 每个数据代表的市场状态
  #output$gmm$pro - 每个市场状态的几率
  
  # 根据不同的市场状态排序
  ranked_regimes <- rank(output$gmm$parameters$mean)
  ranked_classification <- ranked_regimes[output$gmm$classification]
  dates <- index(as.xts(output$gmm$classification))
  regimes <- as.xts(ranked_classification, 
                    order.by=dates)
  
  ## 画出图形
  plot(benchmark_train)
  points(benchmark_train *  (regimes == 1), pch=20,  col="black")
  points(benchmark_train * (regimes == 2), pch=20, col="green")
  points(benchmark_train * (regimes == 3), pch=20, col="red")
  points(benchmark_train * (regimes == 4), pch=20, col="orange")
  points(benchmark_train * (regimes == 5), pch=20, col="blue")
  
  ## 根据不同市场状态的投资回报
  ret_regimes <- na.omit(cbind(
    ret_train * (regimes==1), 
    ret_train *(regimes==2),
    ret_train * (regimes==3), 
    #data_test1[, 1] * (regimes==4), 
    #data_test1[, 1] * (regimes==5), 
    ret_train))
  charts.PerformanceSummary(ret_regimes)
  rbind(table.AnnualizedReturns(ret_regimes), maxDrawdown(ret_regimes), CalmarRatio(ret_regimes))
  
  ### 返回不同市场状态下的数据
  output <- list()
  output$ret <- ret_regimes
  return(output)
}


##################################################################################
hmm_training2 <- function(gmm, data_training) {
  output <- list();
  
  ### determine whether training dataset is a single serie or multiples
  n_serie <- ncol(data_training)  
  
  #### training HMM model
  if (n_serie == 1) {
    hmm_model <- hmmspec(init=gmm$initial, trans=gmm$P, parms.emission = gmm$b, dens.emission = dnorm.hsmm)
    hmm_fitted <- hmmfit(as.numeric(data_training), hmm_model, mstep = mstep.norm)
  }
  else {
    hmm_model <- hmmspec(init=gmm$initial, trans=gmm$P, parms.emission = gmm$b, dens.emission = dmvnorm.hsmm)
    hmm_fitted <- hmmfit(data_training, hmm_model, mstep = mstep.mvnorm)
  }
  #print("hmm fitting")
  #### Predict future regime
  regime <- tail(hmm_fitted$yhat, 1);
  output$hmm <- hmm_fitted
  
  return(output) 
}
##################################################################################
hmm_training <- function(gmm, data_training, data_testing = NULL, ret_target) {
  output <- list();
  
  ### determine whether training dataset is a single serie or multiples
  n_serie <- ncol(data_training)  
  
  #### training HMM model
  if (n_serie == 1) {
    hmm_model <- hmmspec(init=gmm$initial, trans=gmm$P, parms.emission = gmm$b, dens.emission = dnorm.hsmm)
    hmm_fitted <- hmmfit(as.numeric(data_training), hmm_model, mstep = mstep.norm)
  }
  else {
    hmm_model <- hmmspec(init=gmm$initial, trans=gmm$P, parms.emission = gmm$b, dens.emission = dmvnorm.hsmm)
    hmm_fitted <- hmmfit(data_training, hmm_model, mstep = mstep.mvnorm)
  }
  #print("hmm fitting")
  #### Predict future regime
  regime <- tail(hmm_fitted$yhat, 1);
  output$hmm <- hmm_fitted
  
  ############################################################
  #### In the training set, the regimes and returns
  yhat_train <- as.xts(hmm_fitted$yhat, order.by = index(data_training), tzone=tzone(data_training))
  ret_training_regime <- list()
  for (k in 1:gmm$J) {
    ret_training_regime[[k]] <- ret_target * (yhat_train == k)
  }
  ret_training_regime <- do.call(cbind, ret_training_regime)
  
  output$hmm_yhat <- yhat_train
  output$hmm_ret_regime <- ret_training_regime
  output$hmm_predict_regime <- tail(output$hmm_yhat, 1);
  
  print(sum(ret_training_regime))
  
  ### calculate the risk measures 
  sharpe_training_regime_vol <- SharpeRatio.annualized(ret_training_regime)[1,]
  max_sharpe_regime <- match(max(sharpe_training_regime_vol), sharpe_training_regime_vol)
  #calmar_training_regime <- CalmarRatio(ret_training_regime)
  #max_calmar_regime <- match(max(calmar_training_regime), calmar_training_regime)
  #sortino_training_regime <- SortinoRatio(ret_training_regime)
  #max_sortino_regime <- match(max(sortino_training_regime), sortino_training_regime)
  #output$hmm_ret_regime_annualized <- Return.annualized(ret_training_regime)
  
  print(sharpe_training_regime_vol)

  
  output$sharpe_ratio <- sharpe_training_regime_vol;
  output$sharpe_ratio_max_regime <- max_sharpe_regime;
  #output$calmar_ratio <- calmar_training_regime;
  #output$calmar_ratio_max_regime <- max_calmar_regime;
  #output$sortino_ratio <- sortino_training_regime;
  #output$sortino_ratio_max_regime <- max_sortino_regime;
  
  
  
  return(output);
  
}


##################################################################################
hmm_training1 <- function(gmm, data_training, data_testing = NULL, ret_target) {
  output <- list();
  
  ### determine whether training dataset is a single serie or multiples
  n_serie <- ncol(data_training)  
  
  #### training HMM model
  if (n_serie == 1) {
    hmm_model <- hmmspec(init=gmm$initial, trans=gmm$P, parms.emission = gmm$b, dens.emission = dnorm.hsmm)
    hmm_fitted <- hmmfit(as.numeric(data_training), hmm_model, mstep = mstep.norm)
  }
  else {
    hmm_model <- hmmspec(init=gmm$initial, trans=gmm$P, parms.emission = gmm$b, dens.emission = dmvnorm.hsmm)
    hmm_fitted <- hmmfit(data_training, hmm_model, mstep = mstep.mvnorm)
  }
  #print("hmm fitting")
  #### Predict future regime
  regime <- tail(hmm_fitted$yhat, 1);
  pred <- predict(hmm_fitted, data_testing)
  
  ############################################################
  #### In the training set, the regimes and returns
  yhat_train <- as.xts(pred$s, order.by = index(data_testing), tzone=tzone(data_testing))
  ret_training_regime <- list()
  for (k in 1:gmm$J) {
    ret_training_regime[[k]] <- ret_target * (yhat_train == k)
  }
  ret_training_regime <- do.call(cbind, ret_training_regime)
  
  output$hmm_yhat <- yhat_train
  output$hmm_ret_regime <- ret_training_regime
  output$hmm_predict_regime <- tail(output$hmm_yhat, 1);
  
  
  return(output);
  
}

gmmhmm_training <- function(data_training) {
  output <- list();
  
  #### Using Mixture Model to determine the optimal number of regimes and the settings under 
  #### each regime
  mm_model <- Mclust(data_training);
  mm_output <- summary(mm_model);
  output$gmm <- mm_model;
  
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
  
  output$hmm <- hmm_fitted
  
  ############################################################
  #### In the training set, the regimes and returns
  yhat_train <- as.xts(hmm_fitted$yhat, order.by = index(data_training), tzone=tzone(data_training))
  ret_training_regime <- list()
  for (k in 1:J) {
    ret_training_regime[[k]] <- data_training[,1] * (yhat_train == k)
  }
  ret_training_regime <- do.call(cbind, ret_training_regime)
  
  output$hmm_yhat <- yhat_train
  output$hmm_ret_regime <- ret_training_regime
  output$hmm_predict_regime <- tail(output$hmm_yhat, 1);
  
  
  ### calculate the risk measures 
  sharpe_training_regime_vol <- SharpeRatio(ret_training_regime)[2,]
  max_sharpe_regime <- match(max(sharpe_training_regime_vol), sharpe_training_regime_vol)
  calmar_training_regime <- CalmarRatio(ret_training_regime)
  max_calmar_regime <- match(max(calmar_training_regime), calmar_training_regime)
  sortino_training_regime <- SortinoRatio(ret_training_regime)
  max_sortino_regime <- match(max(sortino_training_regime), sortino_training_regime)
  output$hmm_ret_regime_annualized <- Return.annualized(ret_training_regime)
  
  output$sharpe_ratio <- sharpe_training_regime_vol;
  output$sharpe_ratio_max_regime <- max_sharpe_regime;
  output$calmar_ratio <- calmar_training_regime;
  output$calmar_ratio_max_regime <- max_calmar_regime;
  output$sortino_ratio <- sortino_training_regime;
  output$sortino_ratio_max_regime <- max_sortino_regime;
  

  
  return(output);
}

## out of sample test for GMM+HMM
####################################################################
gmmhmm <- function(dataset, ret_target, n_start, n_state = 0) {
  n <- nrow(dataset) 
  ret_s1 <- ret_target * 0;
  for (i in n_start:(n-1)) {
    data_training <- dataset[(i - n_start + 1):i,];
    ## determine whether training dataset is a single serie or multiples
    n_serie <- ncol(data_training)  
    
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
    if (n_serie == 1) {
      mean <- as.numeric(mm_output$mean)
      vcv <- as.numeric(mm_output$variance)
    }
    else
    {
      mean <- list()
      vcv <- list()
      for (j in 1:J){
        mean[[j]] <- mm_output$mean[, j]
        vcv[[j]] <- mm_output$variance[,,j]
      }
    }
    
    b <- list()
    b$mu <- mean
    b$sigma <- vcv
    
    
    
    
    #### training HMM model
    #### training HMM model
    if (n_serie == 1) {
      hmm_model <- hmmspec(init=initial, trans=P, parms.emission = b, dens.emission = dnorm.hsmm)
      hmm_fitted <- hmmfit(as.numeric(data_training), hmm_model, mstep = mstep.norm)
    }
    else {
      hmm_model <- hmmspec(init=initial, trans=P, parms.emission = b, dens.emission = dmvnorm.hsmm)
      hmm_fitted <- hmmfit(data_training, hmm_model, mstep = mstep.mvnorm)
    }
    #hmm_model <- hmmspec(init=initial, trans=P, parms.emission = b, dens.emission =dmvnorm.hsmm)
    #hmm_fitted <- hmmfit(data_training, hmm_model, mstep = mstep.mvnorm)
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
    ret_training_regime <- mean(ret_training_regime)
    
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
    
    #selected_ret <- next_ret * ((regime == top_regime1 & ret_avg_regime1 > 0) | 
    #                              (regime == top_regime2 & ret_avg_regime2 > 0))
    #selected_ret <- next_ret * ((regime == top_regime1 & ret_avg_regime1 > 0) )
    selected_ret <- next_ret * (regime == top_regime1 | regime == top_regime2)
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
    
  }
  
  ret_c <- cbind(ret_s1[n_start:n,], ret_target[n_start:n,])
  save(ret_c, "ret_c.data")
  charts.PerformanceSummary(ret_c)
  #rbind(table.AnnualizedReturns(ret_c), maxDrawdown(ret_c), CalmarRatio(ret_c))
  return(ret_c)
  
}

gmmhmm1 <- function(dataset, ret_target, n_start, n_state = 0) {
  n <- nrow(dataset) 
  ret_s1 <- ret_target * 0;
  for (i in n_start:n) {
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
    ret_training_regime <- mean(ret_training_regime)
    
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
    
    #selected_ret <- next_ret * ((regime == top_regime1 & ret_avg_regime1 > 0) | 
    #                              (regime == top_regime2 & ret_avg_regime2 > 0))
    #selected_ret <- next_ret * ((regime == top_regime1 & ret_avg_regime1 > 0) )
    
    #selected_ret <- next_ret * (regime == top_regime1 | regime == top_regime2)
    selected_ret <- next_ret * (regime == top_regime1)
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
  }
  
  ret_c <- cbind(ret_s1[n_start:n,], ret_target[n_start:n,])
  #rbind(table.AnnualizedReturns(ret_c), maxDrawdown(ret_c), CalmarRatio(ret_c))
  return(ret_c)
  
}



gmmhmm2 <- function(dataset, ret_target, n_start, n_state = 0) {
  n <- nrow(dataset) 
  ret_s1 <- ret_target * 0;
  for (i in n_start:n) {
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
  }
  
  ret_c <- cbind(ret_s1[n_start:n,], ret_target[n_start:n,])
  #rbind(table.AnnualizedReturns(ret_c), maxDrawdown(ret_c), CalmarRatio(ret_c))
  return(ret_c)
  
}


regime_gmmhmm <- function(price_data, target_index = 1, nstate = 0) {
  prices <- na.omit(price_data);
  ret <- ROC(prices, n = 1, type = "continuous")
  #ret <- Return.calculate(prices[endpoints(prices, on=period)], method = "log")
  ret <- na.omit(ret)
  gmm <- gmm_training(ret, nstate) # GMM 捕捉指定数量的市场状态， 并生成相应的参数；
  hmm <- hmm_training(gmm, data_training = ret, ret_target = ret[, target_index])
  return(hmm)
  
}

