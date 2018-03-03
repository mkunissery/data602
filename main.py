from datetime import datetime
import random
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

from enum import Enum
class UserOptions(Enum):
    TRADE = 1
    SHOWBlOTTER = 2
    SHOWPL = 3
    QUIT = 4

class TradeBlotter:

    def AppendTradeLog(self, Ticker, Qty, tType, Price):
        global dflog
        dflog = dflog.append({'Ticker': Ticker, 'Qty': Qty, 'Type': tType, 'Price': Price, 'Cost':Price*Qty, 'Time':datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}, ignore_index=True)

    def GetQuoteFromYahooFinance(self,ticker,type):
        struri = "https://finance.yahoo.com/quote/" + ticker + "?p=" + ticker
        res = requests.get(struri)

        soup = BeautifulSoup(res.content, 'lxml')
        table = soup.find_all('td', {"data-test": type+"-value"})
        soup = BeautifulSoup(str(table), 'lxml')
        span = soup.find("span")
        if span is None:
            soup = BeautifulSoup(res.content, 'lxml')
            table = soup.find_all('td', {"data-test":  "PREV_CLOSE-value"})
            soup = BeautifulSoup(str(table), 'lxml')
            span = soup.find("span")

        if span != None:
            askval = span.text
            ask = askval.split(" ")
            retval = ask[0].replace(",","")
            #retval = round(float(retval)*random.uniform(0.985, 1.01),3) # temporary arragement to make price seem different
            return(str(retval))
        else:
            return(0)

    def GetSummaryStats(self,ticker):
        struri = "https://finance.yahoo.com/quote/" + ticker + "?p=" + ticker
        res = requests.get(struri)
        soup = BeautifulSoup(res.content, 'lxml')
        table = soup.find_all('table', {"data-reactid": "8"})
        soup = BeautifulSoup(str(table), 'lxml')
        df = pd.read_html(str(table))[0]
        return (df)

    def CreateBlotterDataFrame(self):
        #df = pd.read_csv("list.csv",",")
        url = 'https://raw.githubusercontent.com/mkunissery/data/master/list.csv'
        df = pd.read_csv(url)
        return (df)

    def CreateTradeLogDataFrame(self):
        url = 'https://raw.githubusercontent.com/mkunissery/data/master/tradelog.csv'
        df = pd.read_csv(url)
        #df = pd.read_csv("tradelog.csv",",")
        return (df)

    def ShowAvailableCash(self):
        global df
        balance = float(df[df['Ticker'] == 'CASH']["Position"])
        print("\nCash Available:" + '${:,.2f}'.format(balance) + "\n")

    def MakeTrade(self,df):
        print("Enter the ticker you want to trade from the list (AAPL AMZN INTC MSFT SNAP)")
        ticker = input("Enter Ticker:").upper()
        if df["Ticker"].str.contains(ticker).sum() > 0:
            print("-------------------------------\nTicker Summary Characteristics\n-------------------------------")
            print(TradeBlotter.GetSummaryStats(self, ticker))
            balance = float(df[df['Ticker'] == 'CASH']["Position"])
            TradeBlotter.ShowAvailableCash(self)
            position = float(df[df['Ticker'] == ticker.upper()]["Position"])
            BuyOrSell = input("Do You want to Buy (1) , Sell (2):")
            if(BuyOrSell=="1"):
                qty = int(input("Enter the quantity you want to buy:"))
                quote = TradeBlotter.GetQuoteFromYahooFinance(self,ticker,"ASK")
                if(quote != 0):
                    cost = float(quote) * qty
                    if(cost < balance):
                        df.loc[df['Ticker'] == 'CASH', 'Position'] = balance - cost
                        df.loc[df['Ticker'] == ticker, 'Position'] = position + qty
                        TradeBlotter.AppendTradeLog(self,ticker,qty,'B',float(quote))
                        print("Buy " + str(qty) +  " shares of " + ticker + " executed at " + quote)
                        TradeBlotter.ShowAvailableCash(self)
                    else:
                        print("You do not have sufficient balance to buy " + str(qty) + " shares of " + ticker)
                else:
                    print("Price unavailable.. please try later.")

            elif(BuyOrSell=="2"):
                if(position > 0):
                    qty = int(input("Enter the quantity you want to sell max(" + str(position) + "):"))
                    if(qty <= position):
                        quote = float(TradeBlotter.GetQuoteFromYahooFinance(self, ticker,"BID"))
                        if(quote != 0):
                            cash = quote * qty
                            df.loc[df['Ticker'] == 'CASH', 'Position'] = balance + cash
                            df.loc[df['Ticker'] == ticker, 'Position'] = position - qty
                            TradeBlotter.AppendTradeLog(self, ticker, qty, 'S', float(quote))
                            print("Sell " + str(qty) + " shares of " + ticker + " executed at " + str(quote))
                            TradeBlotter.ShowAvailableCash(self)
                        else:
                            print("Price unavailable.. please try later.\n")
                    else:
                        print("The available shares of " + str(position) + " is less that your quantity " + str(qty) + ".\n")

                else:
                    print("You do not have a position in " + ticker + " to sell.\n" )
            else:
                print("Invalid Selection. please try again\n")
                TradeBlotter.MakeTrade(self,df)
        else:
            print("***Invalid ticker selection***.")

    def GetBlotter(self, df):
        if len(dflog) > 0:
            print(dflog)
        else:
            print("No Trades have been posted to your blotter.")


    def GetPL(self,df):
        tickerlist = dflog['Ticker'].tolist()
        tickerlist.append('CASH')
        dfwap = dflog[dflog.Type == 'B'].groupby(["Ticker"]).apply(lambda x: np.average(x.Price, weights=x.Qty))
        dfsell = dflog[dflog.Type == 'S'].groupby(["Ticker"]).apply(lambda x: np.average(x.Price, weights=x.Qty))
        for ticker in dfwap.index:
             df.loc[df['Ticker'] == ticker, 'WAP'] = dfwap.loc[ticker]
             df.loc[df['Ticker'] == ticker, 'UPL'] = 0
             df.loc[df['Ticker'] == ticker, 'RPL'] = 0

        for index, row in df[df['Ticker'].isin(tickerlist)].iterrows():
            bidprice = t.GetQuoteFromYahooFinance(row['Ticker'],"BID")
            if(row['Ticker'].upper() != "CASH"):
                df.loc[df['Ticker'] == row['Ticker'], 'Market'] = round(float(bidprice),3)
            if(row['Position'] > 0):
                position = float(row['Position'])
                wap = float(row['WAP'])
                upl = (float(bidprice)-wap)*position
                df.loc[df['Ticker'] == row['Ticker'], 'UPL'] = upl

            sumofsharessold = dflog[(dflog.Type == 'S') & (dflog.Ticker==row['Ticker'])]["Qty"].sum()
            if (sumofsharessold > 0):
                swap = 0
                for soldticker in dfsell.index:
                    if soldticker == row['Ticker']:
                        swap = float(dfsell.loc[soldticker])
                wap = float(row['WAP'])
                rpl = (swap - wap) * sumofsharessold
                df.loc[df['Ticker'] == row['Ticker'], 'RPL'] = rpl
        return (df)

    def GetUserSelection(self, df):
        quitstatus = 0
        display = "--------------------------------------------------------------"
        selection = input(display + "\nPlease select from the below options\n"+ display + "\nTrade (1)\nShow Blotter (2)\nShow P/L (3)\nQuit (4)\n" )
        try:
            selection = int(selection)
            if(selection == UserOptions.TRADE.value):
                print("You Selected Trade\n")
                TradeBlotter.MakeTrade(self,df)
            elif(selection == UserOptions.SHOWBlOTTER.value):
                print("You selected Blotter\n")
                TradeBlotter.GetBlotter(self,df)
            elif(selection == UserOptions.SHOWPL.value):
                print("you selected P/L\n")
                result = TradeBlotter.GetPL(self,df)
                result = result.fillna(0)
                print(result.to_string(index=False))
            elif(selection == UserOptions.QUIT.value):
                print("You selected Quit\nGoodBye! :)")
                quitstatus = 1
            else:
                print("Invalid selection Option.\n")
        except:
            if (selection.upper() == "TRADE"):
                print("You Selected Trade\n")
            elif (selection.upper().find("BLOTTER") != -1):
                print("You selected Blotter\n")
                TradeBlotter.GetBlotter(self,df)
            elif (selection.upper().find("P/L") != -1 or selection.upper().find("PL") != -1):
                print("you selected P/L\n")
                result = TradeBlotter.GetPL(self,df)
                result = result.fillna(0)
                print(result.to_string(index=False))
            elif (selection.upper().find("QUIT") != -1):
                print("You selected Quit\nGoodBye! :)")
                quitstatus = 1
            else:
                print("Invalid selection Option.\n")
        finally:
            if quitstatus == 0:
                TradeBlotter.GetUserSelection(self, df)
        return

t = TradeBlotter()
df = t.CreateBlotterDataFrame()
dflog = t.CreateTradeLogDataFrame()
print(df)
print(dflog)
t.GetUserSelection(df)