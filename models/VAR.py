import logging

import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from statsmodels.tsa.statespace.varmax import VARMAX, VARMAXResults
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

import greenium.utils.data


class VARModel(VARMAX):

    def __init__(self,
                 dataclass: greenium.utils.data.Data,
                 order: tuple = (1, 0),
                 train_percent: float = 0.7,
                 load: str = None):

        self.dataclass = dataclass
        self.scaler = dataclass.scaler or None
        self.dataset = dataclass.df
        self.logger = dataclass.logger
        self.load = load
        self.train_set, self.test_set = self.split(train_percent)
        # model parameters
        self.order = order

        super(VARModel, self).__init__(
            self.train_set,
            order=self.order)

    def split(self, train_percent):

        stop_idx = np.floor(train_percent * len(self.dataset)).astype(int)
        train_set = self.dataset.iloc[:stop_idx]
        test_set = self.dataset.iloc[stop_idx:]
        # self.train_set = self.train_set.set_index('validdate').asfreq('D')
        # self.test_set = self.test_set.set_index('validdate').asfreq('D')

        self.logger.info(f'Test and train set successfully created.')

        return train_set, test_set

    def fit(self, **kwargs) -> object:
        """
        Inherits from MLEResults.fit()

        :param kwargs:
        :return:
        """
        if self.load:
            self.model_result = VARMAXResults.load(self.load)
            self.logger.info(f'model loaded from {self.load}')
            return self.model_result

        self.model_result = super(VARModel, self).fit(maxiter=1000, disp=False)
        self.logger.info('Trained and fit')

        return self.model_result

    def predict(self,
                start: str, end: str,
                plot: bool = True,
                save_png: str = None):

        """
        Predictions for in-sample dates.

        :rtype: object
        """
        start = pd.to_datetime(start)
        end = pd.to_datetime(end)
        num_hours = np.round((end-start).value/(60*60*10e8)).astype(int)

        pred = self.model_result.predict(start=start, end=end)
        real = self.train_set.loc[start:end]
        pred = pred.set_index(real.index)
        pred = self.dataclass.inverse_transform(pred)
        real = self.dataclass.inverse_transform(real)

        if plot:
            # Plot predictions
            fig, axs = plt.subplots(len(real.columns), 1, figsize=(16, 10))
            fig.subplots_adjust(hspace=0)
            myFmt = DateFormatter("%H:%M")
            label_dict = {'max_power_gym': ('Power Output Gym Dataset', 'Output (kW)'),
                          'max_power_johnson': ('Power Output Johnson Dataset', 'Output (kW)'),
                          'max_power': ('Power Output', 'Output (kW)'),
                          't_2m:C': ('Temperature', 'Degrees Celsius'),
                          'global_rad:W': ('Global Irradiance', 'Irradiance $(W/m^2)$'),
                          'effective_cloud_cover:p': ('Effective Cloud Cover', 'Percent'),
                          'precip_1h:mm': ('Precipitation', 'mm/hr')}

            for i, col in enumerate(real.columns):
                real_vals = real[col].iloc[:num_hours]
                pred_vals = pred[col].iloc[:num_hours]
                rmse = mean_squared_error(real_vals, pred_vals, squared=False)
                mae = mean_absolute_error(real_vals, pred_vals)
                r2 = r2_score(real_vals, pred_vals)
                self.logger.info(f'RMSE {col}: {rmse}')
                time = real.index[:num_hours]
                if col == 'max_power':
                    real_vals /= 1000
                    pred_vals /= 1000
                axs[i].plot(time, real_vals,
                            label='Real' if i == 0 else '_nolegend_', c='b')
                axs[i].plot(time, pred_vals,
                            label='Predicted' if i == 0 else '_nolegend_', c='r')
                axs[i].set_title(label_dict[col][0], y=1.0, pad=-14)
                axs[i].set_ylabel(label_dict[col][1], fontsize=8)
                axs[i].set_ylim(
                    [None, np.amax([np.amax([real_vals, pred_vals]) * 1.4, np.amax([real_vals, pred_vals]) + 0.005])])
                axs[i].text(0.1, 0.9, f'RMSE: {rmse:.3f}\n$R^2$: {r2:.3f}\n'
                                      f'MAPE: {mae/(np.amax(real_vals)-np.amin(real_vals)):0.3f}',
                            horizontalalignment='left',
                            verticalalignment='top',
                            fontsize=8,
                            transform=axs[i].transAxes,
                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                axs[i].xaxis.set_major_formatter(myFmt)
                if col != real.columns[-1]:
                    axs[i].set_xticks([])

            axs[i].set_xlabel('Time (hr)')
            fig.legend()
            fig.suptitle('Real v. Predicted values 24h')
            if save_png:
                plt.savefig(f'scratch/figures/transparent/{save_png}', transparent=True)
            plt.show()

        return pred, real

    def simulate(self, params, nsimulations, **kwargs):

        sim = super(VARModel, self).simulate(params, nsimulations, **kwargs)
        return sim

    def summary(self):

        self.logger.info(f'AIC: {self.model_result.aic}')
        self.logger.info(f'Total MSE: {self.model_result.mse}')
        print(self.model_result.summary())

        residuals = self.model_result.resid
        print(residuals.describe())

        for col in residuals.columns:
            fig, axs = plt.subplots(1, 2)
            residuals[col].plot(ax=axs[0],
                                title=f'Residuals for VAR Model order {self.order}')
            kde = residuals[col].plot(ax=axs[1],
                                      title=f'KDE of Residuals of VAR Model order {self.order}',
                                      kind='kde')
            axs[1].axvline(residuals[col].mean(), c='r')
            axs[1].text(residuals[col].mean(), np.amax(axs[1].lines[0].get_ydata()),
                        s=f'{residuals[col].mean():0.3e}',
                        ha='left',
                        va='bottom',
                        )
            axs[1].legend()
            plt.show()



    def save(self, filename: str, remove_data: bool = False):
        self.model_result.save(f'models/saved_models/var_{filename}', remove_data=remove_data)