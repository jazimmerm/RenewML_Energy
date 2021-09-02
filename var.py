import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import date

from utils.data import Data
from utils.processing import perform_PCA
from utils import utils
from models.VAR import VARModel


def show_fft(stationary: pd.DataFrame, raw_data: pd.DataFrame):
    fig, axs = plt.subplots(nrows=len(raw_data.df.columns), ncols=2)
    fig.subplots_adjust(hspace=0)
    raw_data.FFT(axs=axs.T[0])
    stationary.FFT(axs=axs.T[1])
    axs[0][0].set_title('Raw Data')
    axs[0][1].set_title('Stationarized Data')
    fig.suptitle('FFT: Raw vs Stationary Data')
    for x in range(len(axs)):
        max_ylim = np.max([axs[x][0].get_ylim()[1], axs[x][1].get_ylim()[1]])
        smaller = np.argmax([axs[x][0].get_ylim(), axs[x][1].get_ylim()])
        axs[x][smaller].set_ylim(bottom=None, top=max_ylim)
    plt.show()


if __name__ == '__main__':
    LOGGER = utils.get_logger(
        log_file=f'logs/{date.today()}',
        script_name=os.path.basename(__file__),
    )

    # Get and normalize data
    raw_data = Data.get_data(datafile='data/4Y_Historical.csv',
                             logger=LOGGER)

    # Get and normalize data
    raw_data_gym = Data.get_data(datafile='data/4Y_Historical.csv',
                                 powerfile='data/gym_from_2010_04_06_to_2020_12_31.csv',
                                 logger=LOGGER)

    raw_data_johnson = Data.get_data(datafile='data/4Y_Historical.csv',
                                     powerfile='data/maabarot_johnson_from_2010_04_22_to_2020_12_31.csv',
                                     logger=LOGGER)

    raw_data_johnson_gym = Data.get_data(datafile='data/4Y_Historical.csv',
                                         powerfile='data/maabarot_johnson_from_2010_04_22_to_2020_12_31.csv',
                                         logger=LOGGER)

    gym_johnson = Data.get_data(datafile='data/4Y_Historical.csv',
                                powerfile='data/maabarot_johnson_from_2010_04_22_to_2020_12_31.csv',
                                logger=LOGGER)

    raw_data_johnson_gym.df = pd.concat([raw_data_johnson.df, raw_data_gym.df['max_power']], axis=1, join='inner')
    raw_data_johnson_gym.df.columns = np.concatenate((raw_data.df.columns, ['max_power_johnson', 'max_power_gym']))

    gym_johnson.df = pd.concat([raw_data_gym.df['max_power'], raw_data_johnson.df['max_power']], axis=1, join='inner')
    gym_johnson.df.columns = ['max_power_gym', 'max_power_johnson']

    stationary = raw_data_gym.transform(lag=['hour', 'day'],
                                        resample=False,
                                        scaler=None)
    save_str = 'gym'
    order = 10

    if 'johnson_gym' in save_str:
        stationary.df['max_power_gym'] = stationary.df['max_power_gym'].astype(np.float64)
    else:
        stationary.df['max_power'] = stationary.df['max_power'].astype(np.float64)
    stationary.df = stationary.df.drop(columns=['diffuse_rad:W', 'direct_rad:W'])
    stationary.raw_data = stationary.raw_data.drop(columns=['diffuse_rad:W', 'direct_rad:W'])

    var = VARModel(stationary,
                   order=(order, 0),
                   load=f'models/saved_models/var_{save_str}_{order}.pkl'
                   )

    var.fit()
    var.predict(
                start='2018-01-03 01:00:00',
                end='2018-01-04 01:00:00',
                save_png=f'real_v_pred_{save_str}_{order}.png'
                )
    # var.save(f'{save_str}_order_{order}.pkl', remove_data=False)
    var.summary()