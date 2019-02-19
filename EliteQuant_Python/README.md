# EliteQuant_Python
Python quantitative trading and investment platform

* [Platform Introduction](#platform-introduction)
* [Project Summary](#project-summary)
* [Participation](#participation)
* [Installation](#installation)
* [Development Environment](#development-environment)
* [Architecture Diagram](#architecture-diagram)
* [Todo List](#todo-list)

---

## Platform Introduction

EliteQuant is an open source forever free unified quant trading platform built by quant traders, for quant traders. It is dual listed on both [github](https://github.com/EliteQuant) and [gitee](https://gitee.com/EliteQuant).

The word unified carries two features.
- First it’s unified across backtesting and live trading. Just switch the data source to play with real money.
- Second it’s consistent across platforms written in their native langugages. It becomes easy to communicate with peer traders on strategies, ideas, and replicate performances, sparing language details.

Related projects include
- [A list of online resources on quantitative modeling, trading, and investment](https://github.com/EliteQuant/EliteQuant)
- [C++](https://github.com/EliteQuant/EliteQuant_Cpp)
- [Python](https://github.com/EliteQuant/EliteQuant_Python)
- [Matlab](https://github.com/EliteQuant/EliteQuant_Matlab)
- [R](https://github.com/EliteQuant/EliteQuant_R)
- [C#](https://github.com/EliteQuant/EliteQuant_CSharp)
- [Excel](https://github.com/EliteQuant/EliteQuant_Excel)
- [Java](https://github.com/EliteQuant/EliteQuant_Java)
- [Scala](https://github.com/EliteQuant/EliteQuant_Scala)
- [Kotlin](https://github.com/EliteQuant/EliteQuant_Kotlin)
- [Go](https://github.com/EliteQuant/EliteQuant_Go)
- [Julia](https://github.com/EliteQuant/EliteQuant_Julia)

## Project Summary

EliteQuant_Python is Python3 based multi-threading, concurrent high-frequency trading platform that provides consistent backtest and live trading solutions. It follows modern design patterns such as event-driven, server/client architect, and loosely-coupled robust distributed system. It follows the same structure and performance metrix as other EliteQuant product line, which makes it easier to share with traders using other languages.

## Participation

Please feel free to report issues, fork the branch, and create pull requests. Any kind of contributions are welcomed and appreciated. Through shared code architecture, it also helps traders using other languges.

## Installation

No installation is needed, it's ready for use out of box. Just download the code and enjoy. 

### Backtest

On python side, it depends some python packages. Here are the instructions after a **clean installation** of Anaconda Python 3.6 on Windows 10 system.

1. Add the unzipped folder for example d:\workspace\EliteQuant_Python to PYTHONPATH environment variable

![PYTHONPATH](/resource/pythonpath.PNG?raw=true "PYTHONPATH")

2. pip install the following under command prompt cmd

```python
pip install quandl
pip install pandas-datareader
pip install tushare
pip install pyfolio
pip install qdarkstyle
```

3.  Configure config_backtest.yaml in the source directory

    * datasource: historical data source
    * hist_dir: local history data directory
    * output_dir: output test results directory

    Currently it supports data source from

    * Quandl
    * Tushare
    * Local CSV

4. stay in command prompt, execute

```python
cd source
python backtest_engine.py
```

### Live Trading

Live trading needs one more python package, nanomsg. Here is how to install it on Windows

1. In command prompt, execute
```python
cd resource
easy_install nanomsg-1.0-py3.6-win-amd64.egg
```
2. go to folder createed by last step, C:\Anaconda3\Lib\site-packages\nanomsg-1.0-py3.6-win-amd64.egg\nanomsg-1.0-py3.6-win-amd64.egg\, cut+paste move everything one level up, and delete the extra folder nanomsg-1.0-py3.6-win-amd64.egg.

3. copy resource\nanomsg.dll to C:\Anaconda3\Lib\site-packages\nanomsg-1.0-py3.6-win-amd64.egg\

4. After that, configure source/config.yaml
 
    * If you want to use interactive broker, open IB trader workstation (TWS), go to its menu File/Global Configuration/API/Settings, check "Enable ActiveX and Socket Client", uncheck "Read-Only API"
    * In the config file, change the account id to yours; IB account id usually can be found on the top right of the TWS window.
    * If you use CTP, change your brokerage account information and ctp addresses accordingly.
    * create folder for log_dir and data_dir respectively. The former records runtime logs, while the later saves tick data.

5. run python live_engine.py

![Live Demo](/resource/ib_demo.gif?raw=true "Live Demo")

**Interactive Brokers**
is the most popular broker among retail traders. A lot of retail trading platform such as quantopian, quantconnect are built to support IB. If you don't have IB account but want to try it out, they provide demo account edemo with password demouser. Just download TWS trader workstation and log in with this demo account. Note that accound id changes everytime you log on to TWS with demo account so you have to change EliteQuant config file accordingly.

**CTP**
is the de-facto brokerage for Chinese futures market, including commodity futures and financial futures. They also offer free demo account [SimNow](http://simnow.com.cn/). After registration, you will get account, password, brokerid, along with market data and trading broker address. Replace them in EliteQuant config file accordingly.

## Development Environment

Below is the environment we are using
* Anaconda Python 3.6
* PyCharm Community version 2017.2.4

## Architecture Diagram

Backtest

![Backtest](/resource/Backtest_Diagram.PNG?raw=true "Backtest")

Live Trading

![Live Trading](/resource/Live_Trading_Diagram.PNG?raw=true "Live Trading")

Code Structure

![Code Structure](/resource/code_structure_en.PNG?raw=true "Code Structure")

## Todo List