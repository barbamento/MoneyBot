import pandas as pd
import numpy as np
import os
import coinmarketcapapi
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import datetime
from binance import Client

#   TO DO LIST
#       
#       ADD MULTI INDEX
#


class wallet:
    def __init__(self,exchanges,apis,path="./assets"):
        """
        inizialize the wallet:

            assets:
        list of str,
        name of the assets in the wallet

            exchanges:
        list of str,
        name of the exchange used

            path:
        str,
        local storage of assets
        """
        self.path=path
        self.key_inizialization(exchanges,apis)
        self.wallet=self.wallet_inizialitazion()
        if str(datetime.date.today()) not in np.unique(self.wallet["date"].to_list()): 
            self.add_today_binance()
            self.add_today_nexo()
        self.wallet.to_csv(os.path.join(self.path,"wallet.csv"))

    def key_inizialization(self,exchanges,apis):
        self.cmc_key=apis["cmc_key"]
        if "binance" in exchanges:
            self.api_key=apis["api_key"]
            self.api_secret=apis["api_secret"]

    def wallet_creation(self):
        """
        create a new wallet if none are found in the directory
        """
        wallet=pd.DataFrame(columns=["date","paid","cost","not paid","value","location"])
        return wallet

    def wallet_inizialitazion(self):
        """
        create the local wallet as a csv
        """
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        try:
            wallet=pd.read_csv(os.path.join(self.path,"wallet.csv"),index_col=0)
        except:
            wallet=self.wallet_creation()
            wallet.to_csv(os.path.join(self.path,"wallet.csv"))
        return wallet
      
    def binance_data(self):#find a way to secret the keys
        """
        Get data from binance api
        """
        client = Client(self.api_key, self.api_secret)
        df=pd.DataFrame(client.get_account()["balances"])
        df=df.set_index(["asset"])
        df=pd.DataFrame(df.to_numpy().astype(np.float64),columns=df.columns,index=df.index)
        df=df.loc[(df!=0).any(1)]
        return df

    def add_today_binance(self):
        """
        add the daily income to your dataframe.
        This action can change the dataframe only once per day.
        """
        cmc=coinmarketcapapi.CoinMarketCapAPI(self.cmc_key)
        date=datetime.date.today()
        yesterday=date-datetime.timedelta(days=1)
        today_df=self.binance_data()
        if self.wallet.empty:
            wallet=self.wallet
        else:
            wallet=self.wallet[self.wallet["location"=="binance"]]
        temp_df=pd.DataFrame(columns=wallet.columns)
        df=today_df.apply(np.sum,axis=1)
        for asset in today_df.index:
            temp_df.loc[asset,"date"]=date
            try:
                current_value=wallet[wallet["date"]==yesterday].loc[asset,"not paid"]+wallet[wallet["date"]==yesterday].loc[asset,"paid"]
            except:
                current_value=0
            name= asset if asset[:2]!="LD" else asset[2:]
            print(name)
            response=cmc.cryptocurrency_quotes_latest(symbol=name,convert="EUR").__str__().replace("\'", "\"").replace('None','"None"').split("OK: ")[1]
            convertion_rate=json.loads(response)[name]["quote"]["EUR"]["price"]
            temp_df.loc[asset,["not paid","value","location"]]=[df[asset]-current_value,
                                                            (df[asset]-current_value)*convertion_rate ,
                                                            "binance"]
        if date not in np.unique(self.wallet["date"]):
            self.wallet=self.wallet.append(temp_df.fillna(0))
        return temp_df.fillna(0)

    def add_paid_asset(self,asset,quantity,price,date=datetime.date.today(),location="binance"):###old savings
        """
        change the self.wallet saved file following user given instruction.

            asset:
        str, name of the crypto asset

            quantity:
        float, how much asset you bought

            price:
        float, price of the bought asset
        """
        wallet=self.wallet
        numerical_wallet=self.wallet.loc[:,["paid","cost","not paid","value"]].to_numpy()
        index=pd.MultiIndex.from_frame(self.wallet["date"].reset_index())
        wallet=wallet.drop(["date"],axis=1)
        wallet.index=index
        date=str(date)
        today=str(datetime.date.today())
        if date==today:
            wallet.loc[(asset,date),"paid"]=wallet.loc[(asset,date),"paid"]+quantity
            wallet.loc[(asset,date),"cost"]=price
            wallet.loc[(asset,date),"value"]=wallet.loc[(asset,date),"value"]+price
        else:
            raise ValueError ("To be implemented")
        wallet=wallet.reset_index(level="date")
        self.wallet=wallet
        return wallet

    def add_today_nexo(self,interest="nexo"):
        pass


if __name__=="__main__":
    my_wallet=wallet()
    #print(my_wallet.add_paid_asset(asset="BETH",quantity=0.3,price=200))