# coding: UTF-8
#バックテストコードnote用

import hashlib
import hmac
import requests
import datetime
import json
from pprint import pprint
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


#-----------------------------------------------------------------
# cryptowatchから終値を取り出す
def get_price_data():
    response = requests.get("https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc",params = { "periods" : period ,"after" : 1})
    response = response.json()
    close_data = []
    global l
    l= len(response["result"][str(period)])
    for i in range(l):
        close_data.append(response["result"][str(period)][i][4])
    arr = np.array(close_data)
    return pd.Series(arr)

#--------------------------------------------------------------------
#テクニカル指標実装系関数

#EMA
#EMA_periodは期間、nはろうそく何本分前の値か
def EMA(EMA_period,n):
    EMA_data = []
    for i in range(2*EMA_period):
        EMA_data.insert(0,close[data_n-1-i])
    if n == 0:
        arr = np.array(EMA_data)[-EMA_period:]
    else:
        arr = np.array(EMA_data)[-n-EMA_period:-n]
    EMA = pd.Series(arr).ewm(span=EMA_period).mean()

    return EMA[EMA_period-1]

#MACD
#a=短期EMA_period,b=長期EMA_period,s=シグナル期間
def MACD_and_signal(a,b,s):
    MACD = []
    for i in range(a):
        MACD.insert(0,EMA(a,i)-EMA(b,i))
    arr = np.array(MACD)[-s-1:]
    Signal = pd.Series(arr).rolling(s).mean()

    return MACD,Signal

#ATR
#nは期間、n=14が普通
def ATR(n):
    data = []
    for i in range(2*n-1):
        p1 = response[data_n-i-1][2]-response[data_n-i-1][3] #当日高値-当日安値
        p2 = response[data_n-i-1][2]-response[data_n-i-2][4] #当日高値-前日終値
        p3 = response[data_n-i-1][3]-response[data_n-i-2][4] #当日安値-前日終値
        tr = max(abs(p1),abs(p2),abs(p3))
        data.insert(0,tr)
    arr = np.array(data)[-n:]
    ATR = pd.Series(arr).ewm(span=n).mean()
    return ATR[n-1]


#RSI
#pは期間
def RSI(p):
    RSI_period = p
    diff = close.diff(1)
    positive = diff.clip_lower(0).ewm(alpha=1.0/RSI_period).mean()
    negative = diff.clip_upper(0).ewm(alpha=1.0/RSI_period).mean()
    RSI = 100-100/(1-positive/negative)
    return RSI

#BB
#pは期間,nは偏差の倍率
def BB(p,n):
    Bands_period = p
    Deviation = n
    Base = close.rolling(Bands_period).mean()
    sigma = close.rolling(Bands_period).std(ddof=0)
    Upper = Base+sigma*Deviation
    Lower = Base-sigma*Deviation
    return Base[data_n-1],Upper[data_n-1],Lower[data_n-1]

def engulfing_bar_sell():
    if response[data_n-1][2]>response[data_n-2][2] and response[data_n-1][3]<response[data_n-2][3] and response[data_n-1][4] < (response[data_n-1][2]+2*response[data_n-1][3])/3:
        return True
    else:return False

def engulfing_bar_buy():
    if response[data_n-1][3]<response[data_n-2][3] and response[data_n-1][2]>response[data_n-2][2] and response[data_n-1][4] > (2*response[data_n-1][2]+response[data_n-1][3])/3:
        return True
    else:return False
#--------------------------------------------------------------------
# 戦略

#RSIとMACDによる売りサイン
def buy_signal():
    count3 = count4 = 0
    MACD_sell_sign = RSI_sell_sign = 0

    for i in range(7):
        if RSI(14)[data_n-3-i]>80 and RSI(14)[data_n-2-i]>80 and RSI(14)[data_n-1-i]<=80:
            count3 += 1
        if RSI(14)[data_n-3-i]>70 and RSI(14)[data_n-2-i]>70 and RSI(14)[data_n-1-i]<=70:
            count4 += 1

    if count3 > 0:
        RSI_sell_sign = 0.5
    elif count4 > 0:
        RSI_sell_sign = 0.3

    MACD,Signal = MACD_and_signal(12,26,9)

    if MACD[9] > MACD[10] and MACD[10] > MACD[11] and MACD[11] > 0:
        MACD_sell_sign = 0.5
    elif MACD[9] > MACD[10] and MACD[10] > MACD[11]:
        MACD_sell_sign = 0.3


    if RSI_sell_sign + MACD_sell_sign > 0.7:
        return True
    else: return False

#RSIとMACDによる買いサイン
def sell_signal():
    count1 = count2 = 0
    MACD_buy_sign = RSI_buy_sign = 0


    for i in range(6):
        if RSI(14)[data_n-3-i]<20 and RSI(14)[data_n-2-i]<20 and RSI(14)[data_n-1-i]>=20:
            count1 += 1
        if RSI(14)[data_n-3-i]<30 and RSI(14)[data_n-2-i]<30 and RSI(14)[data_n-1-i]>=30:
            count2 += 1

    if count1 > 0:
        RSI_buy_sign = 0.5
    elif count2 > 0:
        RSI_buy_sign = 0.3

    MACD,Signal = MACD_and_signal(12,26,9)

    if MACD[9] < MACD[10] and MACD[10] < MACD[11] and MACD[11] < 0:
        MACD_buy_sign = 0.5
    elif MACD[9] < MACD[10] and MACD[10] < MACD[11]:
        MACD_buy_sign = 0.3

    if RSI_buy_sign + MACD_buy_sign > 0.7:
        return True
    else: return False

# BBの超シンプル逆張り
def sell_signal2():
    b,u,l = BB(14,3)
    if u < close[data_n-1] and RSI(14)[data_n-1]>70:
        return True
    else:
        return False

def buy_signal2():
    b,u,l = BB(14,3)
    if l > close[data_n-1] and RSI(14)[data_n-1]<30:
        return True
    else:
        return False

def sell_signal3():
    global losscut
    losscut = response[data_n-1][2]-response[data_n-1][3]
    if engulfing_bar_sell():
        return True
    else:return False

def buy_signal3():
    global losscut
    losscut = response[data_n-1][2]-response[data_n-1][3]
    if engulfing_bar_buy():
        return True
    else:return False


#--------------------------------------------------------------

# 設定
while True:
    try:
        period = int(input("何分足でテストしますか？(秒換算した値を入れてください) >> "))
        close_data = get_price_data()
        response_data = requests.get("https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc",params = { "periods" : period , "after" : 1})
        response_data = response_data.json()
        break
    except KeyError:
        pass
    print("cryptowatchにない足のテストはできません")


# 終値配列の長さ
data_n = 100
flag = {
    "check":True,
	"sell_position":False,
	"buy_position":False
}
i = profit = loss = count1 = count2 = drawdown = count_position1 = count_position2 = m = 0
asset_list = []
time_data = []
MACD_data = []

input = int(input("何件分のろうそく足データでテストしますか？(最大{}件) >> ".format(l)))

start = l-input
limit = l-start-(data_n+1)

while i <= limit:
    while(flag["check"]):
        response = []
        closelist = []
        for j in range(data_n):
            response.append(response_data["result"][str(period)][i+j+start])
            closelist.append(close_data[i+j+start])
        arr = np.array(closelist)
        close = pd.Series(arr)

        if sell_signal3():
            print()
            print("==売り注文をします==")
            print("時刻："+str(datetime.datetime.fromtimestamp(response[data_n-1][0])))
            print("価格："+str(close[data_n-1]))
            price = close[data_n-1]

            #=======ここで値幅を設定========
            p_width = losscut
            l_width = losscut
            if 2*ATR(14) > 50000:
                p_width = l_width = 0
            #============================

            flag["sell_position"] = True
            flag["check"] = False


        if buy_signal3():
            print()
            print("==買い注文をします==")
            print("時刻："+str(datetime.datetime.fromtimestamp(response[data_n-1][0])))
            print("価格："+str(close[data_n-1]))
            price = close[data_n-1]

            #=======ここに値幅を設定========
            p_width = losscut
            l_width = losscut
            if 2*ATR(14) > 50000:
                p_width = l_width = 0
            #============================

            flag["buy_position"] = True
            flag["check"] = False


        i += 1
        if i > limit:
            break

    position_time = period

    while(flag["sell_position"]):
        response = []
        closelist = []
        for j in range(data_n):
            response.append(response_data["result"][str(period)][i+j+start])
            closelist.append(close_data[i+j+start])
        arr = np.array(closelist)
        close = pd.Series(arr)

        if response[data_n-1][3] < price-p_width:
            print()
            print("==利確:+"+str(int(p_width))+"==")
            print("時刻："+str(datetime.datetime.fromtimestamp(response[data_n-1][0])))
            print("価格："+str(close[data_n-1]))
            print("ポジションを持っていた時間:"+str(position_time)+"分")
            count_position1 += position_time
            count1 += 1
            profit += int(p_width)
            flag["sell_position"] = False
            flag["check"] = True

        if response[data_n-1][2] > price+l_width:
            print()
            print("==損切り:-"+str(int(l_width))+"==")
            print("時刻："+str(datetime.datetime.fromtimestamp(response[data_n-1][0])))
            print("価格："+str(close[data_n-1]))
            print("ポジションを持っていた時間:"+str(position_time)+"分")
            count_position2 += position_time
            count2 += 1
            loss += int(l_width)
            flag["sell_position"] = False
            flag["check"] = True

        i += 1
        position_time += period/60

        if i > limit:
            break

    while(flag["buy_position"]):
        response = []
        closelist = []
        for j in range(data_n):
            response.append(response_data["result"][str(period)][i+j+start])
            closelist.append(close_data[i+j+start])
        arr = np.array(closelist)
        close = pd.Series(arr)

        if response[data_n-1][2] > price+p_width:
            print()
            print("==利確:+"+str(int(p_width))+"==")
            print("時刻："+str(datetime.datetime.fromtimestamp(response[data_n-1][0])))
            print("価格："+str(close[data_n-1]))
            print("ポジションを持っていた時間:"+str(position_time)+"分")
            count_position1 += position_time
            count1 += 1
            profit += int(p_width)
            flag["buy_position"] = False
            flag["check"] = True

        if response[data_n-1][3] < price-l_width:
            print()
            print("==損切り:-"+str(int(l_width))+"==")
            print("時刻："+str(datetime.datetime.fromtimestamp(response[data_n-1][0])))
            print("価格："+str(close[data_n-1]))
            print("ポジションを持っていた時間:"+str(position_time)+"分")
            count_position2 += position_time
            count2 += 1
            loss += int(l_width)
            flag["buy_position"] = False
            flag["check"] = True

        i += 1
        position_time += period/60

        if i > limit:
            break
    asset_list.append(profit-loss)
    time_data.append(datetime.datetime.fromtimestamp(response[data_n-1][0]))

    if m < profit - loss:
        m = profit - loss
    if drawdown < m-(profit-loss):
        drawdown = m-(profit-loss)

print()
print("======テスト結果======")
print("利益合計："+str(profit))
print("損失合計："+str(loss))
print("儲け："+str(profit-loss))
print("利確回数："+str(count1))
print("利確平均："+str(profit/count1))
print("利確した時の平均ポジション保有時間"+str(count_position1/count1)+" 分")
print("損切り回数："+str(count2))
print("損切り平均："+str(loss/count2))
print("損切りした時の平均ポジション保有時間："+str(count_position2/count2)+" 分")
print("勝率："+str(count1/(count1+count2)*100)+" %")
print("損益率："+str((profit/count1)/(loss/count2)))
print("profit factor："+str(profit/loss))
print("最大ドローダウン："+str(drawdown/1000000.0)+" %")
print("=====================")

#グラフ作成
x = np.array(time_data)
y = np.array(asset_list)
plt.plot(x,y)
plt.xticks(rotation=45)
plt.show()
