library("rJava")
.jinit(parameters="-Xmx1024m")

epoch <- ISOdate(1970,1,1)

us2date <- function( v1 ) {
  epoch + v1/100000
}

ms2date <- function( v1 ) {
  format(epoch + v1/1000, "%Y%m%d")
}

date2ms <- function( d ) {
  z <- difftime(strptime(d, "%Y%m%d"), epoch, units="secs")
  as.numeric(z) * 1000
}

date2jlong <- function( d ) {
  .jlong(date2ms(d))
}

addDays <- function( ts, days ) {
  J("ase/util/Time")$addDays( .jlong(ts), as(days, "integer")) 
}

midnight <- function( ts) {
  J("ase/util/Time")$midnight( .jlong(ts) ) 
}

m2a <- function( map ) {
  array(.jevalArray(J("ase/util/CollectionUtils")$mapToArray( map )))
}

secDouble2df <- function(secDoubles) {
  #this is stupidly slow, i think rbind is stupid.  also the 2 dataframes thing is really stupid!!!
  df <- as.data.frame(do.call("rbind", lapply(secDoubles, getSecDouble)))
  names(df) <- c("secid", "val")
  df2 <- data.frame(secid=sapply(df$secid, "[", c(1)), val=sapply(df$val, "[", c(1)))
  df2
}

#this is also stupidly slow... maybe its the overhead of multiple java calls?
secDoubles2DF<-function(secDoubles) {
  n=length(secDoubles)
  df<-data.frame(secid=rep(0,n),value=rep(0,n))
  if (n==0)
    return(df)	
  
  for (i in 1:n) {
    secid=secDoubles[[i]]$first$getSecId()
    value=secDoubles[[i]]$second$doubleValue()
    df$secid[i]=secid
    df$value[i]=value
  }
  return(df)
}

getSecDouble <- function(pair) {
  list(pair$first$getSecId(), pair$second$doubleValue())
}

to.security <- function(secid) {
  sec <- .jnew("ase/data/Security", as(secid, "integer"));
  sec
}

## s2i <- function( str ) {
##   #workaround because i can't seem to pss native ints
##   J("java/lang/Integer")$parseInt(str)
## }

firstMuFilesOfDay <- function() {
  basedir=paste(Sys.getenv('ROOT_DIR'), 'run', Sys.getenv('STRAT'),sep='/')
  mufiles=data.frame(dates=character(0),files=character(0))
  for (datedir in dir(basedir)) {
    if (!file.info(paste(basedir,datedir,sep='/'))$isdir || datedir<'20110401')
      next;

    x=dir(paste(basedir,datedir,'mus',sep='/'),pattern='mus\\.[0-9]{8}_[0-9]{4}\\.txt')
    x=x[order(x)]
    if (length(x)>0)
      mufiles=rbind(mufiles,data.frame(dates=datedir,files=paste(basedir,datedir,'mus',x[1],sep='/')))
  }
 mufiles
}

simMuFiles <- function(simdir) {
  basedir=paste(simdir, 'mus',sep='/')
  mufiles=data.frame(dates=character(0),files=character(0))
  fs=dir(basedir,pattern='mus\\.[0-9]{8}_[0-9]{4}\\.txt')
  fs=fs[order(fs)]
  for ( file in fs ) {
      d = strsplit(file, "\\.")[[1]][2]
      mufiles = rbind(mufiles,data.frame(dates=d,files=paste(basedir,file,sep="/")))
  }
  mufiles
}

threeDayMuFiles <- function() {
  basedir=paste(Sys.getenv('ROOT_DIR'), 'run', Sys.getenv('STRAT'),sep='/')
  mufiles=data.frame(dates=character(0),files=character(0))
  datedirs=dir(basedir,pattern="^[0-9]{8}$")
  datedirs=datedirs[order(datedirs)]

  dirsFound <- 0
  usedatedirs <- c()
  for (datedir in datedirs[order(datedirs, decreasing=TRUE)]) {
     if (file.exists(paste(basedir,datedir,"mus", sep="/"))) {
        dirsFound <- dirsFound +1
        usedatedirs = cbind(datedir, usedatedirs)
     }
     if (dirsFound == 5)
        break
  }

  for (datedir in usedatedirs) {
    x=dir(paste(basedir,datedir,'mus',sep='/'),pattern='mus\\.[0-9]{8}_[0-9]{4}\\.txt')
    x=x[order(x)]

    for (m in x) {
      d = strsplit(m, "\\.")[[1]][2]
      mufiles=rbind(mufiles,data.frame(dates=d,files=paste(basedir,datedir,'mus',m,sep='/')))
    }
  }
 mufiles
}

plotfiles <- function(basedir, pngfile, max) {
  files=dir(basedir,pattern='simplot\\.*\\.*',full.names=TRUE)
  png(pngfile, width=1300, height=1000)
  plotcolors <- c("blue", "green", "black", "red", "orange", "yellow", "purple", "cyan", "pink")
  ii <- 1
  for ( file in files ) {
    print(paste("Reading ", file, " ", plotcolors[ii]))
    d <- read.table(file, sep="|")
    if (ii == 1) {
      plot(d$V2, type="l", ylim=c(-10000,max), col=plotcolors[ii])
    }
    else {
      lines(d$V2, type="l", col=plotcolors[ii])           
    }
    ii <- ii + 1
  }
  legend("topleft", legend=files, col=plotcolors)
}
