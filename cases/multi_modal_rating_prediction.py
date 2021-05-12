import os

import numpy as np
from sklearn.metrics import roc_auc_score as roc_auc

from fedot.core.chains.chain import Chain
from fedot.core.chains.node import PrimaryNode, SecondaryNode
from fedot.core.data.data import InputData, OutputData, train_test_data_setup
from fedot.core.repository.tasks import Task, TaskTypesEnum
from fedot.core.utils import project_root


def calculate_validation_metric(pred: OutputData, valid: InputData) -> float:
    predicted = np.ravel(pred.predict)
    real = np.ravel(valid.target)

    rmse = roc_auc(y_true=real,
                   y_score=predicted)

    return round(rmse, 2)


def run_multi_modal_case():
    task = Task(TaskTypesEnum.classification)

    files_path = 'cases/data/mm_imdb/'
    path = os.path.join(str(project_root()), files_path)

    data = InputData.from_json_files(path, fiedls_to_use=['votes', 'year'],
                                     label='rating', task=task)

    class_labels = np.asarray([0 if t <= 7 else 1 for t in data.target])
    data.target = class_labels

    ratio = 0.5

    train, test = train_test_data_setup(data, shuffle_flag=False, split_ratio=ratio)

    img_files_path = 'cases/data/mm_imdb/*.jpeg'
    img_path = os.path.join(str(project_root()), img_files_path)

    data_img = InputData.from_image(images=img_path, labels=class_labels, task=task)

    train_img, test_img = train_test_data_setup(data_img, shuffle_flag=False, split_ratio=ratio)

    data_text = InputData.from_json_files(path, fiedls_to_use=['plot'],
                                          label='rating', task=task)
    data_text.target = class_labels
    train_text, test_text = train_test_data_setup(data_text, shuffle_flag=False, split_ratio=ratio)

    # image
    image_node = PrimaryNode('cnn', node_data={'fit': train_img, 'predict': test_img})
    image_node.custom_params = {'image_shape': (28, 28, 3),
                                'architecture': 'simplified',
                                'num_classes': 2,
                                'epochs': 15,
                                'batch_size': 128}

    # table
    numeric_node = PrimaryNode('rf', node_data={'fit': train, 'predict': test})

    # text
    node_text_clean = PrimaryNode('text_clean', node_data={'fit': train_text, 'predict': test_text})
    text_node = SecondaryNode('tfidf', nodes_from=[node_text_clean])

    chain = Chain(SecondaryNode('logit', nodes_from=[numeric_node, image_node, text_node]))
    chain.fit()
    prediction = chain.predict()

    rmse = calculate_validation_metric(prediction, test)

    print(rmse)


if __name__ == '__main__':
    run_multi_modal_case()
