import numpy as np
import pandas as pd
import sys
import glob

path = "./training_data_large/"  # to make sure signal files are written in same directory as data files

def compute_market_prices(prices):
    """Compute market prices according to the trading competition recipe.

    Parameters
    ----------
    prices : DataFrame
        Data frame with market prices. Should include columns 'bid_price',
        'bid_volume', 'aks_price', 'ask_volume'.

    Returns
    -------
    prices : DataFrame
        Same data frame, but with a column 'market_price' appended.
    """
    denom = prices.bid_volume + prices.ask_volume
    numer = (prices.bid_price * prices.ask_volume +
             prices.ask_price * prices.bid_volume)
    mask = denom == 0
    denom[mask] = 2
    numer[mask] = prices.bid_price[mask] + prices.ask_price[mask]
    prices = prices.copy()
    prices['market_price'] = numer / denom
    return prices


def find_optimal_strategy(prices, max_position=3, cost_per_trade=0.02):
    """Find optimal trading strategy.

    A dynamic programming algorithm is used. Time complexity is "number
    of samples x number of maximum positions".

    Parameters
    ----------
    prices : DataFrame
        Data frame with market prices. Should include columns 'bid_price',
        'aks_price', 'market_price'.
    max_position : int
        Maximum allowed number of positions in buying or selling.
    cost_per_trade : float, default 0.02
        Fee paid for every trade.

    Returns
    -------
    actions : ndarray
        Sequence of optimal actions: -1 for sell, 0 for hold, 1 for buy.
        Length is the same as the number of columns in `prices`.
    pnl : float
        Profit per trading action.
    """
    buy_price = np.maximum(prices.bid_price, prices.ask_price).values
    sell_price = np.minimum(prices.bid_price, prices.ask_price).values

    account = np.full((prices.shape[0] + 1, 2 * max_position + 3), -np.inf)
    account[0, max_position + 1] = 0

    actions = np.empty((prices.shape[0], 2 * max_position + 3), dtype=int)

    for i in range(prices.shape[0]):
        for j in range(1, account.shape[1] - 1):
            buy = account[i, j - 1] - cost_per_trade - buy_price[i]
            sell = account[i, j + 1] - cost_per_trade + sell_price[i]
            hold = account[i, j]
            if buy > sell and buy > hold:
                account[i + 1, j] = buy
                actions[i, j] = 1
            elif sell > buy and sell > hold:
                account[i + 1, j] = sell
                actions[i, j] = -1
            else:
                account[i + 1, j] = hold
                actions[i, j] = 0

    pnl = account[-1, 1:-1] + (np.arange(-max_position, max_position + 1) *
                               prices.market_price.iloc[-1])
    j = np.argmax(pnl) + 1
    optimal_sequence = []
    for i in reversed(range(actions.shape[0])):
        optimal_sequence.append(actions[i, j])
        j -= actions[i, j]
    optimal_sequence = np.array(list(reversed(optimal_sequence)))

    return optimal_sequence, np.max(pnl) / optimal_sequence.size


def simulate_trading(prices, actions, cost_per_trade=0.02):
    """Simulate trading according to given actions.

    This is a literate translation of a pseudo code provided in [1]_.

    Parameters
    ----------
    prices : DataFrame
        Data frame with market prices. Should include columns 'bid_price',
        'aks_price', 'market_price'.
    actions : array_like
        Sequence of actions: -1 for sell, 0 for hold, 1 for buy. Length is the
        same as the number of columns in `prices`.
    cost_per_trade : float, default 0.02
        Fee paid for every trade.

    Returns
    -------
    pnl : float
        Profit per trading action.

    References
    ----------
    .. [1] Roni Mittelman "Time-series modeling with undecimated fully
       convolutional neural networks", http://arxiv.org/abs/1508.00317
    """
    pnl = 0
    position = 0
    market_price = prices.market_price.values
    buy_price = np.maximum(prices.bid_price, prices.ask_price).values
    sell_price = np.minimum(prices.bid_price, prices.ask_price).values

    for i in range(len(actions)):
        if i > 0:
            pnl += position * (market_price[i] - market_price[i - 1])

        if actions[i] == 1:
            pnl -= cost_per_trade
            pnl -= buy_price[i]
            pnl += market_price[i]
            position += 1
        elif actions[i] == -1:
            pnl -= cost_per_trade
            pnl += sell_price[i]
            pnl -= market_price[i]
            position -= 1

    return pnl / len(actions)


if __name__ == '__main__':
    # Example data file can be downloaded from here
    # https://s3.amazonaws.com/dvcpublic/workdir.zip. But any file in
    # the competition format should work.

    
    file_list = sorted(glob.glob('./training_data_large/prod_data_*v.txt'))

    if len(file_list) == 0:
        print(
            "Files ./training_data_large/product_data_*txt and signal_*.csv are needed. Please copy them in the ./training_data_large/ . Aborting.")
        sys.exit()

    for j in range(len(file_list)):
        filename = file_list[j]
        print('Training: ', filename)

        #df = pd.read_csv("prod_data_v.txt", header=None, delim_whitespace=True)
        df = pd.read_csv(filename, header=None, delim_whitespace=True)
        prices = pd.DataFrame(df.iloc[:, 2:6].values,
                              columns=['bid_price', 'bid_volume', 'ask_price',
                                       'ask_volume'])
        prices = compute_market_prices(prices)

        actions, pnl_opt = find_optimal_strategy(prices)
        pnl_sim = simulate_trading(prices, actions)
        print("PNL compute by the optimization algorithm {:.3f}".format(pnl_opt))
        print("PNL compute by the simulator {:.3f}".format(pnl_sim))
