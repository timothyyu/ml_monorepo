


##### 全局分型 Hurst Index
##### 计算log(R)和log(S)
#######################################################
RS <- function(data) {
  
  data = na.omit(data)
  m = mean(data)
  Y = data - m
  Z = cumsum(Y)
  R = (max(Z) - min(Z))
  S = sd(Y)
  RS = R / S
  n = length(data)
  
  result <- list()
  result$RS <- log(RS)
  result$N <- log(n)
  return(result)
}

### RS1 - 计算R/S = Log(R) / Log(S)
##################################################
RS1 <- function(data) {
  
  result <- RS(data);
  rs <- result$RS / result$N
  return(rs)
}

### Expected RS - 计算预期的平均RS
### 预期的RS与k - 数据的长度有关
##########################################################
ExpectedRS <- function(k) {
  expRS <- ((k -0.5)/k)*((k*pi/2)^(-0.5))*sum(sqrt(k/c(1:(k-1)) - 1))
  return (expRS)
}


GlobalHurst <- function(data, n) {
  
  
  hurst <- list()
  i <- 1
  i_next <- i + n - 1
  
  len <- nrow(data)
  count <- 1
  
  list_RS <- list();
  while (i_next <= len) {
    
    list_RS[[count]] <- RS(data[i:i_next])$RS;
    
    i <- i_next
    i_next <- i_next + n - 1
    count <- count + 1
  }
  list_RS <- do.call(rbind, list_RS)
  RS <- mean(list_RS);
  
  
  result <- list();
  result$RS <- RS;
  result$N <- log(n);
  result$hurst <- RS / log(n);
  return(result)
  
}

