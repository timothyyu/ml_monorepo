source( "utils.R")

load.daily.prices <- function(securities, start, end) {
  dpwidget <- .jnew("ase/data/widget/SQLDailyPriceWidget")
  pricemap <- dpwidget$getPrices(securities, .jlong(start), .jlong(end))
  arr <- m2a(pricemap)
}

load.detailed.estimates <- function(sec, asof, attr) {
  date <- date2ms(asof)
  J("ase/util/RUtils")$getDetailed(sec, date, attr);
}

plot.stock.returns <- function(stock, start, end) {
  sec <- .jnew("ase/data/Security", as(stock, "integer"));
  ts <- J("ase.util.RUtils")$getStockPrices(sec, .jlong(date2ms(start)), .jlong(date2ms(end)))
  arr1 <- .jcall(ts, "[D", "closeArray")
  arr2 <- .jcall(ts, "[D", "close_tsArray")
  plot(arr2,arr1, type="l")
}
