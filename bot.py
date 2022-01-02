import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from Barbagram.barbagram import telegram
from wallet import wallet
import os

class bot():
    def __init__(self,exchanges):
        self.secrets=self.read_secrets()
        self.wallet=wallet(["binance"],apis=self.secrets)
        self.bot=telegram(self.secrets["TOKEN"])
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

    def bot_corpus(self,arg):
        if arg["result"][0]["message"]["text"]=="send_wallet":
            print(self.wallet.wallet)

if __name__=="__main__":
    bot(exchanges=["binance"])