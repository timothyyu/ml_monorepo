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
  if ( length(merged$val.x)>0 && length(merged$val.y)>0 ) {
     if ( intercept )
        fit <- lm( merged$val.x ~ merged$val.y )
     else
        fit <- lm( merged$val.x ~ 0 + merged$val.y)
  }
  else
     fit <- NULL
}

weighted.fit.attr <- function(indeps, deps, weights, intercept = TRUE) {
  merged1 <- merge(indeps, weights, by.x = c("secid", "born"), by.y = c("secid", "born"))
  merged2 <- merge(merged1, deps, by.x = c("secid", "born"), by.y = c("secid", "born"))
  if ( length(merged2$val.x) >0 ) {
      if ( intercept )
         fit <- lm( merged2$val.x ~ merged2$val.y, weights=merged2$weight )
      else
         fit <- lm( merged2$val.x ~ 0 + merged2$val.y, weights=merged2$weight )
  }
  else
      fit <- NULL
}

aggregate.calcres.files.trimmed <- function(files,attrs) {
  result <- NULL    
  for (file in files) {
    print(paste("Loading file: ", file))
    calcres <- load.calcres(file)
    calcres <- calcres[calcres$attr %in% attrs, ]
    result <- rbind(result, calcres)
  }
  result
}

aggregate.calcres.files <- function(files) {
  result <- NULL    
  for (file in files) {
    print(paste("Loading file: ", file))
    calcres <- load.calcres(file)
    result <- rbind(result, calcres)
  }
  result
}

load.variables <- function(dir, files) {
  variables=list()
  for ( file in files ) {
     name=strsplit(file,"\\.")[[1]][1]
     print(name)
     variables[[name]] <- read.table(gzfile(paste(dir,file,sep="/")), sep="|", col.names=c("secid", "val", "born"), fill=TRUE, nrows=500000, colClasses = c("integer", "numeric", "character"))
  }
  variables
}

indep.attrs <- c("hlC_B_MA-BINDNAME1", "hl0_B_MA-BINDNAME1",
                 "hlC_B_MA-SIC", "hl0_B_MA-SIC",
                 "hlC_BS_MA-BINDNAME1", "hl0_BS_MA-BINDNAME1",
                 "hlC_BS_MA-SIC", "hl0_BS_MA-SIC",
                 "o2cC_BAdj_B_MA-BINDNAME1", "o2c0_BAdj_B_MA-BINDNAME1",
                 "o2cC_BAdj_B_MA-SIC",  "o2c0_BAdj_B_MA-SIC",
                 "o2cC_VAdj_BAdj_B",  "o2c0_VAdj_BAdj_B",
                 "o2cC_BAdj_BS_MA-BINDNAME1", "o2c0_BAdj_BS_MA-BINDNAME1",
                 "o2cC_BAdj_BS_MA-SIC",  "o2c0_BAdj_BS_MA-SIC",
                 "o2cC_VAdj_BAdj_B",  "o2c0_VAdj_BAdj_B",
           "EPS_Q_CE_Diff_B_D-5.0", "EPS_Q_CE_Diff_B_MA-BINDNAME1_D-5.0",
           "EPS_Q_CE_Diff_B_D-10.0", "EPS_Q_CE_Diff_B_MA-BINDNAME1_D-10.0",
           "EPS_Q_CE_Diff_BS_D-5.0", "EPS_Q_CE_Diff_BS_MA-BINDNAME1_D-5.0",
           "EPS_Q_CE_Diff_BS_D-10.0", "EPS_Q_CE_Diff_BS_MA-BINDNAME1_D-10.0",
           "ratDiffC_B_D-5.0", "ratDiffC_B_MA-BINDNAME1_D-5.0",
           "ratDiffC_B_D-10.0", "ratDiffC_B_MA-BINDNAME1_D-10.0",
           "ratDiffC_BS_D-5.0", "ratDiffC_BS_MA-BINDNAME1_D-5.0",
           "ratDiffC_BS_D-10.0", "ratDiffC_BS_MA-BINDNAME1_D-10.0",
           "TARGETPRICE_CE_Diff_B_D-5.0", "TARGETPRICE_CE_Diff_B_MA-BINDNAME1_D-5.0",
           "TARGETPRICE_CE_Diff_B_D-10.0","TARGETPRICE_CE_Diff_B_MA-BINDNAME1_D-10.0",
           "TARGETPRICE_CE_Diff_BS_D-5.0", "TARGETPRICE_CE_Diff_BS_MA-BINDNAME1_D-5.0",
           "TARGETPRICE_CE_Diff_BS_D-10.0","TARGETPRICE_CE_Diff_BS_MA-BINDNAME1_D-10.0",
           "TARGETPRICE_CE_2P_B_D-5.0", "TARGETPRICE_CE_2P_B_MA-BINDNAME1_D-5.0",
           "TARGETPRICE_CE_2P_BS_D-5.0", "TARGETPRICE_CE_2P_BS_MA-BINDNAME1_D-5.0",
           "EPS_Q_DE_Diff_B_D-5.0", "EPS_Q_DE_Diff_B_MA-BINDNAME1_D-5.0",
           "EPS_Q_DE_Diff_B_D-10.0", "EPS_Q_DE_Diff_B_MA-BINDNAME1_D-10.0",
           "EPS_Q_DE_Diff_BS_D-5.0", "EPS_Q_DE_Diff_BS_MA-BINDNAME1_D-5.0",
           "EPS_Q_DE_Diff_BS_D-10.0", "EPS_Q_DE_Diff_BS_MA-BINDNAME1_D-10.0",
           "ratDiffD_B_D-10.0", "ratDiffD_B_MA-BINDNAME1_D-10.0",
           "ratDiffD_BS_D-10.0", "ratDiffD_BS_MA-BINDNAME1_D-10.0",
           "TARGETPRICE_DE_Diff_B_D-5.0",
           "TARGETPRICE_DE_Diff_B_D-10.0",
           "TARGETPRICE_DE_Diff_BS_D-5.0",
           "TARGETPRICE_DE_Diff_BS_D-10.0",
           "TARGETPRICE_DE_2P_B_D-5.0", "TARGETPRICE_DE_2P_B_MA-BINDNAME1_D-5.0",
           "TARGETPRICE_DE_2P_BS_D-5.0", "TARGETPRICE_DE_2P_BS_MA-BINDNAME1_D-5.0",
           "FRATING_D-10.0",
           "FEARN_D-10.0",
           "FHOT_D-3.0",
           "recentEarnings_T-C_B_D-5.0",
           "recentEarnings_T-C_BS_D-5.0",
           "FLY1_T-C_B_D-5.0",
           "FLY1_T-C_BS_D-5.0",
           "nofly2_T-C_B_FlyAdj",
           "nofly2_T-C_BS_FlyAdj",
           "e2p_B_MA-BINDNAME1", "e2p_B_MA-SIC", "e2p_GA",
           "e2p_BS_MA-BINDNAME1", "e2p_BS_MA-SIC",
           "s2p_B_MA-BINDNAME1", "s2p_B_MA-SIC",
           "s2p_BS_MA-BINDNAME1", "s2p_BS_MA-SIC",
           "c2a_B",
           "c2a_BS",
           "ee2p1_GA", "ee2p1_GA_MA-BINDNAME1", "ee2p1_GA_MA-SIC", "ee2p2_GA", "ee2p2_GA_MA-BINDNAME1", "ee2p2_GA_MA-SIC",
           "BorrowAvailMult", "BorrowReturnFrac", "AdjBorrowRate", "AdjPushedRate",
           "Buyback_D-5.0", "Buyback_D-10.0",
           "c2oC", "c2oC_BAdj", "c2oC_BAdj_B_MA-BINDNAME1", "c2oC_BAdj_B_MA-SIC",
           "c2oC_BAdj_BS_MA-BINDNAME1", "c2oC_BAdj_BS_MA-SIC",
           "SIFrac", "SIFrac_Diff", "SIFrac_Diff_D-10.0", "SIFrac_D-10.0",
           "qhlC_B_MA-BINDNAME1", "qhl0_B_MA-BINDNAME1",
           "qhlC_B_MA-SIC", "qhl0_B_MA-SIC",
           "qhlC_BS_MA-BINDNAME1", "qhl0_BS_MA-BINDNAME1",
           "qhlC_BS_MA-SIC", "qhl0_BS_MA-SIC",
           "barraRRC", 
           "FULL1", "FULL2", "FULL3", "FULL5", "FULL10", "FULL20", "FULL30",
           "advp"
           )

dep.attrs <- c("RawRet1", "RawRet2", "RawRet3", "RawRet5", "RawRet10", "RawRet20", "RawRet30",
               "RsdRet1", "RsdRet2", "RsdRet3", "RsdRet5", "RsdRet10", "RsdRet20", "RsdRet30",
               "BarraRsdRet1", "BarraRsdRet2", "BarraRsdRet3", "BarraRsdRet5", "BarraRsdRet10", "BarraRsdRet20", "BarraRsdRet30"
               )

print.indeps <- function() {
   for (v in indep.attrs)
      write(v, file="")
}

print.deps <- function() {
   for (v in dep.attrs)
      write(v, file="")
}


fit.sim2 <- function(dir, weightedFit = FALSE, trimOutliers = 0, intercept = TRUE, con = "") {
  if (con != "") 
     con <- file(con,"w") 
  trimOutliers <- trimOutliers/10000.0/2
  indepsdir <- paste(dir, "/fit/indeps", sep="")
  depsdir <- paste(dir, "/fit/deps", sep="")

  independent <- load.variables(indepsdir, list.files(indepsdir, pattern = "gz$", full.names=FALSE))
  dependent <- load.variables(depsdir, list.files(depsdir, pattern = "gz$", full.names=FALSE))
  
  if ( weightedFit ) {
    print("Using weighted fit")
    weights <- independent[['advp']]
    names(weights)[names(weights)=="val"]="weight"
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

  write(paste("independent","dependent","type","coeff","10^coeff","stderr","t-value","min residual","max residual","deg. of freedom","adj r^2","f-statistic","p-value",sep="|"),file = con)

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
          q=quantile(attr.dep$val, c(trimOutliers, 1-trimOutliers))
          attr.dep <- attr.dep[attr.dep$val>q[1] & attr.dep$val<q[2], ]
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
        coef2=10^coef
 
        write(paste(independentName,dependentName,type,coef,coef2,stderr,tval,minres,maxres,df,r2adj,fstat,pval,sep="|"),file=con)
      }
      #else {
        #print("No attrs found.  Skipping...") 
      #}
    }
  }
}


fit.sim <- function(dir, weightedFit = FALSE, trimOutliers = 0, intercept = TRUE, con = "") {
  if (con != "") 
     con <- file(con,"w") 
  trimOutliers <- trimOutliers/10000.0/2
  calcresdir <- paste(dir, "/calcres", sep="")
  fitdir <- paste(dir, "/fit", sep="")

  independent <- aggregate.calcres.files.trimmed( list.files(calcresdir, pattern = "^calcres", full.names=TRUE) , c(indep.attrs, "advp"))
  #now get and indeps from the fitres files
  independent <- rbind(independent, aggregate.calcres.files.trimmed( list.files(fitdir, patter = "^fitres", full.names=TRUE), indep.attrs))  
  dependent <- aggregate.calcres.files.trimmed( list.files(fitdir, pattern = "^fitres", full.names=TRUE), dep.attrs )
  
  if ( weightedFit ) {
    print("Using weighted fit")
    weights <- independent[independent$attr == 'advp', ]
    weights <- data.frame(secid=weights$secid,born=weights$born,weight=weights$val)
    weights$weight <- as.numeric(as.character(weights$weight))/1e6
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

  write(paste("independent","dependent","type","coeff","10^coeff","stderr","t-value","min residual","max residual","deg. of freedom","adj r^2","f-statistic","p-value",sep="|"),file = con)

  for ( attr in indep.attrs ) {
    print(paste("Fitting ", attr))
    for ( depvar in dep.attrs ) {
      print(paste("On ", depvar))
      
      attr.indep <- independent[independent$attr == attr, ]
      if ( length(attr.indep) > 0 ) {
        attr.indep$val <- as.numeric(as.character(attr.indep$val))
        attr.dep <- dependent[dependent$attr == depvar, ]
        
        if ( length(attr.dep)==0 ) {
          print("ERROR: no dependents found!")
          next
        }

        if (trimOutliers>0 && trimOutliers<0.5) {
          q=quantile(attr.dep$val, c(trimOutliers, 1-trimOutliers))
          attr.dep <- attr.dep[attr.dep$val>q[1] & attr.dep$val<q[2], ]
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
        coef2=10^coef
 
        write(paste(independentName,dependentName,type,coef,coef2,stderr,tval,minres,maxres,df,r2adj,fstat,pval,sep="|"),file=con)
      }
      #else {
        #print("No attrs found.  Skipping...") 
      #}
    }
  }
}

