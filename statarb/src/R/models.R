library("qcc")
source( "utils.R")

load.mus <- function(filename) {
  mus <- read.table(filename,sep='|',col.names=c('secid','fc','val'))
  mus$fc <- factor(mus$fc)
  mus$val <- as.numeric(as.character(mus$val))
  mus
}

load.calcres.old <- function(filename) {
  calcres <- read.table(gzfile(filename), sep="|", col.names=c("timestamp", "coid", "issue", "attr", "date", "val"))
  calcres <- calcres[calcres$coid != 0, ]
  calcres$attr <- factor(calcres$attr)
  calcres
}

load.calcres <- function(filename) {
  calcres <- read.table(gzfile(filename), sep="|", col.names=c("secid", "attr", "datatype", "date", "val", "curr", "born"), fill=TRUE)
  calcres <- calcres[calcres$secid != "FCOV", ]
  calcres$attr <- factor(calcres$attr)
  calcres 
}

calcres.stats<-function(calcres){
  v=as.numeric(as.character(calcres$val))
  l=tapply(v,calcres$attr,length)
  m=tapply(v,calcres$attr,mean)
  s=tapply(v,calcres$attr,var)
  cmin=tapply(v,calcres$attr,min)
  cmax=tapply(v,calcres$attr,max)
  calcstats<-data.frame(names=attr(l,"dimnames"),size=l,mean=m,std=sqrt(s),min=cmin,max=cmax)
  calcstats
}

load.data.prices.dates <- function(securites, start, end) {
  load.daily.prices(securities, date2ms(start), date2ms(end))
}

extract.calcres.item <- function(calcres, item) {
  calcres[calcres$attr == item, ]
}

daily.item.check <- function(item) {
  m <- mean(item$val)
  s <- sd(item$val)
  name <- item$attr[1]
  print(paste("Examining model ", name))
  
  res <- item[item$val > m+5*s | item$val < m-5*s, c(2,3,4,6)]
  print(res)

  hist(item$val, main=name)
}

calcres.timeseries <- function() {
  files <- system("$BIN_DIR/get_calcres_files.py --rootdir '/apps/multex/trade/run/live-prod' --startdate 20100920", intern=TRUE)
  model.ts <- NULL
  for ( file in files ) {
    print(file)
    calcres <- load.calcres.old(file)
    model.ts <- daily.items.check(calcres, model.ts)
  }
}

daily.items.check <- function(calcres, model.ts) {
  itemnames = c("CepsqDifB-Dk5.0_3")
  for ( name in itemnames ) {
    item <- extract.calcres.item(calcres, name)
    daily.item.check(item)

    model.ts <- rbind(model.ts, item)
  }
  model.ts
}

load.forecasts <- function(configfile, calcresfile) {
  calcres <- J("ase/data/CalcResults")$restore( .jnew(J("java/io/File"),calcresfile) )
  forecastDefs <- J("ase/calculator/Forecast")$loadDefs( configfile )
  forecastDefs <- new(J("java/util/Vector"),forecastDefs)
  
  forecastList=list()
  horizon <- 5.0
  for (i in 0:(forecastDefs$size()-1)) {
    f<-forecastDefs$get(i)
    forecasts<-f$calculate(calcres,horizon) #map of secid to double
    forecasts<-m2a(forecasts) #R list of java Pair<Security,Double>
    df=secDoubles2DF(forecasts) #Data frame of secid,value
    
    forecastList[[as.character(f$name)]]=df;
  }
  return(forecastList)
}

forecast.stats<-function(forecasts) {
  n=length(forecasts)
  name=rep("",n)
  size=rep(0,n)
  mean=rep(0,n)
  std=rep(0,n)
  min=rep(0,n)
  max=rep(0,n)
  
  for (i in 1:n) {
    df=forecasts[[i]]
    fname=attr(forecasts,"names")[i]
    if (length(df$value)>0) {
      name[i]=as.character(fname)
      mean[i]=mean(df$value)
      std[i]=sqrt(var(df$value))
      size[i]=length(df$value)
      min[i]=min(df$value)
      max[i]=max(df$value)
    }
    else {
      name[i]=as.character(fname)
      mean[i]=NA
      std[i]=NA
      size[i]=0
      min[i]=NA
      max[i]=NA
    }
  }	
  stats<-data.frame(name=name,size=size,mean=mean,std=std,min=min,max=max)
}

testme2 <- function() {
  configfile <- "/apps/ase/config/opt.prod.cfg"
  calcresfile <- "/apps/ase/research/useq-live/dailysim/20110218/calcres/calcres.20110217_1450.txt.gz"
  forecasts1 <- load.forecasts(configfile, calcresfile)
  print("check")
  forecast.stats(forecasts1)
}

## testme <- function() {
##   model.ts$datep <- factor(sapply(model.ts$timestamp, ms2date))
##   grps <- qcc.groups(model.ts$val, model.ts$datep)
  
##   pdf("test1.pdf")
##   qcc(grps, type="xbar")
##   qcc(grps, type="S")
##   dev.off()
##   model.ts
## }

qccReport <- function(mode=0, simdir="") {
  if (mode == 0) {
     pdf(paste(Sys.getenv('REPORT_DIR'),'qcc','qcc.pdf',sep='/'))
     mufiles <- firstMuFilesOfDay()
  }
  else if (mode == 1) {
     pdf(paste(Sys.getenv('REPORT_DIR'),'qcc','intra_qcc.pdf',sep='/'))
     mufiles <- threeDayMuFiles()
  }
  else if (mode ==2) {
     pdf(paste(simdir,'qcc.pdf',sep='/'))
     mufiles <- simMuFiles(simdir)
  }

  maxdate="0"
  fcvalues <- list()
  for (i in 1:nrow(mufiles)) {
    date <- as.character(mufiles$dates[i])
    file <- as.character(mufiles$files[i])
    mus <- load.mus(file)
    fc2values=tapply(mus$val,mus$fc,identity)

    if (date>maxdate)
       maxdate<-date

    for (name in names(fc2values)) {
      if (is.null(fcvalues[[name]])) {
        fcvalues[[name]]=list()
      }

      fcvalues[[name]][[date]]=fc2values[[name]]
    }
  }

  for (forecastname in names(fcvalues)) {
    cols=max(as.numeric(lapply(fcvalues[[forecastname]],length)))+1
    rows=length(fcvalues[[forecastname]])
    mm=matrix(NA,rows,cols)
    
    for (i in 1:length(fcvalues[[forecastname]])) {
      fcvalues[[forecastname]][[i]][cols]=0
      mm[i,]=fcvalues[[forecastname]][[i]]
    }
    
    qcc(mm,labels=names(fcvalues[[forecastname]]),type='xbar',title=paste('Mean of',forecastname,'as of ',maxdate))
    qcc(mm,labels=names(fcvalues[[forecastname]]),type='S',title=paste('SD of',forecastname,'as of',maxdate))
  }

  dev.off()
}
