from os import close
import ibapi
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import *
import threading
import time 
import ta
import math
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytz 


# Vars
orderId = 1

# Class for Interactive Brokers Connection
class IBApi (EWrapper, EClient): 
    def __init__(self):
        EClient.__init__(self, self)
    # historical backtest Data 
    def historicalData(self, reqId, bar): 
        try:
            bot.on_bar_update(reqId,bar,False)
        except Exception as e: 
            print(e)
    # On Realtime Bar after historical data finished
    def historicalDataUpdate(self, reqId, bar):
        try:
            bot.on_bar_update(reqId,bar,True)
        except Exception as e: 
            print(e)
    # On hitorical Data End 
    def historicalDataEnd(self, reqId, start, end):
        print(reqId)
    # get next order ID we can use
    def nextValidId(self, nextorderId):
        global orderId
        orderId = nextorderId
    #Listen for realtime bars 
    def realtimeBar(self, reqId, time, open_, high, low, close,volume, wap, count):
        super().realtimeBar(reqId, time, open_, high, low, close, volume, wap, count)
        try:
            bot.on_bar_update(reqId, time, open_, high, low, close, volume, wap, count)
        except Exception as e:
            print(e)
    def error(self, id, errorCode, errorMsg):
        print(errorCode)
        print(errorMsg)


# Bar Object
class Bar: 
    open = 0 
    low = 0 
    high = 0 
    close = 0 
    volume = 0 
    date = datetime.now()
    def __init__(self):
        self.open = 0
        self.low = 0 
        self.high = 0 
        self.close = 0 
        self.volume = 0
        self.date = datetime.now()
    

#Bot logic
class Bot:
    ib = None
    barsize = 1 # 1 min barsize
    currentBar = Bar()
    bars = []
    reqId = 1
    global orderId
    smaPeriod = 50
    symbol = ""
    initialbartime = datetime.now().astimezone(pytz.timezone("America/New_York"))


    def __init__(self):
        #Connect to IB on init
        self.ib = IBApi()
        self.ib.connect("127.0.01", 7497,1)
        ib_thread = threading.Thread(target=self.run_loop, daemon=True)
        ib_thread.start()
        time.sleep(1)
        currentBar = Bar()
        # get symbol info
        self.symbol = input("Enter the symbol you want to trade : ")
        # Get Bar Size 
        self.barsize = input("Enter the barsize you want to trade in minutes : ")
        mintext = "min"
        if (int(self.barsize)> 1): 
            mintext = "mins"
        queryTime = (datetime.now().astimezone(pytz.timezone("America/New_York"))-timedelta(days=1)).replace(hour=16,minute=0,second=0,microsecond=0).strftime("%Y%m%d %H:%M:%S")
        # create our IB contract object
        contract = Contract()
        contract.symbol = self.symbol.upper()
        #change depending on what contracts rading 
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        self.ib.reqIds(-1)
        # request market data 
                        #self.ib.reqRealTimeBars(0, contract, 5, "TRADES", 1, [])
        self.ib.reqHistoricalData(self.reqId,contract,"","2 D",str(self.barsize)+mintext,"TRADES",1,1,True,[])

    # Listen to socket in serparate thread 
    def run_loop(self):
        self.ib.run()

    # Bracket Order SetUp
    def bracketOrder(self, parentOrderId, action, quantity, profitTarget, stopLoss):
        #initial entry 
        #create our IB Contract Object 
        contract = Contract()
        contract.symbol = self.symbol.upper()
        #change depending on what contracts trading 
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        # Create Parent Order / initial entry 
        parent = Order()
        parent.orderId = parentOrderId
        parent.orderType = "MKT"
        parent.action = action 
        parent.totalQuantity = quantity
        parent.transmit = False
        # Profit Target 
        profitTargetOrder = Order()
        profitTargetOrder.orderId = parent.orderId+1
        profitTargetOrder.orderType = "LMT"
        profitTargetOrder.action = "SELL"
        profitTargetOrder.totalQuantity = quantity
        profitTargetOrder.lmtPrice = round(profitTarget,2)
        profitTargetOrder.parentId = parentOrderId
        profitTargetOrder.transmit = False
        # Stop Loss 
        stopLossOrder = Order()
        stopLossOrder.orderId = parent.orderId+2
        stopLossOrder.orderType = "STP"
        stopLossOrder.action = "SELL"
        stopLossOrder.totalQuantity = quantity
        stopLossOrder.parentId = parentOrderId
        stopLossOrder.auxPrice = round(stopLoss,2)
        stopLossOrder.transmit = True

        bracketOrders = [parent, profitTargetOrder, stopLossOrder]
        return bracketOrders
        
    # pass realtime bar data back to our bot object
    def on_bar_update(self, reqId, bar,realtime):
        global orderId
        #Historical Data to catch up
        if (realtime == False): # means we are backtesting #
            self.bars.append(bar)
        else:
            bartime = datetime.strptime(bar.date,"%Y%m%d %H:%M:%S").astimezone(pytz.timezone("America/New_York"))
            minutes_diff = (bartime-self.initialbartime).total_seconds() / 60.0
            self.currentBar.date = bartime
            # On bar Close (means when bar close, can be changed to reach a certain time or price)
            if (minutes_diff > 0 and math.floor(minutes_diff) % self.barsize == 0):
                #Entry - If we have a higher high, a higher low and we cross the 50 SMA buy 
                #1) SMA
                closes = []
                for bar in self.bars:
                    closes.append(bar.close)
                self.close_array = pd.Series(np.asarray(closes))
                self.sma = ta.trend.sma(self.close_array,self.smaPeriod,True)
                print (" SMA : " + str(self.sma[len(self.sma)-1]))
                # 2) Calculate higher highs and lows 
                lastLow = self.bars[len(self.bars)-1].low
                lastHigh = self.bars[len(self.bars)-1].high
                lastClose = self.bars[len(self.bars)-1].close
                lastBar=self.bars[len(self.bars)-1]
                # Check criteria 
                if (bar.close > lastHigh
                    and self.currentBar.low > lastLow
                    and bar.close > self.str(self.sma[len(self.sma)-1])
                    and lastClose < str(self.sma[len(self.sma)-2])):
                    #bracket Order 2% profit target 1% stop Loss 
                    profitTarget = bar.close*1.02
                    stopLoss = bar.close*0.99
                    quantity = 1
                    bracket = self.bracketOrder(orderId, "BUY", quantity, profitTarget, stopLoss)
                    contract = Contract()
                    contract.symbol = self.symbol.upper()
                    #change depending on what contracts trading 
                    contract.secType = "STK"
                    contract.exchange = "SMART"
                    contract.currency = "USD"
                    #Place Bracket Order 
                    for o in bracket: 
                        o.ocaGroup = "OCA_"+str(orderId)
                        #o.ocaType = 2 
                        self.ib.placeOrder(o.orderId,contract,o)
                    orderId += 3
                #Bar closed append
                self.currentBar.close = bar.close
                if (self.currentBat.date != lastBar.date):
                    print("New bar!")
                    self.bars.append(self.currentBar)
                self.currentBar.open = bar.open 
                
        #Build realtime bar
        if (self.currentBar.open == 0):
            self.currentBar.open = bar.open
        if (self.currentBar.high == 0 or bar.high > self.currentBar.high):
            self.currentBar.high = bar.high
        if (self.currentBar.low == 0 or bar.low < self.currentBar.low):
            self.currentBar.low = bar.low


# start bot
bot = Bot()