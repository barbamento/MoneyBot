from gc import freeze
from inspect import stack
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
import Mtg
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
        date=datetime.date.today()
        if str(date) not in self.binwallet.index.get_level_values("date").to_list():
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
        result=result.sort_index(level=0)
        for i in assets:
            print(i)
            if i in locked.index:
                v1=locked.loc[i]
            else:
                v1=0
            if i in free.index:
                v2=free.loc[i]   
            else:
                v2=0
            result.loc[(i,str(datetime.date.today()),"binance")]=[v1+v2]
            result=result.sort_index(level=0)
        return result.dropna()

    def add_today_binance(self):
        """
        add the daily income to your dataframe.
        This action can change the dataframe only once per day.
        """
        
        date=datetime.date.today()
        today_df=self.binance_data()
        prices=[]
        stacked=[]
        for asset in today_df.index:
            locked_value=0
            response=self.cmc.cryptocurrency_quotes_latest(symbol=asset[0],convert="EUR").__str__().replace("\'", "\"").replace('None','"None"').split("OK: ")[1]
            prices+=[json.loads(response)[asset[0]]["quote"]["EUR"]["price"]]
            stacked+=[locked_value]
        today_df["stacked"]=np.array(stacked)
        today_df["value"]=(np.array(today_df["free"].to_list()).astype(float)+np.array(stacked))*np.array(prices).astype(float)
        for ind in self.stacks.index:
            asset=ind[0]
            if asset in today_df.index:
                free,stacked,value=today_df.loc[(asset,str(date),"binance"),:]
                price=value/(free+stacked)
                stacked+=self.stacks.loc[ind,"stacked"]
                value=(free+stacked)*price
                today_df.loc[(asset,str(date),"binance"),:]=[free,stacked,value]
        self.binwallet=pd.concat([self.binwallet,today_df])
        return today_df

    def add_locked_stacking(self,asset,stacked_ammount,finish_stacking=None,lenght_stacking=None):
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
                    wallet=wallet.drop(i)
        except:
            wallet=self.stack_creation()
            wallet.to_csv(os.path.join(self.path,"binance_stack.csv"))
        return wallet
             
class nexo:
    def __init__(self,cmc):
        self.name="nexo"
        self.path="nexo"
        self.cmc=cmc
        self.stacks=self.load_stacking()
        self.add_today_wallet()

    def nexo_situation(self):
        pass

    def add_today_wallet(self):#rimetti a posto perchè domani non worka più
        '''
        1.load stacks
        2.load wallet
        3.load conditions
        4.use condition to calculate todays intrest
        5.return wallet+intrest        
        '''
        self.wallet=self.wallet_inizialitazion()
        yesterday_index=[list(i) for i in self.wallet.index.to_list()]
        for ind in yesterday_index:
            stacked,free=self.wallet.loc[tuple(ind),["stacked","free"]]
            response=self.cmc.cryptocurrency_quotes_latest(symbol=ind[0],convert="EUR").__str__().replace("\'", "\"").replace('None','"None"').split("OK: ")[1]
            price=json.loads(response)[ind[0]]["quote"]["EUR"]["price"]
            ind[3:6]=[stacked,free,(stacked+free)*price]
            ind[1]=str(datetime.date.today())
        today_wallet=pd.DataFrame(yesterday_index,columns=["asset","date","location","stacked","free","value"])
        today_wallet=today_wallet.set_index(["asset","date","location"]).sort_index(level=0)        
        self.wallet=pd.concat([self.wallet,today_wallet])
        self.wallet.to_csv(os.path.join(self.path,"nexo.csv")) 
        return today_wallet

    def wallet_inizialitazion(self):
        """
        create the local wallet as a csv
        """
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        try:
            wallet=pd.read_csv(os.path.join(self.path,"nexo.csv"),index_col=[0,1,2])
        except:
            wallet=pd.DataFrame(columns=["asset","date","location","stacked","free","value"])
            wallet=wallet.set_index(["asset","date","location"])
        wallet.sort_index(level=0)
        wallet.to_csv(os.path.join(self.path,"nexo.csv"))   
        return wallet

    def conditions(self):
        try:
            df=pd.read_csv(os.path.join(self.path,"nexo_terms.csv"),index_col=[0,1])
        except:
            df=pd.DataFrame(columns=["asset","term","percentage","nexo_tokens"])
            df=df.set_index(["asset","term"])
        df=df.sort_index(level=0)
        df.to_csv(os.path.join(self.path,"nexo_terms.csv"))
        return df

    def add_condition(self,asset,term,percentage,nexo_tokens):
        df=self.conditions()
        df.loc[(asset,term),:]=[percentage,nexo_tokens]
        df=df.sort_index(level=0)
        df.to_csv(os.path.join(self.path,"nexo_terms.csv"))
        return df

    def stack_creation(self):
        """
        create a new wallet if none are found in the directory
        """
        wallet=pd.DataFrame(columns=["asset","location","release day","stacked","type"])
        wallet=wallet.set_index(["asset","location","release day"])
        wallet=wallet.sort_index(level=0)
        return wallet

    def load_stacking(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        try:
            wallet=pd.read_csv(os.path.join(self.path,"nexo_stack.csv"),index_col=[0,1,2])
            if datetime.date.today() in np.array(wallet.index.to_list())[:,2]:
                to_remove=[i for i in wallet.index if str(datetime.date.today()) in i[2]]
                for i in to_remove:
                    wallet.drop(i)
        except:
            wallet=self.stack_creation()
            wallet.to_csv(os.path.join(self.path,"nexo_stack.csv"))
        return wallet

    def add_coin(self,asset,added_ammount):
        today=str(datetime.date.today())
        add_index=(asset,today,"nexo")
        if (asset,today,"nexo") in self.wallet.index:
            stack,free,old_value=self.wallet.loc[add_index]
            price=old_value/(free+stack)
            free=free+added_ammount
            value=(free+stack)*price
        else:
            response=self.cmc.cryptocurrency_quotes_latest(symbol=asset,convert="EUR").__str__().replace("\'", "\"").replace('None','"None"').split("OK: ")[1]
            price=json.loads(response)[asset]["quote"]["EUR"]["price"]
            stack=0
            free=added_ammount
            value=free*price
        self.wallet.loc[add_index,:]=[stack,free,value]
        self.wallet=self.wallet.sort_index(level=0)
        self.wallet.to_csv(os.path.join(self.path,"nexo.csv"))
        return self.wallet

    def add_locked_stacking(self,asset,stacked_ammount,finish_stacking=None,lenght_stacking=None):
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
        if lenght_stacking>=120:
            stack_type="LOCK12"
        elif lenght_stacking>=30:
            stack_type="LOCK3"
        else:
            stack_type="LOCK1"
        self.stacks.loc[(asset,"nexo",finish_stacking),:]=[stacked_ammount,stack_type]
        self.stacks.to_csv(os.path.join(self.path,"nexo_stack.csv"))
        return self.wallet,self.stacks


class crypto:
    def __init__(self):
        self.name="crypto"
        self.path="./crypto"

class wallet:
    def __init__(self,exchanges,apis,path="assets"):
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
        self.cmc=coinmarketcapapi.CoinMarketCapAPI(apis["cmc_key"])
        if "binance" in exchanges:
            self.bin=binance(apis["api_secret"],apis["api_key"],self.cmc)
            print(self.bin.binwallet)
        if "nexo" in exchanges:
            self.nexo=nexo(self.cmc)
            print(self.nexo.wallet)

        

def read_secrets():
    paths=[f for f in os.listdir("./secrets") if f[-4:]==".txt"]
    api=[]
    for f in paths:
        with open(os.path.join("./secrets/",f), "r") as text_file:
            api.append(text_file.read())
    return dict(zip([f[:-4] for f in paths],api))

if __name__=="__main__":
    #print(pd.show_versions())
    my_wallet=wallet(["binance","nexo"],read_secrets())