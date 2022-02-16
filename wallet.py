from calendar import month
from gc import freeze
from inspect import stack
from lib2to3.pgen2.token import PERCENTEQUAL
from platform import release
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
from sklearn.model_selection import LeaveOneGroupOut
import Mtg
from requests.models import codes
from dateutil import relativedelta

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

class nexo2:
    def __init__(self,cmc):
        self.cmc=cmc
        self.name="nexo"
        self.path="nexo"
        self.methon="coin"
        self.terms=self.load_terms()

    def load_terms(self):
        try:
            df=pd.read_csv(os.path.join(self.path,"nexo_terms.csv"),index_col=[0,1,2])
        except:
            df=pd.DataFrame(columns=["asset","term","nexo_tokens","percentage"])
            df=df.set_index(["asset","term","nexo_tokens"])
        df=df.sort_index(level=0)
        df.to_csv(os.path.join(self.path,"nexo_terms.csv"))
        return df


class nexo:
    def __init__(self,cmc):
        self.name="nexo"
        self.path="nexo"
        self.cmc=cmc
        self.method="coin"
        self.stacks=self.load_stacking()
        self.wallet=self.wallet_inizialitazion()
        print(self.wallet)
        if str(datetime.date.today()) not in self.wallet.index.get_level_values("date").to_list():
            self.add_today_wallet()
            exit()
            self.wallet.to_csv(os.path.join(self.path,"nexo.csv"))
        print(self.wallet)
        
    def add_today_wallet(self):
        today_wallet=pd.DataFrame(columns=["asset","date","location","stacked","free","value"])
        today_wallet=today_wallet.set_index(["asset","date","location"]).sort_index(level=0)
        today=str(datetime.date.today())
        '''
        add stacks to today_wallet. It adds locked value and indexes
        '''
        for asset,location,release_day in self.stacks.index:
            ammount,interest_type,accrued=self.stacks.loc[(asset,location,release_day),:]
            if (asset,today,"nexo") in today_wallet.index:
                stacked,free,value=today_wallet.loc[(asset,today,"nexo"),:]
                price=value/(stacked+free)
                stacked+=ammount
                today_wallet.loc[(asset,today,"nexo"),:]=[stacked,free,(stacked+free)*price]
            else:
                response=self.cmc.cryptocurrency_quotes_latest(symbol=asset,convert="EUR").__str__().replace("\'", "\"").replace('None','"None"').split("OK: ")[1]
                price=json.loads(response)[asset]["quote"]["EUR"]["price"]
                today_wallet.loc[(asset,today,"nexo"),:]=[ammount,0,price*ammount]
        """
        add free coins to today_wallet. It adds free value and indexes
        """
        yesterday=str(datetime.date.today()-datetime.timedelta(days=1))
        for ind in self.wallet.index:
            ind=list(ind)
            self.wallet=self.wallet.sort_index(level=0)
            if ind[1]==yesterday:
                yesterday_info=self.wallet.loc[tuple(ind),:]
                asset=ind[0]
                if (asset,today,"nexo") in today_wallet.index:
                    stacked,free,value=today_wallet.loc[(asset,today,"nexo"),:]
                    price=value/(stacked+free)
                    free+=ammount
                    free=yesterday_info[1]
                    today_wallet.loc[(asset,today,"nexo"),:]=[stacked,free,(stacked+free)*price]
                else:
                    response=self.cmc.cryptocurrency_quotes_latest(symbol=asset,convert="EUR").__str__().replace("\'", "\"").replace('None','"None"').split("OK: ")[1]
                    price=json.loads(response)[asset]["quote"]["EUR"]["price"]
                    today_wallet.loc[(asset,today,"nexo"),:]=[0,yesterday_info[1],yesterday_info[1]*price]
        print(today_wallet)
        print(self.wallet)
        '''
        add interest to today wallet
        '''
        #nexo_type=self.nexo_percentage(today_wallet)
        nexo_type="GOLD"
        for ind in today_wallet.index:#it add flex interest
            print(ind)
            asset=list(ind)[0]
            free=today_wallet.loc[ind,"free"] 
            free+=self.interest(asset,"FLEX",free,nexo_type,method=self.method)
            today_wallet.loc[ind,"free"]=free
        for ind in self.stacks.index:#add accrued term interest
            stack_type=self.stacks.loc[ind,"type"]
            if stack_type=="LOCK1":
                days=30
            elif stack_type=="LOCK3":
                days=90
            elif stack_type=="LOCK12":
                days=365
            else:
                raise ValueError ("Problems in nexo_stack.csv.\ncheck {} for {}".format(stack_type,ind))
            asset=list(ind)[0]
            accrued=self.stacks.loc[ind,"accrued"]
            stacked=self.stacks.loc[ind,"stacked"]
            accrued+=self.interest(asset,stack_type,stacked,nexo_type,method=self.method)*days
            if list(ind)[2]!=str(datetime.date.today()+relativedelta(months=1)) and stack_type=="LOCK1":
                pass
            elif list(ind)[2]!=str(datetime.date.today()+relativedelta(months=3)) and stack_type=="LOCK3":
                pass
            elif list(ind)[2]!=str(datetime.date.today()+datetime.timedelta(days=365)) and stack_type=="LOCK12":
                pass
            else:
                self.stacks.loc[ind,"accrued"]=accrued
            if list(ind)[2]==today:
                print("The stacking preiod of {} is finished. You earned {} {}".format(asset,accrued,self.method))
                today_wallet.loc[(asset,today,"nexo"),"stacked"]+=accrued   
        print(today_wallet)     
        #self.wallet=pd.concat([self.wallet,today_wallet]).sort_index(level=0)

    def nexo_percentage(self,wallet):
        today=str(datetime.date.today())
        total_value=wallet.sort_index(level=0).reset_index(level=["asset","location"]).loc[today,"value"].sum()
        nexo_value=wallet.loc[("NEXO",today,"nexo"),"value"]
        print("nexo value : {}\ntotal value : {}".format(nexo_value,total_value))
        if nexo_value/total_value<0.01:
            return "BASE"
        elif nexo_value/total_value<0.05:
            return "SILVER"
        elif nexo_value/total_value<0.1:
            return "GOLD"
        else:
            return "PLATINUM"

    def interest(self,asset,term,quantity,nexo_term,method="nexo"):
        percentage=self.terms().loc[(asset,term,nexo_term),"percentage"]
        if method=="nexo":
            interest=quantity*percentage/100
        else:
            if term=="LOCK1":
                print("a")
                days=30
            elif term=="LOCK3":
                days=120
            elif term in ["LOCK12"]:
                days=365
            elif term=="FLEX":
                days=1
            interest=quantity*((1+percentage/100)**((days)/365)-1)/(days)
        if asset in ["USDT","USDC"]:
            return round(interest,6)
        else:
            return round(interest,8)

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

    def terms(self):
        try:
            df=pd.read_csv(os.path.join(self.path,"nexo_terms.csv"),index_col=[0,1,2])
        except:
            df=pd.DataFrame(columns=["asset","term","nexo_tokens","percentage"])
            df=df.set_index(["asset","term","nexo_tokens"])
        df=df.sort_index(level=0)
        df.to_csv(os.path.join(self.path,"nexo_terms.csv"))
        return df

    def add_term(self,asset,term,percentage,nexo_tokens):
        df=self.terms()
        df.loc[(asset,term,nexo_tokens),:]=[percentage]
        df=df.sort_index(level=0)
        df.to_csv(os.path.join(self.path,"nexo_terms.csv"))
        return df

    def stack_creation(self):
        """
        create a new wallet if none are found in the directory
        """
        wallet=pd.DataFrame(columns=["asset","location","release day","stacked","type","accrued"])
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
        print(self.wallet)
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
        self.stacks.loc[(asset,"nexo",finish_stacking),:]=[stacked_ammount,stack_type,0]
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
        wallets=[]
        if "binance" in exchanges:
            self.bin=binance(apis["api_secret"],apis["api_key"],self.cmc)
            wallets+=[self.bin.binwallet.sort_index(level=0)]
        if "nexo" in exchanges:
            self.nexo=nexo(self.cmc)
            wallets+=[self.nexo.wallet.sort_index(level=0)]
        self.wallet=pd.concat(wallets).sort_index(level=0)
        #print(self.wallet)
        #print(self.nexo.interest("USDT","FLEX",299.384603-0.070677,"GOLD",method="coin"))

    def visualize_progress(self,asset):
        self.wallet.loc[asset,"value"]
        
        

        

def read_secrets():
    paths=[f for f in os.listdir("./secrets") if f[-4:]==".txt"]
    api=[]
    for f in paths:
        with open(os.path.join("./secrets/",f), "r") as text_file:
            api.append(text_file.read())
    return dict(zip([f[:-4] for f in paths],api))

if __name__=="__main__":
    #print(pd.show_versions())
    print()
    my_wallet=wallet(["binance","nexo"],read_secrets())
    
    
    if False:
        my_wallet.nexo.add_term("BTC","LOCK1",5.5,"GOLD")
        my_wallet.nexo.add_term("BTC","FLEX",4.5,"GOLD")
        my_wallet.nexo.add_term("NEXO","FLEX",7,"GOLD")
        my_wallet.nexo.add_term("NEXO","LOCK3",9,"GOLD")
        my_wallet.nexo.add_term("NEXO","LOCK12",12,"GOLD")
        my_wallet.nexo.add_term("DOT","LOCK1",12,"GOLD")
        my_wallet.nexo.add_term("DOT","FLEX",11,"GOLD")
        my_wallet.nexo.add_term("DOGE","FLEX",0.5,"GOLD")
        my_wallet.nexo.add_term("USDP","FLEX",9,"GOLD")
        my_wallet.nexo.add_term("USDT","FLEX",9,"GOLD")
        my_wallet.nexo.add_term("USDC","FLEX",9,"GOLD")