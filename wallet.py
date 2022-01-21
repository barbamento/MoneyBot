from tracemalloc import start
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
#
#       ADD SUPPORT MULTIWALLET FOR CRYPTO

class binance:
    def __init__(self,secret,key,cmc,path="./binance/"):
        self.cmc=cmc
        self.api_key=key
        self.api_secret=secret
        self.client = Client(key, secret)
        self.path=path
        self.name="binance"
        self.stacks=self.load_stacking()
        self.binwallet=self.wallet_inizialitazion()
        self.add_today_binance()
        self.binwallet.to_csv(os.path.join(self.path,"binance.csv"))

    def wallet_creation(self):
        """
        create a new wallet if none are found in the directory
        """
        wallet=pd.DataFrame(columns=["asset","date","location","stacked","free","value"])
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
            wallet=pd.read_csv(os.path.join(self.path,"binance.csv"),index_col=[0,1,2])
        except:
            wallet=self.wallet_creation()
            wallet.to_csv(os.path.join(self.path,"binance.csv"))
        return wallet
      
    def binance_data(self):
        """
        Get data from binance api

            return:
        pd.Dataframe, with multiindex ["asset","date"] and a single entries called ["free"].
        """
        df=pd.DataFrame(self.client.get_account()["balances"]).astype({"asset":str,"free":float,"locked":float})
        df=df.set_index("asset")
        df=df.loc[(df!=0).any(1)]
        locked=df[df.index.str[:2]=="LD"].apply(sum,axis=1)
        locked.index=locked.index.str[2:]
        free=df[df.index.str[:2]!="LD"].apply(sum,axis=1)
        assets=list(set(locked.index).union(set(free.index)))
        index=pd.MultiIndex.from_arrays([assets,[datetime.date.today()]*len(assets),["binance"]*len(assets)],names=["asset","date","location"])
        result=pd.DataFrame(columns=["free"],index=index)
        #result.sort_index()
        for i in assets:
            if i in locked.index:
                v1=locked.loc[i]
            else:
                v1=0
            if i in free.index:
                v2=free.loc[i]   
            else:
                v2=0
            result=result.sort_index(level=0)
            result.loc[(i,str(datetime.date.today()),"binance"),"free"]=v1+v2#performance error here
        return result

    def add_today_binance(self):#add locking stacking, maybe with external function
        """
        add the daily income to your dataframe.
        This action can change the dataframe only once per day.
        """
        
        date=datetime.date.today()
        today_df=self.binance_data()
        prices=[]
        stacked=[]
        for asset in today_df.index:
            if ("asset",str(date-datetime.timedelta(days=1)),"binance") in self.binwallet.index:
                locked_value=self.binwallet.loc[("asset",str(date-datetime.timedelta(days=1)),"binance"),"stacked"]
            else:
                locked_value=0
            response=self.cmc.cryptocurrency_quotes_latest(symbol=asset[0],convert="EUR").__str__().replace("\'", "\"").replace('None','"None"').split("OK: ")[1]
            prices+=[json.loads(response)[asset[0]]["quote"]["EUR"]["price"]]
            stacked+=[locked_value]
        today_df["stacked"]=np.array(stacked)
        today_df["value"]=(np.array(today_df["free"].to_list()).astype(float)+np.array(stacked))*np.array(prices).astype(float)
        if str(date) not in self.binwallet.index.get_level_values("date").to_list():
            self.binwallet=self.binwallet.append(today_df)
        return today_df

    def add_locked_stacking(self,asset,stacked_ammount,finish_stacking=None,lenght_stacking=None):
        print(self.binwallet)
        if finish_stacking==None and isinstance(lenght_stacking,int):
            finish_stacking=datetime.date.today()+datetime.timedelta(days=lenght_stacking)
        else:
            if "-" in finish_stacking:
                finish_stacking=finish_stacking.split("-")
            elif "/" in finish_stacking:
                finish_stacking=finish_stacking.split("/")
            else:
                raise ValueError ("Wrong date format")
            finish_stacking=[int(i) for i in finish_stacking]
            finish_stacking=datetime.date(finish_stacking[0],finish_stacking[1],finish_stacking[2])
            lenght_stacking=finish_stacking-datetime.date.today()
            lenght_stacking=lenght_stacking.days
        self.stacks.loc[(asset,"binance",finish_stacking),:]=stacked_ammount
        self.binwallet=self.binwallet.sort_index(level=0)
        row=self.binwallet.loc[(asset,str(datetime.date.today()),"binance")].to_list()
        row[0]+=stacked_ammount
        price=row[2]/row[1]
        row[2]=(row[0]+row[1])*price
        self.binwallet.loc[(asset,str(datetime.date.today()),"binance")]=row
        self.stacks.to_csv(os.path.join(self.path,"binance_stack.csv"))
        self.binwallet.to_csv(os.path.join(self.path,"binance.csv"))
        return self.binwallet,self.stacks

    def stack_creation(self):
        """
        create a new wallet if none are found in the directory
        """
        wallet=pd.DataFrame(columns=["asset","location","release day","stacked"])
        wallet=wallet.set_index(["asset","location","release day"])
        wallet=wallet.sort_index(level=0)
        return wallet

    def load_stacking(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        try:
            wallet=pd.read_csv(os.path.join(self.path,"binance_stack.csv"),index_col=[0,1,2])
            if datetime.date.today() in np.array(wallet.index.to_list())[:,2]:
                to_remove=[i for i in wallet.index if str(datetime.date.today()) in i[2]]
                for i in to_remove:
                    wallet.drop(i)
        except:
            wallet=self.stack_creation()
            wallet.to_csv(os.path.join(self.path,"binance_stack.csv"))
        return wallet
             
class nexo:
    def __init__(self):
        self.name="nexo"
        self.path="./nexo"

class crypto:
    def __init__(self):
        self.name="crypto"
        self.path="./crypto"

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
        self.cmc=coinmarketcapapi.CoinMarketCapAPI(self.cmc_key)
        if "binance" in exchanges:
            self.bin=binance(apis["api_secret"],apis["api_key"],self.cmc)
       
        exit()
        self.wallet=self.wallet_inizialitazion()
        #if str(datetime.date.today()) not in np.unique(self.wallet["date"].to_list()):
        if False:
            if "binance" in exchanges:
                self.add_today_binance()
            if "nexo" in exchanges:
                self.add_today_nexo()
        print(self.wallet)
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
            wallet=pd.read_csv(os.path.join(self.path,"wallet.csv"),index_col=[0,1,2])
        except:
            wallet=self.wallet_creation()
            wallet.to_csv(os.path.join(self.path,"wallet.csv"))
        return wallet
      
    def binance_data(self):
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
        return result

    def add_today_binance(self):#add locking stacking, maybe with external function
        """
        add the daily income to your dataframe.
        This action can change the dataframe only once per day.
        """
        date=datetime.date.today()
        today_df=self.binance_data()
        temp_df=pd.DataFrame(columns=self.wallet.columns,index=today_df.index)
        prices=[]
        for asset in today_df.index:
            response=self.cmc.cryptocurrency_quotes_latest(symbol=asset[0],convert="EUR").__str__().replace("\'", "\"").replace('None','"None"').split("OK: ")[1]
            prices+=[json.loads(response)[asset[0]]["quote"]["EUR"]["price"]]
        today_df["value"]=np.array(today_df["ammount"].to_list()).astype(float)*np.array(prices).astype(float)
        if str(date) not in self.wallet.index.get_level_values("date").to_list():
            self.wallet=self.wallet.append(today_df)
        return temp_df

    def add_today_nexo(self):
        date=str(datetime.date.today())
        #date=str(datetime.date.today()-datetime.timedelta(days=1))
        wallet=self.wallet.xs((date,"nexo"),level=("date","location"))
        print(wallet)
        

    def nexo_data(self):
        yesterday=str(datetime.date.today()-datetime.timedelta(days=1))
        wallet=self.wallet.xs("nexo",level="location")
        print(wallet.index.get_level_values(level="date"))
        if yesterday in wallet.index.get_level_values(level="date"):
            self.add_today_nexo()


    def add_paid_asset(self,asset,quantity,price,location="binance"):###old savings
        """
        change the self.wallet saved file following user given instruction.

            asset:
        str, name of the crypto asset

            quantity:
        float, how much asset you bought

            price:
        float, price of the bought asset
        """
        today=str(datetime.date.today())
        exist_today=(asset,today,location) in self.wallet.index.to_list()
        if not exist_today:
            response=self.cmc.cryptocurrency_quotes_latest(symbol=asset,convert="EUR").__str__().replace("\'", "\"").replace('None','"None"').split("OK: ")[1]
            price=json.loads(response)[asset]["quote"]["EUR"]["price"]
            wallet=pd.DataFrame([[asset,today,location,quantity,quantity*price]],columns=["asset","date","location","ammount","value"])
            wallet=wallet.set_index(["asset","date","location"])
            self.wallet=self.wallet.append(wallet)
        else:
            response=self.cmc.cryptocurrency_quotes_latest(symbol=asset,convert="EUR").__str__().replace("\'", "\"").replace('None','"None"').split("OK: ")[1]
            price=json.loads(response)[asset]["quote"]["EUR"]["price"]
            self.wallet.loc[(asset,today,location),:]+=[quantity,quantity*price]
        return self.wallet

    def check_missing_days(self,exchange):
        if False:
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
        else:
            pass

def read_secrets():
    paths=[f for f in os.listdir("./secrets") if f[-4:]==".txt"]
    api=[]
    for f in paths:
        with open(os.path.join("./secrets/",f), "r") as text_file:
            api.append(text_file.read())
    return dict(zip([f[:-4] for f in paths],api))

if __name__=="__main__":
    my_wallet=wallet(["binance","nexo"],read_secrets())
    my_wallet.add_paid_asset(asset="BTC",quantity=0.2,price=1000,location="nexo")
    #my_wallet.add_paid_asset(asset="ADA",quantity=0.2,price=1000,location="binance")
    my_wallet.add_today_nexo()
    #print(my_wallet.add_paid_asset(asset="BETH",quantity=0.3,price=200))