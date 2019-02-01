source( "utils.R")
source( "models.R")

bars2df <- function(bars) {
  #this is stupidly slow, i think rbind is stupid.
  df <- as.data.frame(do.call("rbind", lapply(bars, getBarData)))
  names(df) <- c("secid", "closes")
  df$closes <- ts(df$closes)
  df$logrels <- sapply(df$closes, function(x) {diff(log(x))})
  df
}

getBarData <- function(bar) {
  list(bar$first$getSecId(), bar$second$closeArray())
}

create.logrels <- function(price.arr) {
  array()
}

get.fit <- function(merged) {
  depvar <- sapply(merged$logrels, "[", c(1))
  fit <- lm(depvar ~ merged$val)
}

fit.attr <- function(indeps, deps, intercept = TRUE) {
  merged <- merge(indeps, deps, by.x = c("secid", "born"), by.y = c("secid", "born"))
  if ( length(merged$x)>0 && length(merged$y)>0 ) {
     if ( intercept )
        fit <- lm( merged$y ~ merged$x )
     else
        fit <- lm( merged$y ~ 0 + merged$x)
  }
  else {
     fit <- NULL
  }
  return(fit)
}

weighted.fit.attr <- function(indeps, deps, weights, intercept = TRUE) {
  merged1 <- merge(indeps, weights, by.x = c("secid", "born"), by.y = c("secid", "born"))
  merged2 <- merge(merged1, deps, by.x = c("secid", "born"), by.y = c("secid", "born"))
  if ( length(merged2$x) >0 && length(merged2$y)>0) {
      if ( intercept )
         fit <- lm( merged2$y ~ merged2$x, weights=merged2$weight )
      else
         fit <- lm( merged2$y ~ 0 + merged2$x, weights=merged2$weight )
  }
  else{
      fit <- NULL
  }
  return(fit)
}

load.indep.variables <- function(dir, files) {
  variables=list()
  for ( file in files ) {
     name=strsplit(file,"\\.gz")[[1]]
     print(paste("Loading: ", name))
     variables[[name]] <- read.table(gzfile(paste(dir,file,sep="/")), sep="|", col.names=c("secid", "x", "born"), fill=TRUE, colClasses = c("integer", "numeric", "character"))
  }
  return(variables)
}

load.dep.variables <- function(dir, files) {
  variables=list()
  for ( file in files ) {
     name=strsplit(file,"\\.gz")[[1]]
     print(paste("Loading: ",name))
     variables[[name]] <- read.table(gzfile(paste(dir,file,sep="/")), sep="|", col.names=c("secid", "y", "born"), fill=TRUE, colClasses = c("integer", "numeric", "character"))
  }
  return(variables)
}



indep.intra.attrs <- c(
                       "hlC_BS_MA-BINDNAME1", "hl0_BS_MA-BINDNAME1",
                       "hlC_BS_MA-SIC", "hl0_BS_MA-SIC",

                       "qhlC_BS_MA-BINDNAME1", "qhl0_BS_MA-BINDNAME1",
                       "qhlC_BS_MA-SIC", "qhl0_BS_MA-SIC",

                       "o2cC_BAdj_BS_MA-BINDNAME1", "o2c0_BAdj_BS_MA-BINDNAME1",
                       "o2cC_BAdj_BS_MA-SIC",  "o2c0_BAdj_BS_MA-SIC",

                       "barraRRC", "barraRR0",
                       
                       "baSize_1", "baSizeSQ_1", "baDollarsEff_1", "baDollars_1",                       
                       
                       "pcaRet", "pcaRet_1_3", "pcaRet_2_3", "pcaRet_3_3", "pcaRet_4_3",

                       "o2cC_VAdj_BAdj_BS_MA-BINDNAME1",
                       
                       "baDollarsEff_Y_MA-BINDNAME1", "baDollars_Y_MA-BINDNAME1", "baSize_Y_MA-BINDNAME1", "baSizeSQ_Y_MA-BINDNAME1", 
                       "baDollarsEff_S_MA-BINDNAME1", "baDollars_S_MA-BINDNAME1", "baSize_S_MA-BINDNAME1", "baSizeSQ_S_MA-BINDNAME1", 

                       "c2oC_BAdj_BS_MA-BINDNAME1",
                       "c2oC_BAdj_BS_MA-SIC",

                       "EPS_Q_CE_Diff_BS_MA-BINDNAME1_ST-1", "TARGETPRICE_CE_Diff_BS_MA-BINDNAME1_ST-1", "EPS_Q_DE_Diff_BS_MA-BINDNAME1_ST-1", "TARGETPRICE_DE_Diff_BS_MA-BINDNAME1_ST-1",
                       "EPS_Q_CE_Diff_BS_ST-1", "TARGETPRICE_CE_Diff_BS_ST-1", "EPS_Q_DE_Diff_BS_ST-1", "TARGETPRICE_DE_Diff_BS_ST-1", "ratDiffC_BS_ST-1", "ratDiffD_BS_ST-1", 
                       
                       "advp",
                       "SPREAD"
                       )

indep.attrs <- c(
                 "rnews", "rnews_D-1.0",
                 
                 "FULL1", "FULL2", "FULL3", "FULL5", "FULL10", "FULL20", "FULL30",
                 
                 "hlC_BS_MA-BINDNAME1", "hl0_BS_MA-BINDNAME1",
                 "hlC_BS_MA-SIC", "hl0_BS_MA-SIC",

                 "qhlC_BS_MA-BINDNAME1", "qhl0_BS_MA-BINDNAME1",
                 "qhlC_BS_MA-SIC", "qhl0_BS_MA-SIC",

                 "o2cC_BAdj_BS_MA-BINDNAME1", "o2c0_BAdj_BS_MA-BINDNAME1",
                 "o2cC_BAdj_BS_MA-SIC",  "o2c0_BAdj_BS_MA-SIC",
                 "o2cC_VAdj_BAdj_BS",  "o2c0_VAdj_BAdj_BS",
                 "o2cC_BS_MA-BINDNAME1_BAdj_VAdj",
                 "o2cC_VAdj_BAdj_BS_MA-BINDNAME1",

                 "barraRRC", "barraRR0",

                 "pcaDailyRetC","pcaDailyRet0","pcaDailyRet1","pcaDailyRet2",
                 
                 "baDollarsEff_Y_MA-BINDNAME1", "baDollars_Y_MA-BINDNAME1", "baSize_Y_MA-BINDNAME1", "baSizeSQ_Y_MA-BINDNAME1",
                 "baDollarsEff_S_MA-BINDNAME1", "baDollars_S_MA-BINDNAME1", "baSize_S_MA-BINDNAME1", "baSizeSQ_S_MA-BINDNAME1",
                 "baDollarsEff_Y", "baDollars_Y", "baSize_Y", "baSizeSQ_Y", "SPREAD_Y",
                 "baDollarsEff_S", "baDollars_S", "baSize_S", "baSizeSQ_S", "SPREAD_S",

                 "c2oC_BAdj_BS_MA-BINDNAME1_TAdj-REV", "c2o0_BAdj_BS_MA-BINDNAME1_TAdj-REV",
                 "c2oC_BAdj_BS_MA-SIC", "c2o0_BAdj_BS_MA-SIC",

                 "SIFrac", "SIFrac_Diff", "SIFrac_Diff_D-10.0", "SIFrac_D-10.0",
                 "SIFrac_MA-BINDNAME1_D-10.0", "SIFrac_Diff_MA-BINDNAME1_D-10.0",

                 "BorrowAvailMult", "BorrowReturnFrac", "AdjBorrowRate", "AdjPushedRate",
                 "Buyback_D-5.0", "Buyback_D-10.0",
                 
                 "EPS_Q_CE_Diff_BS_D-5.0", "EPS_Q_CE_Diff_BS_MA-BINDNAME1_D-5.0", "EPS_Q_CE_Diff_BS_MA-SIC_D-5.0",
                 "EPS_Q_CE_Diff_BS_D-10.0", "EPS_Q_CE_Diff_BS_MA-BINDNAME1_D-10.0", "EPS_Q_CE_Diff_BS_MA-SIC_D-10.0",
                 "ratDiffC_BS_D-5.0", "ratDiffC_BS_MA-BINDNAME1_D-5.0", "ratDiffC_BS_MA-SIC_D-5.0",
                 "ratDiffC_BS_D-10.0", "ratDiffC_BS_MA-BINDNAME1_D-10.0", "ratDiffC_BS_MA-SIC_D-10.0",
                 "TARGETPRICE_CE_Diff_BS_D-5.0", "TARGETPRICE_CE_Diff_BS_MA-BINDNAME1_D-5.0", "TARGETPRICE_CE_Diff_BS_MA-SIC_D-5.0",
                 "TARGETPRICE_CE_Diff_BS_D-10.0", "TARGETPRICE_CE_Diff_BS_MA-BINDNAME1_D-10.0", "TARGETPRICE_CE_Diff_BS_MA-SIC_D-10.0",
                 "TARGETPRICE_CE_2P_BS_D-5.0", "TARGETPRICE_CE_2P_BS_MA-BINDNAME1_D-5.0", "TARGETPRICE_CE_2P_BS_MA-SIC_D-5.0",
                 
                 "EPS_Q_DE_Diff_BS_D-5.0", "EPS_Q_DE_Diff_BS_MA-BINDNAME1_D-5.0", "EPS_Q_DE_Diff_BS_MA-SIC_D-5.0",
                 "EPS_Q_DE_Diff_BS_D-10.0", "EPS_Q_DE_Diff_BS_MA-BINDNAME1_D-10.0", "EPS_Q_DE_Diff_BS_MA-SIC_D-10.0",
                 "ratDiffD_BS_D-10.0", "ratDiffD_BS_MA-BINDNAME1_D-10.0", "ratDiffD_BS_MA-SIC_D-10.0",
                 "TARGETPRICE_DE_Diff_BS_D-5.0",
                 "TARGETPRICE_DE_Diff_BS_D-10.0",
                 "TARGETPRICE_DE_Diff_BS_MA-BINDNAME1_D-10.0", "TARGETPRICE_DE_Diff_BS_MA-BINDNAME1_D-5.0",
                 "TARGETPRICE_DE_Diff_BS_MA-SIC_D-10.0", "TARGETPRICE_DE_Diff_BS_MA-SIC_D-5.0",
                 "TARGETPRICE_DE_2P_BS_D-5.0", "TARGETPRICE_DE_2P_BS_MA-BINDNAME1_D-5.0", "TARGETPRICE_DE_2P_BS_MA-SIC_D-5.0",
                 
                 "FRATING_D-10.0",
                 "FEARN_D-10.0",
                 "FHOT_D-3.0",
                 
                 "recentEarnings_T-C_BS_D-5.0",
                 "FLY1_T-C_BS_D-5.0",
                 "nofly2_T-C_BS_FlyAdj",
                 
                 "e2p_BS_MA-BINDNAME1", "e2p_BS_MA-SIC",
                 "s2p_BS_MA-BINDNAME1", "s2p_BS_MA-SIC",
                 "c2a_BS", "c2a_BS_MA-BINDNAME1", "c2a_BS_GA", "c2a_BS_GA_MA-BINDNAME1",
                 "ee2p1_GA", "ee2p1_GA_MA-BINDNAME1", "ee2p1_GA_MA-SIC", "ee2p2_GA", "ee2p2_GA_MA-BINDNAME1", "ee2p2_GA_MA-SIC",

                 "advp"
                 )

dep.attrs <- c("RawRet1", "RawRet2", "RawRet3", "RawRet5", "RawRet10", "RawRet20", "RawRet30",
               "RsdRet1", "RsdRet2", "RsdRet3", "RsdRet5", "RsdRet10", "RsdRet20", "RsdRet30",
               "BarraRsdRet1", "BarraRsdRet2", "BarraRsdRet3", "BarraRsdRet5", "BarraRsdRet10", "BarraRsdRet20", "BarraRsdRet30",
               "C2ORawRet1", "C2ORsdRet1"
               )

dep.intra.attrs <- c("IntraRawRet10", "IntraRawRet20", "IntraRawRet30", "IntraRawRet60", "IntraRawRet120",
                     "C2ORawRet1" )

dep.hourly.attrs <- c("Hourly1RawRet", "Hourly1RsdRet",
                     "Hourly2RawRet", "Hourly2RsdRet",
                     "Hourly3RawRet", "Hourly3RsdRet",
                     "Hourly4RawRet", "Hourly4RsdRet",
                     "Hourly5RawRet", "Hourly5RsdRet",
                     "Hourly6RawRet", "Hourly6RsdRet")

print.indeps <- function() {
   for (v in indep.attrs)
      write(v, file="")
}

print.indeps.intra <- function() {
   for (v in indep.intra.attrs)
      write(v, file="")
}

print.deps <- function() {
   for (v in dep.attrs)
      write(v, file="")
}

print.deps.intra <- function() {
   for (v in dep.intra.attrs)
      write(v, file="")
}

print.deps.hourly <- function() {
   for (v in dep.hourly.attrs)
      write(v, file="")
}

fit.sim <- function(dir, weightedFit = FALSE, trimOutliers = 0, intraday = FALSE, intercept = TRUE, con = "") {
  if (con != "") {
    con <- file(con,"w")
  }
  if (trimOutliers>0) {
    print("Trimming outliers...")
    trimOutliers <- trimOutliers/10000.0/2
  }

  if (intraday) {
    print("Running Intraday Fit")
    indep.attrs <- indep.intra.attrs
    dep.attrs <- dep.intra.attrs
#    dep.atts <- dep.hourly.attrs
    indepsdir <- paste(dir, "/fit/intra.indeps", sep="")
    depsdir <- paste(dir, "/fit/intra.deps", sep="")
  }
  else {
    print("Running Daily Fit")
    indepsdir <- paste(dir, "/fit/indeps", sep="")
    depsdir <- paste(dir, "/fit/deps", sep="")
  }

  independent <- load.indep.variables(indepsdir, list.files(indepsdir, pattern = "gz$", full.names=FALSE))
  dependent <- load.dep.variables(depsdir, list.files(depsdir, pattern = "gz$", full.names=FALSE))
  
  if ( weightedFit ) {
    print("Using weighted fit")
    weights <- independent[['advp']]

    names(weights)[names(weights)=="x"]="weight"
    weights$weight <- weights$weight/1e6
  }

  if ( intercept ) {
     index <- 2
     print("Using intercept")
  }
  else {
     index <- 1
     print("NOT Using intercept")
  }

  if ( trimOutliers >0 )
     print(paste("Trimming",trimOutliers*1000,"bps on each side"))

  write(paste("independent","dependent","type","coeff","stderr","t-value","min residual","max residual","deg. of freedom","adj r^2","f-statistic","p-value",sep="|"),file = con)

  for ( attr in indep.attrs ) {
    print(paste("Fitting ", attr))
    for ( depvar in dep.attrs ) {
      print(paste("On ", depvar))
      
      attr.indep <- independent[[attr]]
      if ( length(attr.indep) > 0 ) {
        attr.dep <- dependent[[depvar]]
        
        if ( length(attr.dep)==0 ) {
          print("ERROR: no dependents found!")
          next
        }

        if (trimOutliers>0 && trimOutliers<0.5) {
          q=quantile(attr.dep$y, c(trimOutliers, 1-trimOutliers))
          attr.dep <- attr.dep[attr.dep$y>q[1] & attr.dep$y<q[2], ]
        }

        if ( weightedFit ) {
           attr.weighted.fit <- weighted.fit.attr(attr.indep, attr.dep, weights, intercept)
           if ( is.null(attr.weighted.fit) ) {
              print("ERROR: null fit")
              next;
           }
           fs <- summary(attr.weighted.fit)
           print(fs)
        }
        else {
           attr.fit <- fit.attr(attr.indep, attr.dep, intercept)
           if ( is.null(attr.fit) ) {
             print("ERROR: null fit")
             next;
           }
           fs <- summary(attr.fit)
           print(fs)
        }
	
        cfs <- coef(fs)

        if (nrow(cfs) < index) {
           print("lm singularity encountered")
           next;
        }

        independentName=attr
        dependentName=depvar
        type=""
        if (weightedFit)
           type=paste(type,"w",sep="")
        if (trimOutliers>0)
           type=paste(type,"t",sep="")
        if (intercept == FALSE)
           type=paste(type,"0",sep="")
        if (type == "")
           type="n"

        coef=cfs[index,1]
        stderr=cfs[index,2]
        tval=cfs[index,3]
        minres=min(fs$residuals)
        maxres=max(fs$residuals)
        r2adj=fs$adj.r.squared
        fstat=fs$fstatistic[1]
        df=fs$df[2]
        pval=cfs[index,4]
 
        write(paste(independentName,dependentName,type,coef,stderr,tval,minres,maxres,df,r2adj,fstat,pval,sep="|"),file=con)
      } #if ( nrow(attr.indep) > 0 )
    }
  }
}
