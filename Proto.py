import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QApplication, QFileDialog
from PyQt5.uic import loadUi
from bs4 import BeautifulSoup as bs
from dotenv import load_dotenv
import os
from sys import exit
import pandas as pd
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.techindicators import TechIndicators
import matplotlib.pyplot as plt
import numpy as np

# ! Extract key to .env file

# ? MessageBox format CTYPES
# ctypes.windll.user32.MessageBoxW(0, "Your text", "Your title", 1)
load_dotenv()
ALPHA_KEY = os.getenv("ALPHA_KEY")

class MainWindow(QDialog):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        # Attributes
        self.ticker = "TSLA" # Ticker symbol
        self.money = 0
        self.log = []
        self.isInvested = False
        self.buyTolerance = 1
        self.sellTolerance = 1

        
        loadUi("StockGUI.ui", self)
        
        # Connections
        self.exitButton.clicked.connect(self.kill)
        self.GetStockDataButton.clicked.connect(self.doStuff)


    def logActions(self, price, buysell):
        roundMoney = round(self.money, 2)
        roundBuy = round(self.money + price, 2)
        roundSell = round(self.money - price, 2)
        logMsg = ""
        if buysell == "S":
            logMsg = f"{roundMoney} now.Sold at ${price} => {roundBuy}"
        else:
            logMsg = f"{roundMoney} now. Bought at ${price} => {roundSell}"
        self.log.append(logMsg)

    def doStuff(self):
        periods = 60
        ts = TimeSeries(key=ALPHA_KEY, output_format='pandas')
        data_ts, meta_data_ts = ts.get_weekly(symbol='GOOG')
        data_otn = data_ts.iloc[::-1]
        # data_otn.head()
        data = data_otn['4. close'].to_frame() # Isolate to closing column
        data['SMA30'] = data['4. close'].rolling(30).mean() # Calculate 30 week moving average
        data.dropna(inplace = True)
        plt.rcParams["figure.figsize"] = [16, 8]
        plt.plot(data[['4. close', 'SMA30']])

        isInvested = False # Assume you start with no money invested
        money = 0
        log = []

        moneySpent = 0

        buyTolerance = 0  #  0.05
        sellTolerance = 1 #0.15
        def logAction(price, buysell):
            if buysell == "S":
                log.append(f"{round(money, 2)} now.Sold at ${price} => {round(money + price, 2)}")
            else:
                log.append(f"{round(money, 2)} now. Bought at ${price} => {round(money - price, 2)}")
            
        # Loop through and check if price < sma or not
        for i in range(len(data['SMA30'])):
            currentPrice = data['4. close'][i]
            currentSMA = data['SMA30'][i]
            
            if currentPrice < currentSMA and not isInvested and currentPrice <= (1 - buyTolerance) * currentSMA:
                plt.plot([data.index[i]], [currentSMA], marker = "$B$", ls = 'none', ms = 10, color = "red")
                isInvested = True
                logAction(currentPrice, "B")
                money -= currentPrice
                
            elif currentPrice > currentSMA and isInvested and currentPrice >= sellTolerance * currentSMA:
                plt.plot([data.index[i]], [currentSMA], marker = "$S$", ls = 'none', ms = 10, color = "lime")
                isInvested = False
                logAction(currentPrice, "S")
                money += currentPrice
        for entry in log:
            print(entry)
        plt.show()
    def kill(self):
        """Exit the Interface"""
        print(ALPHA_KEY)
        exit(0)

app=QApplication(sys.argv)
mainwindow=MainWindow()
widget=QtWidgets.QStackedWidget()
widget.addWidget(mainwindow)
widget.setFixedWidth(1000)
widget.setFixedHeight(700)
widget.show()
sys.exit(app.exec_())