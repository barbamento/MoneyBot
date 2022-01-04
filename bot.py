import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from Barbagram.barbagram import keyboard,telegram,message,button
from wallet import wallet
import os
import sys

class bot():
    def __init__(self,exchanges):
        self.secrets=self.read_secrets()
        wallet(["binance"],apis=self.secrets)#toglilo ed inizializza tutto ogni giorno
        self.bot=telegram(self.secrets["TOKEN"])
        #self.bot.setCommands([])
        self.bot.start_bot(self.bot_corpus)

    def read_secrets(self):
        """
        read all the tokens and apy key located in the secrets folder.
        Every api needs to be in a separate txt file and with some name rules:

        Mandatory:

            TOKEN       telegram token
            cmc_key     coinmarketcap key

        Optional:
            
            api_secret  secret api key from binance
            api_key     api key from binance

        Returns:
            Dict,
        contains all the secret key.
        """
        paths=[f for f in os.listdir("./secrets") if f[-4:]==".txt"]
        api=[]
        for f in paths:
            with open(os.path.join("./secrets/",f), "r") as text_file:
                api.append(text_file.read())
        return dict(zip([f[:-4] for f in paths],api))

    def bot_corpus(self,message):#switch to comands
        if message.text.lower()=="prova":
            reply_markup=[self.bot.InlineMarkupButton(text="prova0",callback_data="0"),self.bot.InlineMarkupButton(text="prova1",callback_data="1")]
            print(self.bot.sendMessage(chat_id=message.chat_id,text=message.text,reply_markup=reply_markup).json())
        elif message.text=="start":
            self.program(message)
        elif message.text=="exit":
            sys.exit()
        else:
            print(self.bot.sendMessage(chat_id=message.chat_id,text="welo").json())

    def program(self,message):
        buttons=["prova0","prova1","prova2","prova3"]
        kb=keyboard(buttons)
        print(kb.keyboard)
        kb=kb.to_inline()
        print(kb)
        print(self.bot.sendMessage(chat_id=message.chat_id,text="welo",reply_markup=kb).json())


if __name__=="__main__":
    bot(exchanges=["binance"])