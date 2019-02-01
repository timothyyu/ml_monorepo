library(RMySQL)

mysql_fund_values <- function(fund_codes, start_date, end_date){
  conn <- dbConnect(MySQL(), dbname = "mofang", host="182.92.214.1", username="jiaoyang", password="Mofang123")

  
  result <- NA;
  i <- 1;
  
  for(code in fund_codes){
    
    sql <- sprintf("select fi_globalid from fund_infos where fi_code = %d", code);
    
    fund_mofang_id <- dbGetQuery(conn, sql)
    
    id <- fund_mofang_id$fi_globalid
    
    sql <- sprintf("select fv_time, fv_authority_value from fund_value where fv_fund_id = %d and fv_time >= '%s' and fv_time <= '%s'", id, start_date, end_date);
    
    #print(sql);
    
    values <- dbGetQuery(conn,sql);
    
    if( i == 1){
      result <- values;
    }else{
      result <- merge(result ,values, by.x="fv_time", by.y="fv_time");
    }
    i <- i + 1;
    
  }
  
  nr_fund <- length(fund_codes)
  
  output <- as.xts(result[, 2:(nr_fund+1)], order.by=strptime(result[,1],
                              format="%Y-%m-%d", tz=""))
  colnames(output) <- fund_codes
  
  
  dbDisconnect(conn);
  return(output);
}

#fund_codes <- c(160119, 000051, 000216, 050025, 000071)
#res <- mysql_fund_values(fund_codes,'2015-09-30','2015-10-13')
#print(res)