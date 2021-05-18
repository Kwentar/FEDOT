import warnings

import pandas as pd
import numpy as np

from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

from fedot.core.chains.node import PrimaryNode, SecondaryNode
from fedot.core.chains.chain import Chain
from fedot.core.data.data import InputData
from fedot.core.repository.dataset_types import DataTypesEnum
from fedot.core.repository.tasks import Task, TaskTypesEnum

warnings.filterwarnings('ignore')


def get_refinement_chain():
    """ Create a chain like this
    5      ridge
    4             dtreg
    3 lasso     decompose
    2     scaling
    1 one_hot_encoding
    """
    # 1
    node_encoding = PrimaryNode('one_hot_encoding')
    # 2
    node_scaling = SecondaryNode('scaling', nodes_from=[node_encoding])
    # 3
    node_lasso = SecondaryNode('lasso', nodes_from=[node_scaling])
    node_decompose = SecondaryNode('decompose', nodes_from=[node_scaling, node_lasso])
    # 4
    node_dtreg = SecondaryNode('dtreg', nodes_from=[node_decompose])
    node_dtreg.custom_params = {'max_depth': 3}
    # 5
    final_node = SecondaryNode('ridge', nodes_from=[node_lasso, node_dtreg])

    chain = Chain(final_node)
    return chain


def get_non_refinement_chain():
    node_encoding = PrimaryNode('one_hot_encoding')
    node_scaling = SecondaryNode('scaling', nodes_from=[node_encoding])

    node_lasso = SecondaryNode('lasso', nodes_from=[node_scaling])
    node_dtreg = SecondaryNode('dtreg', nodes_from=[node_scaling])
    node_dtreg.custom_params = {'max_depth': 3}

    final_node = SecondaryNode('ridge', nodes_from=[node_lasso, node_dtreg])

    chain = Chain(final_node)
    return chain


def prepare_input_data(features, target):
    """ Function create InputData with features """
    x_data_train, x_data_test, y_data_train, y_data_test = train_test_split(
        features,
        target,
        test_size=0.2,
        shuffle=True,
        random_state=10)
    y_data_test = np.ravel(y_data_test)

    # Define regression task
    task = Task(TaskTypesEnum.regression)

    # Prepare data to train the model
    train_input = InputData(idx=np.arange(0, len(x_data_train)),
                            features=x_data_train,
                            target=y_data_train,
                            task=task,
                            data_type=DataTypesEnum.table)

    predict_input = InputData(idx=np.arange(0, len(x_data_test)),
                              features=x_data_test,
                              target=y_data_test,
                              task=task,
                              data_type=DataTypesEnum.table)

    return train_input, predict_input, task


def run_river_experiment(file_path, with_tuning=False):
    """ Function launch example with experimental features of the FEDOT framework

    :param file_path: path to the csv file
    :param with_tuning: is it need to tune chains or not
    """

    # Read dataframe and prepare train and test data
    df = pd.read_csv(file_path)
    features = np.array(df[['level_station_1', 'mean_temp', 'month', 'precip']])
    target = np.array(df['level_station_2']).reshape((-1, 1))

    # Prepare InputData for train and test
    train_input, predict_input, task = prepare_input_data(features, target)
    y_data_test = predict_input.target

    # Get refinement chain
    r_chain = get_refinement_chain()
    non_chain = get_non_refinement_chain()

    # Fit it
    r_chain.fit(train_input)
    non_chain.fit(train_input)

    if with_tuning:
        r_chain.fine_tune_all_nodes(loss_function=mean_absolute_error,
                                    loss_params=None,
                                    input_data=train_input,
                                    iterations=100)
        non_chain.fine_tune_all_nodes(loss_function=mean_absolute_error,
                                      loss_params=None,
                                      input_data=train_input,
                                      iterations=100)

    # Predict
    predicted_values = r_chain.predict(predict_input)
    r_preds = predicted_values.predict

    # Predict
    predicted_values = non_chain.predict(predict_input)
    non_preds = predicted_values.predict

    y_data_test = np.ravel(y_data_test)

    mse_value = mean_squared_error(y_data_test, r_preds, squared=False)
    mae_value = mean_absolute_error(y_data_test, r_preds)
    print(f'RMSE with decompose - {mse_value:.2f}')
    print(f'MAE with decompose - {mae_value:.2f}\n')

    mse_value_non = mean_squared_error(y_data_test, non_preds, squared=False)
    mae_value_non = mean_absolute_error(y_data_test, non_preds)
    print(f'RMSE non decompose - {mse_value_non:.2f}')
    print(f'MAE non decompose - {mae_value_non:.2f}\n')


if __name__ == '__main__':
    run_river_experiment(file_path='../cases/data/river_levels/station_levels.csv',
                         with_tuning=False)