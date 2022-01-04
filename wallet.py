import pandas as pd
import numpy as np
import os
import coinmarketcapapi
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import datetime
from binance import Client
from requests.models import codes

#   TO DO LIST
#       
#       ADD MULTI INDEX
#
#       ADD SUPPORT MULTIWALLET FOR CRYPTO

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
        #if str(datetime.date.today()) not in np.unique(self.wallet["date"].to_list()):
        if True:
            if "binance" in exchanges:
                self.add_today_binance()
            if "nexo" in exchanges:
                self.add_today_nexo()
        #self.check_missing_days("binance")
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
        wallet=pd.DataFrame(columns=["asset","date","location","ammount","value"])
        wallet=wallet.set_index(["asset","date","location"])
        wallet=wallet.sort_index()
        return wallet

    def wallet_inizialitazion(self):
        """
        create the local wallet as a csv
        """
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        try:
            wallet=pd.read_csv(os.path.join(self.path,"wallet.csv"),index_col=[0,2])
        except:
            wallet=self.wallet_creation()
            wallet.to_csv(os.path.join(self.path,"wallet.csv"))
        return wallet
      
    def binance_data(self):#add locking stacking, maybe with external function
        """
        Get data from binance api

            return:
        pd.Dataframe, with multiindex ["asset","date"] and a single entries called ["ammount"].
        """
        client = Client(self.api_key, self.api_secret)
        df=pd.DataFrame(client.get_account()["balances"]).astype({"asset":str,"free":float,"locked":float})
        df=df.set_index("asset")
        df=df.loc[(df!=0).any(1)]
        locked=df[df.index.str[:2]=="LD"].apply(sum,axis=1)
        locked.index=locked.index.str[2:]
        free=df[df.index.str[:2]!="LD"].apply(sum,axis=1)
        assets=list(set(locked.index).union(set(free.index)))
        index=pd.MultiIndex.from_arrays([assets,[datetime.date.today()]*len(assets),["binance"]*len(assets)],names=["asset","date","location"])
        result=pd.DataFrame(columns=["ammount"],index=index)
        for i in assets:
            if i in locked.index:
                v1=locked.loc[i]
            else:
                v1=0
            if i in free.index:
                v2=free.loc[i]   
            else:
                v2=0
            result.loc[(i,str(datetime.date.today()),"binance"),"ammount"]=v1+v2#performance error here
        result.sort_index()
        return result

    def add_today_binance(self):
        """
        add the daily income to your dataframe.
        This action can change the dataframe only once per day.
        """
        cmc=coinmarketcapapi.CoinMarketCapAPI(self.cmc_key)
        date=datetime.date.today()
        today_df=self.binance_data()
        temp_df=pd.DataFrame(columns=self.wallet.columns,index=today_df.index)
        temp_df.sort_index()
        prices=[]
        for asset in today_df.index:
            response=cmc.cryptocurrency_quotes_latest(symbol=asset[0],convert="EUR").__str__().replace("\'", "\"").replace('None','"None"').split("OK: ")[1]
            prices+=[json.loads(response)[asset[0]]["quote"]["EUR"]["price"]]
        today_df["value"]=np.array(today_df["ammount"].to_list())*np.array(prices)
        print(self.wallet.index.to_list())
        if str(date) not in np.unique(self.wallet.index.to_list()):
            self.wallet=self.wallet.append(today_df)
        return temp_df

    def check_missing_days(self,exchange):
        wallet=self.wallet[self.wallet["location"]==exchange]
        for asset in np.unique(wallet.index.to_list()):
            if len(wallet.loc[asset,:]["date"])>=2 and not isinstance(wallet.loc[asset,:]["date"],str):
                d0=wallet.loc[asset,:]["date"].to_list()[-2].split("-")
                d0=[int(i) for i in d0]
                d0=datetime.date(d0[0],d0[1],d0[2])
                d1=wallet.loc[asset,:]["date"][-1].split("-")
                d1=[int(i) for i in d1]
                d1=datetime.date(d1[0],d1[1],d1[2])
                interval=d1-d0
                interval=interval.days
                if interval>=2:
                    for i in range(interval-1):
                        date=d0+datetime.timedelta(days=i)


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
        wallet=self.to_multindex(self.wallet)
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