# Rattle is Copyright (c) 2006-2014 Togaware Pty Ltd.

#============================================================
# Rattle timestamp: 2015-10-17 14:52:53 x86_64-apple-darwin13.4.0 

# Rattle version 3.4.3 user 'jianboxue'

# Export this log textview to a file using the Export button or the Tools 
# menu to save a log of all activity. This facilitates repeatability. Exporting 
# to file 'myrf01.R', for example, allows us to the type in the R Console 
# the command source('myrf01.R') to repeat the process automatically. 
# Generally, we may want to edit the file to suit our needs. We can also directly 
# edit this current log textview to record additional information before exporting. 

# Saving and loading projects also retains this log.

library(rattle)

# This log generally records the process of building a model. However, with very 
# little effort the log can be used to score a new dataset. The logical variable 
# 'building' is used to toggle between generating transformations, as when building 
# a model, and simply using the transformations, as when scoring a dataset.

building <- TRUE
scoring  <- ! building

# The colorspace package is used to generate the colours used in plots, if available.

library(colorspace)

# A pre-defined value is used to reset the random seed so that results are repeatable.

crv$seed <- 42 

#============================================================
# Rattle timestamp: 2015-10-17 14:53:01 x86_64-apple-darwin13.4.0 

# Load an R data frame.

crs$dataset <- data

# Display a simple summary (structure) of the dataset.

str(crs$dataset)

#============================================================
# Rattle timestamp: 2015-10-17 14:53:02 x86_64-apple-darwin13.4.0 

# Note the user selections. 

# Build the training/validate/test datasets.

set.seed(crv$seed) 
crs$nobs <- nrow(crs$dataset) # 5000 observations 
crs$sample <- crs$train <- sample(nrow(crs$dataset), 0.7*crs$nobs) # 3500 observations
crs$validate <- sample(setdiff(seq_len(nrow(crs$dataset)), crs$train), 0.15*crs$nobs) # 750 observations
crs$test <- setdiff(setdiff(seq_len(nrow(crs$dataset)), crs$train), crs$validate) # 750 observations

# The following variable selections have been noted.

crs$input <- c("shanghai.1", "shanghai.SMA.3", "shanghai.SMA.5", "shanghai.SMA.10",
               "shanghai.2", "shanghai.EMA.2", "shanghai.SMA.20", "shanghai.SMA.20.1",
               "shanghai.SMA.20.2", "shanghai.SMA.20.3", "shanghai.SMA.20.4", "shanghai.SMA.20.5",
               "shanghai.EMA.14", "macd", "signal")

crs$numeric <- c("shanghai.1", "shanghai.SMA.3", "shanghai.SMA.5", "shanghai.SMA.10",
                 "shanghai.2", "shanghai.EMA.2", "shanghai.SMA.20", "shanghai.SMA.20.1",
                 "shanghai.SMA.20.2", "shanghai.SMA.20.3", "shanghai.SMA.20.4", "shanghai.SMA.20.5",
                 "shanghai.EMA.14", "macd", "signal")

crs$categoric <- NULL

crs$target  <- "shanghai"
crs$risk    <- NULL
crs$ident   <- NULL
crs$ignore  <- NULL
crs$weights <- NULL

#============================================================
# Rattle timestamp: 2015-10-17 14:53:07 x86_64-apple-darwin13.4.0 

# Decision Tree 

# The 'rpart' package provides the 'rpart' function.

library(rpart, quietly=TRUE)

# Reset the random number seed to obtain the same results each time.

set.seed(crv$seed)

# Build the Decision Tree model.

crs$rpart <- rpart(shanghai ~ .,
                   data=crs$dataset[crs$train, c(crs$input, crs$target)],
                   method="class",
                   parms=list(split="information"),
                   control=rpart.control(usesurrogate=0, 
                                         maxsurrogate=0))

# Generate a textual view of the Decision Tree model.

print(crs$rpart)
printcp(crs$rpart)
cat("\n")

# Time taken: 0.60 secs

#============================================================
# Rattle timestamp: 2015-10-17 14:53:08 x86_64-apple-darwin13.4.0 

# Ada Boost 

# The `ada' package implements the boost algorithm.

library(ada, quietly=TRUE)

# Build the Ada Boost model.

set.seed(crv$seed)
crs$ada <- ada(shanghai ~ .,
               data=crs$dataset[crs$train,c(crs$input, crs$target)],
               control=rpart.control(maxdepth=30,
                                     cp=0.010000,
                                     minsplit=20,
                                     xval=10),
               iter=50)

# Print the results of the modelling.

print(crs$ada)
round(crs$ada$model$errs[crs$ada$iter,], 2)
cat('Variables actually used in tree construction:\n')
print(sort(names(listAdaVarsUsed(crs$ada))))
cat('\nFrequency of variables actually used:\n')
print(listAdaVarsUsed(crs$ada))

# Time taken: 8.74 secs

#============================================================
# Rattle timestamp: 2015-10-17 14:53:17 x86_64-apple-darwin13.4.0 

# Random Forest 

# The 'randomForest' package provides the 'randomForest' function.

library(randomForest, quietly=TRUE)

# Build the Random Forest model.

set.seed(crv$seed)
crs$rf <- randomForest(shanghai ~ .,
                       data=crs$dataset[crs$sample,c(crs$input, crs$target)], 
                       ntree=500,
                       mtry=3,
                       importance=TRUE,
                       na.action=na.roughfix,
                       replace=FALSE)

# Generate textual output of 'Random Forest' model.

crs$rf

# The `pROC' package implements various AUC functions.

library(pROC, quietly=TRUE)

# Calculate the Area Under the Curve (AUC).

roc(crs$rf$y, as.numeric(crs$rf$predicted))

# Calculate the AUC Confidence Interval.

ci.auc(crs$rf$y, as.numeric(crs$rf$predicted))

# List the importance of the variables.

rn <- round(importance(crs$rf), 2)
rn[order(rn[,3], decreasing=TRUE),]

# Time taken: 9.28 secs

#============================================================
# Rattle timestamp: 2015-10-17 14:53:26 x86_64-apple-darwin13.4.0 

# Support vector machine. 

# The 'kernlab' package provides the 'ksvm' function.

library(kernlab, quietly=TRUE)

# Build a Support Vector Machine model.

set.seed(crv$seed)
crs$ksvm <- ksvm(as.factor(shanghai) ~ .,
                 data=crs$dataset[crs$train,c(crs$input, crs$target)],
                 kernel="rbfdot",
                 prob.model=TRUE)

# Generate a textual view of the SVM model.

crs$ksvm

# Time taken: 2.48 secs

#============================================================
# Rattle timestamp: 2015-10-17 14:53:29 x86_64-apple-darwin13.4.0 

# Regression model 

# Build a Regression model.

crs$glm <- glm(shanghai ~ .,
               data=crs$dataset[crs$train, c(crs$input, crs$target)],
               family=binomial(link="logit"))

# Generate a textual view of the Linear model.

print(summary(crs$glm))
cat(sprintf("Log likelihood: %.3f (%d df)\n",
            logLik(crs$glm)[1],
            attr(logLik(crs$glm), "df")))
cat(sprintf("Null/Residual deviance difference: %.3f (%d df)\n",
            crs$glm$null.deviance-crs$glm$deviance,
            crs$glm$df.null-crs$glm$df.residual))
cat(sprintf("Chi-square p-value: %.8f\n",
            dchisq(crs$glm$null.deviance-crs$glm$deviance,
                   crs$glm$df.null-crs$glm$df.residual)))
cat(sprintf("Pseudo R-Square (optimistic): %.8f\n",
            cor(crs$glm$y, crs$glm$fitted.values)))
cat('\n==== ANOVA ====\n\n')
print(anova(crs$glm, test="Chisq"))
cat("\n")

# Time taken: 0.27 secs

#============================================================
# Rattle timestamp: 2015-10-17 14:53:29 x86_64-apple-darwin13.4.0 

# Neural Network 

# Build a neural network model using the nnet package.

library(nnet, quietly=TRUE)

# Build the NNet model.

set.seed(199)
crs$nnet <- nnet(as.factor(shanghai) ~ .,
                 data=crs$dataset[crs$sample,c(crs$input, crs$target)],
                 size=10, skip=TRUE, MaxNWts=10000, trace=FALSE, maxit=100)

# Print the results of the modelling.

cat(sprintf("A %s network with %d weights.\n",
            paste(crs$nnet$n, collapse="-"),
            length(crs$nnet$wts)))
cat(sprintf("Inputs: %s.\n",
            paste(crs$nnet$coefnames, collapse=", ")))
cat(sprintf("Output: %s.\n",
            names(attr(crs$nnet$terms, "dataClasses"))[1]))
cat(sprintf("Sum of Squares Residuals: %.4f.\n",
            sum(residuals(crs$nnet) ^ 2)))
cat("\n")
print(summary(crs$nnet))
cat('\n')

# Time taken: 0.09 secs

#============================================================
# Rattle timestamp: 2015-10-17 14:53:33 x86_64-apple-darwin13.4.0 

# Evaluate model performance. 

# Generate an Error Matrix for the Decision Tree model.

# Obtain the response from the Decision Tree model.

crs$pr <- predict(crs$rpart, newdata=crs$dataset[crs$validate, c(crs$input, crs$target)], type="class")

# Generate the confusion matrix showing counts.

table(crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai, crs$pr,
      dnn=c("Actual", "Predicted"))

# Generate the confusion matrix showing proportions.

pcme <- function(actual, cl)
{
  x <- table(actual, cl)
  tbl <- cbind(round(x/length(actual), 2),
               Error=round(c(x[1,2]/sum(x[1,]),
                             x[2,1]/sum(x[2,])), 2))
  names(attr(tbl, "dimnames")) <- c("Actual", "Predicted")
  return(tbl)
};
pcme(crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai, crs$pr)

# Calculate the overall error percentage.

overall <- function(x)
{
  if (nrow(x) == 2) 
    cat((x[1,2] + x[2,1]) / sum(x)) 
  else
    cat(1 - (x[1,rownames(x)]) / sum(x))
} 
overall(table(crs$pr, crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai,  
              dnn=c("Predicted", "Actual")))

# Calculate the averaged class error percentage.

avgerr <- function(x) 
  cat(mean(c(x[1,2], x[2,1]) / apply(x, 1, sum))) 
avgerr(table(crs$pr, crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai,  
             dnn=c("Predicted", "Actual")))

# Generate an Error Matrix for the Ada Boost model.

# Obtain the response from the Ada Boost model.

crs$pr <- predict(crs$ada, newdata=crs$dataset[crs$validate, c(crs$input, crs$target)])

# Generate the confusion matrix showing counts.

table(crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai, crs$pr,
      dnn=c("Actual", "Predicted"))

# Generate the confusion matrix showing proportions.

pcme <- function(actual, cl)
{
  x <- table(actual, cl)
  tbl <- cbind(round(x/length(actual), 2),
               Error=round(c(x[1,2]/sum(x[1,]),
                             x[2,1]/sum(x[2,])), 2))
  names(attr(tbl, "dimnames")) <- c("Actual", "Predicted")
  return(tbl)
};
pcme(crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai, crs$pr)

# Calculate the overall error percentage.

overall <- function(x)
{
  if (nrow(x) == 2) 
    cat((x[1,2] + x[2,1]) / sum(x)) 
  else
    cat(1 - (x[1,rownames(x)]) / sum(x))
} 
overall(table(crs$pr, crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai,  
              dnn=c("Predicted", "Actual")))

# Calculate the averaged class error percentage.

avgerr <- function(x) 
  cat(mean(c(x[1,2], x[2,1]) / apply(x, 1, sum))) 
avgerr(table(crs$pr, crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai,  
             dnn=c("Predicted", "Actual")))

# Generate an Error Matrix for the Random Forest model.

# Obtain the response from the Random Forest model.

crs$pr <- predict(crs$rf, newdata=na.omit(crs$dataset[crs$validate, c(crs$input, crs$target)]))

# Generate the confusion matrix showing counts.

table(na.omit(crs$dataset[crs$validate, c(crs$input, crs$target)])$shanghai, crs$pr,
      dnn=c("Actual", "Predicted"))

# Generate the confusion matrix showing proportions.

pcme <- function(actual, cl)
{
  x <- table(actual, cl)
  tbl <- cbind(round(x/length(actual), 2),
               Error=round(c(x[1,2]/sum(x[1,]),
                             x[2,1]/sum(x[2,])), 2))
  names(attr(tbl, "dimnames")) <- c("Actual", "Predicted")
  return(tbl)
};
pcme(na.omit(crs$dataset[crs$validate, c(crs$input, crs$target)])$shanghai, crs$pr)

# Calculate the overall error percentage.

overall <- function(x)
{
  if (nrow(x) == 2) 
    cat((x[1,2] + x[2,1]) / sum(x)) 
  else
    cat(1 - (x[1,rownames(x)]) / sum(x))
} 
overall(table(crs$pr, na.omit(crs$dataset[crs$validate, c(crs$input, crs$target)])$shanghai,  
              dnn=c("Predicted", "Actual")))

# Calculate the averaged class error percentage.

avgerr <- function(x) 
  cat(mean(c(x[1,2], x[2,1]) / apply(x, 1, sum))) 
avgerr(table(crs$pr, na.omit(crs$dataset[crs$validate, c(crs$input, crs$target)])$shanghai,  
             dnn=c("Predicted", "Actual")))

# Generate an Error Matrix for the SVM model.

# Obtain the response from the SVM model.

crs$pr <- predict(crs$ksvm, newdata=na.omit(crs$dataset[crs$validate, c(crs$input, crs$target)]))

# Generate the confusion matrix showing counts.

table(na.omit(crs$dataset[crs$validate, c(crs$input, crs$target)])$shanghai, crs$pr,
      dnn=c("Actual", "Predicted"))

# Generate the confusion matrix showing proportions.

pcme <- function(actual, cl)
{
  x <- table(actual, cl)
  tbl <- cbind(round(x/length(actual), 2),
               Error=round(c(x[1,2]/sum(x[1,]),
                             x[2,1]/sum(x[2,])), 2))
  names(attr(tbl, "dimnames")) <- c("Actual", "Predicted")
  return(tbl)
};
pcme(na.omit(crs$dataset[crs$validate, c(crs$input, crs$target)])$shanghai, crs$pr)

# Calculate the overall error percentage.

overall <- function(x)
{
  if (nrow(x) == 2) 
    cat((x[1,2] + x[2,1]) / sum(x)) 
  else
    cat(1 - (x[1,rownames(x)]) / sum(x))
} 
overall(table(crs$pr, na.omit(crs$dataset[crs$validate, c(crs$input, crs$target)])$shanghai,  
              dnn=c("Predicted", "Actual")))

# Calculate the averaged class error percentage.

avgerr <- function(x) 
  cat(mean(c(x[1,2], x[2,1]) / apply(x, 1, sum))) 
avgerr(table(crs$pr, na.omit(crs$dataset[crs$validate, c(crs$input, crs$target)])$shanghai,  
             dnn=c("Predicted", "Actual")))

# Generate an Error Matrix for the Linear model.

# Obtain the response from the Linear model.

crs$pr <- as.vector(ifelse(predict(crs$glm, type="response", newdata=crs$dataset[crs$validate, c(crs$input, crs$target)]) > 0.5, "1", "-1"))

# Generate the confusion matrix showing counts.

table(crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai, crs$pr,
      dnn=c("Actual", "Predicted"))

# Generate the confusion matrix showing proportions.

pcme <- function(actual, cl)
{
  x <- table(actual, cl)
  tbl <- cbind(round(x/length(actual), 2),
               Error=round(c(x[1,2]/sum(x[1,]),
                             x[2,1]/sum(x[2,])), 2))
  names(attr(tbl, "dimnames")) <- c("Actual", "Predicted")
  return(tbl)
};
pcme(crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai, crs$pr)

# Calculate the overall error percentage.

overall <- function(x)
{
  if (nrow(x) == 2) 
    cat((x[1,2] + x[2,1]) / sum(x)) 
  else
    cat(1 - (x[1,rownames(x)]) / sum(x))
} 
overall(table(crs$pr, crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai,  
              dnn=c("Predicted", "Actual")))

# Calculate the averaged class error percentage.

avgerr <- function(x) 
  cat(mean(c(x[1,2], x[2,1]) / apply(x, 1, sum))) 
avgerr(table(crs$pr, crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai,  
             dnn=c("Predicted", "Actual")))

# Generate an Error Matrix for the Neural Net model.

# Obtain the response from the Neural Net model.

crs$pr <- predict(crs$nnet, newdata=crs$dataset[crs$validate, c(crs$input, crs$target)], type="class")

# Generate the confusion matrix showing counts.

table(crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai, crs$pr,
      dnn=c("Actual", "Predicted"))

# Generate the confusion matrix showing proportions.

pcme <- function(actual, cl)
{
  x <- table(actual, cl)
  tbl <- cbind(round(x/length(actual), 2),
               Error=round(c(x[1,2]/sum(x[1,]),
                             x[2,1]/sum(x[2,])), 2))
  names(attr(tbl, "dimnames")) <- c("Actual", "Predicted")
  return(tbl)
};
pcme(crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai, crs$pr)

# Calculate the overall error percentage.

overall <- function(x)
{
  if (nrow(x) == 2) 
    cat((x[1,2] + x[2,1]) / sum(x)) 
  else
    cat(1 - (x[1,rownames(x)]) / sum(x))
} 
overall(table(crs$pr, crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai,  
              dnn=c("Predicted", "Actual")))

# Calculate the averaged class error percentage.

avgerr <- function(x) 
  cat(mean(c(x[1,2], x[2,1]) / apply(x, 1, sum))) 
avgerr(table(crs$pr, crs$dataset[crs$validate, c(crs$input, crs$target)]$shanghai,  
             dnn=c("Predicted", "Actual")))