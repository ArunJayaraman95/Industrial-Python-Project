import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QApplication, QFileDialog, QTableWidgetItem
from PyQt5.uic import loadUi
from dotenv import load_dotenv
import os
import ctypes
import pandas as pd
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.techindicators import TechIndicators
import matplotlib.pyplot as plt
import numpy as np
import logging

# ? MessageBox format CTYPES for popup windows
# ctypes.windll.user32.MessageBoxW(0, "Your text", "Your title", 1)

# Get environment variable to get API key
load_dotenv()
ALPHA_KEY = os.getenv("ALPHA_KEY")

logging.basicConfig(level=logging.INFO)


class MainWindow(QDialog):
    def __init__(self):
        super(MainWindow, self).__init__()

        # Attributes
        self.ticker = "TSLA"  # Ticker symbol
        self.money = 0
        self.log = []
        self.isInvested = False
        self.buyTolerance = 0
        self.sellTolerance = 0
        self.actionCount = 0
        self.trail = 0
        self.tickerList = []

        loadUi("StockGUI.ui", self)
        self.initTable()

        # Connections to callback functions
        self.exitButton.clicked.connect(self.kill)
        self.GetStockDataButton.clicked.connect(self.evaluateStrategy)
        self.tickerEdit.textChanged.connect(self.updateValues)

    def logActions(self, price, buysell):
        """Log a buy/sell action to the log.
        Showing current price, money, action and resulting money"""

        roundMoney = f"${round(self.money, 2)}"
        roundSell = f"${round(self.money + price, 2)}"
        roundBuy = f"${round(self.money - price, 2)}"
        price = f"${price}"
        logMsg = ""

        if buysell == "S":
            logMsg = f"{roundMoney} now.Sold at {price} => {roundSell}"
            self.addRow(roundMoney, "Sell", price, roundSell)
        else:
            logMsg = f"{roundMoney} now. Bought at {price} => {roundBuy}"
            self.addRow(roundMoney, "Buy", price, roundBuy)

        self.log.append(logMsg)

    def readTickerFile(self):
        with open("tickers.txt", "r") as file:
            for line in file:
                self.tickerList.append(line.strip())
                logging.info(line.strip())

    def updateValues(self):
        self.ticker = self.tickerEdit.text().upper()
        if self.buyToleranceEdit.text() == "":
            self.buyTolerance = 0
        else:
            self.buyTolerance = float(self.buyToleranceEdit.text())

        if self.sellToleranceEdit.text() == "":
            self.sellTolerance = 0
        else:
            self.sellTolerance = float(self.sellToleranceEdit.text())

        if self.trailStopEdit.text() != "":
            self.trail = float(self.trailStopEdit.text())

    def reset(self):
        # Clear/Delete graph
        plt.clf()
        plt.cla()
        plt.close()
        # Reset table
        self.actionLog.setRowCount(0)

        # Reset values to defaults
        self.money = 0
        self.log = []
        self.isInvested = False
        self.buyTolerance = 0
        self.sellTolerance = 0
        self.actionCount = 0
        self.trail = 0
        self.readTickerFile()

    def evaluateStrategy(self):
        """Gets stock data and runs
        through data to evaluate trading strategy."""

        self.reset()
        self.updateValues()

        # print(self.buyTolerance, "xxx", self.sellTolerance)s
        logging.info(f"{self.buyTolerance} + {self.sellTolerance}")

        # Get weekly timeseries data for given stock and put into pandas dataframe
        ts = TimeSeries(key=ALPHA_KEY, output_format="pandas")
        try:
            data_ts, meta_data_ts = ts.get_weekly(symbol=self.ticker)
        except:
            ctypes.windll.user32.MessageBoxW(0, "Invalid Ticker", "ERROR", 1)
            sys.exit(0)
        data_otn = data_ts.iloc[::-1]  # Reverse to order from old to recent

        data = data_otn["4. close"].to_frame()  # Isolate to closing column
        data["SMA30"] = (
            data["4. close"].rolling(30).mean()
        )  # Calculate 30 week moving average
        data.dropna(inplace=True)  # Remove NA (null) values

        # Parameters for plot
        plt.rcParams["figure.figsize"] = [16, 8]
        plt.plot(data[["4. close", "SMA30"]])

        # Loop through and check for buy or sell conditions
        for i in range(len(data["SMA30"])):
            currentPrice = data["4. close"][i]
            currentSMA = data["SMA30"][i]

            underSMA = currentPrice < currentSMA
            overSMA = currentPrice > currentSMA

            underBuyTolerance = currentPrice <= (1 - self.buyTolerance) * currentSMA
            overSellTolerance = currentPrice >= (1 + self.sellTolerance) * currentSMA

            if underSMA and underBuyTolerance and not self.isInvested:
                plt.plot(
                    [data.index[i]],
                    [currentSMA],
                    marker="$B$",
                    ls="none",
                    ms=10,
                    color="red",
                )
                self.isInvested = True
                self.logActions(currentPrice, "B")
                self.money -= currentPrice

            elif overSMA and overSellTolerance and self.isInvested:
                plt.plot(
                    [data.index[i]],
                    [currentSMA],
                    marker="$S$",
                    ls="none",
                    ms=10,
                    color="lime",
                )
                self.isInvested = False
                self.logActions(currentPrice, "S")
                self.money += currentPrice

        # Print log to console
        # for entry in self.log:
        #     print(entry)

        figs = list(map(plt.figure, plt.get_fignums()))

        figs[0].canvas.manager.window.move(-1800, 300)

        plt.show()

    def initTable(self):
        t = self.actionLog
        t.setRowCount(0)
        t.setColumnCount(4)

        columnLabels = ["Previous $", "Action", "Stock $", "Current $"]
        t.setHorizontalHeaderLabels(columnLabels)
        # t.setItem(0, 0, QTableWidgetItem(str(3)))

    def addRow(self, prevPrice, action, stockPrice, currentPrice):
        self.actionLog.insertRow(self.actionCount)
        for idx, entry in enumerate([prevPrice, action, stockPrice, currentPrice]):
            self.actionLog.setItem(self.actionCount, idx, QTableWidgetItem(str(entry)))

        self.actionCount += 1

    def kill(self):
        """Exit the Interface"""
        # Close graph
        plt.clf()
        plt.cla()
        plt.close()

        sys.exit(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainwindow = MainWindow()
    widget = QtWidgets.QStackedWidget()
    widget.addWidget(mainwindow)
    widget.setFixedWidth(1000)
    widget.setFixedHeight(700)
    widget.show()
    sys.exit(app.exec_())
