## Abstract
We used Machine learning techniques to evaluate past data pertaining to the stock market and world affairs of the corresponding time period, in order to make predictions in stock trends. We built a model that will be able to buy and sell stock based on profitable prediction, without any human interactions. The model uses Natural Language Processing (NLP) to make smart “decisions” based on current affairs, article, etc. With NLP and the basic rule of probability, our goal is to increases the accuracy of the stock predictions.

## Introduction
Natural Language Processing is a technique used by a computer to understand and manipulate natural languages. By natural languages, we mean all human derived languages. Natural language processing or NLP for short is used to analyze text and let machines derive meaning from the input. This human-computer interaction allows us to come up with many different applications to bring man and machine as one. For example, on google, if we use 
google translation, that is NLP and so is speech recognition. In our project, we make use of some established NLP techniques to evaluate past data pertaining to the stock market and world affairs of the corresponding time period, in order to make predictions in stock trends. 

In order to proceed with this objective, we needed to understand what Sentimental Analysis is. Sentimental Analysis is an analytical method that the computer uses to understand a natural language and deduce if the message is positive, neutral or negative. In our case, Sentimental analysis refers to the deduction of the news headlines if they increase the stock or reduce it. By doing so, we end up with the ‘emotional’ status of the data which is what sentimental analysis gives its user.

## Data Collection and Wrangling
We have used the Combined_News_DJIA.csv dataset (courtesy Aaron7sun, Kaggle.com) .The Combined_News_DJIA.csv dataset spans from 2008 to 2016. We extended the dataset to include additional data. This additional data is collected from the Guardian’s Restful News API for the 2000- 2008 period. We take the 25 most popular headlines for each given day in this period. In addition, we also pull the Dow Jones Index (DJI) of Yahoo Finance’s website for the 2000- 2008 period to compare the influence of the data.  There are two channels of data provided in this dataset:
       
* News data that has historical news headlines from Reddit World News Channel. Only the top 25 headlines are considered for a single date. 
* Stock data for Dow Jones Industrial Average (DJIA) over the corresponding time range is used to label the data. The stock data is compiled from Yahoo Finance.
Note: The headlines for each data acts as the explanatory data that causes the stock price to either rise (labeled 1) or to fall (labelled 0). We have the top 25 headlines for one single date arranged as one row of the extracted data set.
Since our goal is to predict the tendency of the stock of a specific company, the data that lead the stock’s price of the next day to decline or stay the same are labelled “0”, while the data that lead the price of the next day to rise are labelled “1”. We compare the data between the two pulled data set and then merge them together to get the more accurate prediction.

With the raw data, we cannot proceed much further until we manipulate the data to suit our analysis and convert the data into vectors that are much easier to work on. For this, we use Word2Vec. This is a group of related models used to create word embeddings. Word embeddings are sets of language modeling and feature learning techniques in NLP where words or phrases from the vocabulary are mapped to vectors of real numbers. These vectors make up the training and test sets. English is really easy – see all those spaces? That makes it really easy to tokenize – in other words, to determine what’s a word. So we just use a simple set of rules for English tokenization.
This raw data is manipulated using python. We first split the data into lists of words but these lists are flooded with HTML tags and punctuations. We cleaned up the data and removed all HTML tags and punctuations. Then we moved forward with removing stop words. Stop words are words that do not contribute to the meaning or sentiment of the data such as ‘the’, ‘is’, ‘and’, etc. We have also converted all the letters to lowercase to make a more even data set to play with.

## Workflow
With the training data set, we got to convert them into numeric representation for machine learning. For this, we use ‘Bag of Words’ model. The Bag of Words model learns a vocabulary from all of the documents, then models each document by counting the number of times each word appears. These values are the feature vectors that are derived from the model. 
The thing is we cannot stop at just using the Bag of Words model as this generates feature vectors that only give importance to the number of occurrences of words rather than where they occur and with what words they accompany. To get past this, we use the n-gram model or the skip gram model. Now, with this model, we can store the order of words in the way they occur in the data. The number of words stored in a single order depends on the value on n. Say n=2, calls for a bigram model which stores sets of 2 words in order.
 	We use Natural Language Processing (NLP) to interpret and construct the data set. The data are composed of a row of sentences. In order to reduce the complexity, the stop words such as “a”, “and”, “the” have been cleaned. In addition, we came across the N-gram model which helps predict the next set of words in an n- worded text or speech. The Google’s Word2Vec deep learning method are also provided to focus on the sentiment of the words by means of the bag of words concept. This method is suitable for us because it doesn’t need labels in order to create meaningful representations. If there are enough training data, it would produces word vector with intriguing characteristics so that we could analyze the relationship between the words that have similar meanings.
With all this done, we have our manipulated data vectors ready to be trained and tested. We have split the extracted dataset in the ratio of 4:1. 80% of the extracted data will be the training data and 20% of the extracted data will be the test data. We work with 4 models in this project to train our data.
* Naive Bayes
* Random Forest
* Logistic Regression
* Support Vector Machines

## Environment
We used Jupyter Notebook which is an open-source web application that allows you to create and share documents that contain live code, equations, visualizations and explanatory text. We perform data cleaning and transformation, statistical modeling and machine learning in this environment.


## Comparison of Model Performance using Accuracy of Prediction
![Alt text](https://github.com/niharikabalachandra/Stock-Market-Prediction-Using-Natural-Language-Processing/blob/master/chart.png)
* Random forests had highest accuracy on the a Bi-gram model as shown in the chart. The prediction accuracy was 85.97%. Using Natural 
* Language Processing techniques, we were able to accurately predict the stock market trends 85% of the time. 


## Conclusion
Social Media can sometimes be deceiving when delivering the right frame of speech. Here we have used twitter feed and news articles around the web that has influenced the stock market of a company. Through this project, it helped us understand the basics of Natural Language Processing. Even though you can’t bet your money on the stock from this project, this work can be treated as solid understanding of the basics of Natural Language Processing. Using the same model for different text data is also feasible. It was interesting to know about how to go from text data to vectors of numbers and applying Machine learning techniques that can help to influence the stock market of a company. It helped us a gain wider sense of the power of NLP in various applications. From reading about machine learning models in class to implement them with real data and observe the performance of a model, tuning the parameters, performing exploratory data analysis set a great learning curve for future projects. 

We also went from using an available data set to scraping our own data which made this project a little more interesting and challenging. To get more insights on which model to use and how to construct them, we learnt by reading through research papers and usage of scikit learn to build our models. As any project that does not take a straight path towards completion we hit certain roadblocks while implementing this project. 

Road block 1: 
As any machine learning task is concerned the data in consideration  was restrictive and had few data cleaning to be done. Firstly the data consisted of a character “’b” appended to text in multiple ways and was a little challenging to remove it across the entire dataset.  

Road block 2: 
It was also challenging to find more data. The dataset available to use was from 2008 to 2016. We had to scrape it from another source (Yahoo News) completely and put in the format that we wanted to work for our Machine learning model.It was a challenging task to scrape it and wrangle it to the data set that we wanted to (25 top headlines and labels associated with them)

Road block 3: 
While we put the dataset for our SVM model, there were quite a few errors it kept throwing and one of them being NaN values and the number of cores we used to train our model. We used all the 4 cores to run our algorithm in parallel for faster execution. 

## Future work
This project leaves room for future work and ways to accomplish them: 
The number of features used in the data set can be expanded. Right now we have gathered the top 25 News headlines, It is important to have more features that help the model learn better. 
We are looking at the stock of one company. We can expand it to work for multiple companies at once and we can also include real time- time series analysis. 
Perform multi class classification for various parameters of stock trading.

## Appendix: Code
All the source files used in this project can be found at: https://github.com/niharikabalachandra/Stock-Market-Prediction-Using-Natural-Language-Processing 


## References

F. Xu and V. Keelj, "Collective Sentiment Mining of Microblogs in 24-Hour Stock Price Movement Prediction," 2014 IEEE 16th Conference on Business Informatics, Geneva, 2014, pp. 60-67. doi: 10.1109/CBI.2014.37

L. Bing, K. C. C. Chan and C. Ou, "Public Sentiment Analysis in Twitter Data for Prediction of a Company's Stock Price Movements," 2014 IEEE 11th International Conference on e-Business Engineering, Guangzhou, 2014, pp. 232-239. doi: 10.1109/ICEBE.2014.47

D. Rao, F. Deng, Z. Jiang and G. Zhao, "Qualitative Stock Market Predicting with Common Knowledge Based Nature Language Processing: A Unified View and Procedure," 2015 7th International Conference on Intelligent Human-Machine Systems and Cybernetics, Hangzhou, 2015, pp. 381-384. doi: 10.1109/IHMSC.2015.114

Z. Jiang, P. Chen and X. Pan, "Announcement Based Stock Prediction," 2016 International Symposium on Computer, Consumer and Control (IS3C), Xi'an, 2016, pp. 428-431. doi: 10.1109/IS3C.2016.114

W. Bouachir, A. Torabi, G. A. Bilodeau and P. Blais, "A bag of words approach for semantic segmentation of monitored scenes," 2016 International Symposium on Signal, Image, Video and Communications (ISIVC), Tunis, 2016, pp. 88-93. doi: 10.1109/ISIVC.2016.7893967

D. Sehgal and A. K. Agarwal, "Sentiment analysis of big data applications using Twitter Data with the help of HADOOP framework," 2016 International Conference System Modeling & Advancement in Research Trends (SMART), Moradabad, 2016, pp. 251-255. doi: 10.1109/SYSMART.2016.7894530

R. Zhao; K. Mao, "Fuzzy Bag-of-Words Model for Document Representation," in IEEE Transactions on Fuzzy Systems , vol.PP, no.99, pp.1-1 doi: 10.1109/TFUZZ.2017.2690222

V. U. Thompson, C. Panchev and M. Oakes, "Performance evaluation of similarity measures on similar and dissimilar text retrieval," 2015 7th International Joint Conference on Knowledge Discovery, Knowledge Engineering and Knowledge Management (IC3K), Lisbon, 2015, pp. 577-584

C. Sreejith, M. Indu and P. C. R. Raj, "N-gram based algorithm for distinguishing between Hindi and Sanskrit texts," 2013 Fourth International Conference on Computing, Communications and Networking Technologies (ICCCNT), Tiruchengode, 2013, pp. 1-4. doi: 10.1109/ICCCNT.2013.6726777

M. Kaya, G. Fidan and I. H. Toroslu, "Sentiment Analysis of Turkish Political News," 2012 IEEE/WIC/ACM International Conferences on Web Intelligence and Intelligent Agent Technology, Macau, 2012, pp. 174-180. doi: 10.1109/WI-IAT.2012.115
