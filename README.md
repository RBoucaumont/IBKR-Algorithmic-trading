# IBKR-Algorithmic-trading
Implementation, development and connection of an algorithmic trading strategy with Interactive Brokers API.

*Strategy1.py*
Code which executes basic dual signals strategy with TWS API. This strategy will buy when current prices breaks through triangle formation (ie. lower highs and higher lows) and breaks 50 EMA. 

*MarketData.py*
Code to request realtime market data from IBKR TWS API.

*PlaceOrder.py*
Code to execute market order to IBKR TWS API. Possibility to change market order and account information.

