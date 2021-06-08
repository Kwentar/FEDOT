import os
from unittest.mock import patch

import pytest

from cases.data.data_utils import get_scoring_case_data_paths
from fedot.core.chains.chain import Chain
from fedot.core.chains.node import PrimaryNode, SecondaryNode
from fedot.core.data.data import InputData
from fedot.core.data.data_split import train_test_data_setup
from fedot.core.log import default_log
from fedot.sensitivity.chain_sensitivity_facade import ChainSensitivityAnalysis
from fedot.sensitivity.deletion_methods.multi_times_analysis import MultiTimesAnalyze
from fedot.sensitivity.node_sa_approaches import NodeAnalysis, NodeDeletionAnalyze, NodeReplaceOperationAnalyze
from fedot.sensitivity.chain_sensitivity import ChainAnalysis
from fedot.sensitivity.operations_hp_sensitivity.multi_operations_sensitivity import MultiOperationsHPAnalyze
from fedot.sensitivity.operations_hp_sensitivity.one_operation_sensitivity import OneOperationHPAnalyze
from fedot.sensitivity.nodes_sensitivity import NodesAnalysis
from fedot.sensitivity.sa_requirementrs import SensitivityAnalysisRequirements
from test.unit.utilities.test_chain_import_export import create_func_delete_files


@pytest.fixture(scope='session', autouse=True)
def delete_files(request):
    paths = ['sa_test_result_path']
    delete_files = create_func_delete_files(paths)
    delete_files()
    request.addfinalizer(delete_files)


def scoring_dataset():
    train_file_path, test_file_path = get_scoring_case_data_paths()
    train_data = InputData.from_csv(train_file_path)
    test_data = InputData.from_csv(test_file_path)

    return train_data, test_data


def get_chain():
    knn_node = PrimaryNode('knn')
    lda_node = PrimaryNode('qda')
    xgb_node = PrimaryNode('xgboost')

    final = SecondaryNode('xgboost', nodes_from=[knn_node, lda_node, xgb_node])

    chain = Chain(final)

    return chain


def given_data():
    chain = get_chain()
    train_data, test_data = scoring_dataset()
    node_index = 2
    result_path = 'sa_test_result_path'
    if not os.path.exists(result_path):
        os.mkdir(result_path)

    return chain, train_data, test_data, chain.nodes[node_index], result_path


# ------------------------------------------------------------------------------
# ChainStructureAnalysis

def test_chain_structure_analyze_init_log_defined():
    # given
    chain, train_data, test_data, nodes_to_analyze, _ = given_data()
    approaches = [NodeDeletionAnalyze]
    test_log_object = default_log('test_log_chain_sa')

    # when
    chain_analyzer = NodesAnalysis(chain=chain,
                                   train_data=train_data,
                                   test_data=test_data,
                                   approaches=approaches,
                                   nodes_to_analyze=[nodes_to_analyze],
                                   log=test_log_object)

    assert isinstance(chain_analyzer, NodesAnalysis)


def test_chain_structure_analyze_analyze():
    # given
    chain, train_data, test_data, _, result_dir = given_data()
    approaches = [NodeDeletionAnalyze]

    # when
    result = NodesAnalysis(chain=chain,
                           train_data=train_data,
                           test_data=test_data,
                           approaches=approaches,
                           path_to_save=result_dir).analyze()
    assert isinstance(result, dict)


# ------------------------------------------------------------------------------
# NodeAnalysis


def test_node_analysis_init_default():
    # given

    # when
    node_analyzer = NodeAnalysis()

    # then
    assert isinstance(node_analyzer, NodeAnalysis)
    assert len(node_analyzer.approaches) == 2


def test_node_analysis_init_defined_approaches_and_log():
    # given
    approaches = [NodeDeletionAnalyze, NodeReplaceOperationAnalyze]
    test_log_object = default_log('test_log_node_sa')

    node_analyzer = NodeAnalysis(approaches=approaches,
                                 log=test_log_object)

    # then
    assert isinstance(node_analyzer, NodeAnalysis)
    assert len(node_analyzer.approaches) == 2
    assert node_analyzer.log is test_log_object


# @patch('fedot.sensitivity.sensitivity_facade.NodeAnalysis.analyze', return_value={'key': 'value'})
# @pytest.mark.skip('Works for more than 10 minutes - TODO improve it')
def test_node_analysis_analyze():
    # given
    chain, train_data, test_data, node_to_analyze, result_dir = given_data()

    # when
    node_analysis_result: dict = NodeAnalysis(path_to_save=result_dir). \
        analyze(chain=chain,
                node=node_to_analyze,
                train_data=train_data,
                test_data=test_data)

    assert isinstance(node_analysis_result, dict)


# ------------------------------------------------------------------------------
# NodeAnalyzeApproach

def test_node_deletion_analyze():
    # given
    chain, train_data, test_data, node_to_analyze, result_dir = given_data()

    # when
    node_analysis_result = NodeDeletionAnalyze(chain=chain,
                                               train_data=train_data,
                                               test_data=test_data,
                                               path_to_save=result_dir).analyze(node=node_to_analyze)

    # then
    assert isinstance(node_analysis_result, float)


def test_node_deletion_sample_method():
    # given
    _, train_data, test_data, _, result_dir = given_data()
    primary_first = PrimaryNode('knn')
    primary_second = PrimaryNode('knn')
    central = SecondaryNode('xgboost', nodes_from=[primary_first, primary_second])
    secondary_first = SecondaryNode('lda', nodes_from=[central])
    secondary_second = SecondaryNode('lda', nodes_from=[central])
    root = SecondaryNode('logit', nodes_from=[secondary_first, secondary_second])
    chain_with_multiple_children = Chain(nodes=root)

    # when
    result = NodeDeletionAnalyze(chain=chain_with_multiple_children,
                                 train_data=train_data,
                                 test_data=test_data,
                                 path_to_save=result_dir).sample(chain_with_multiple_children.nodes[2])

    # then
    assert result is None


def test_node_deletion_analyze_zero_node_id():
    # given
    chain, train_data, test_data, _, result_dir = given_data()

    # when
    node_analysis_result = NodeDeletionAnalyze(chain=chain,
                                               train_data=train_data,
                                               test_data=test_data,
                                               path_to_save=result_dir).analyze(node=chain.root_node)

    # then
    assert isinstance(node_analysis_result, float)
    assert node_analysis_result == 1.0


def test_node_replacement_analyze_defined_nodes():
    # given
    chain, train_data, test_data, node_to_analyze, result_dir = given_data()

    replacing_node = PrimaryNode('lda')

    # when
    node_analysis_result = \
        NodeReplaceOperationAnalyze(chain=chain,
                                    train_data=train_data,
                                    test_data=test_data,
                                    path_to_save=result_dir).analyze(node=node_to_analyze,
                                                                     nodes_to_replace_to=[replacing_node])

    # then
    assert isinstance(node_analysis_result, float)


# @pytest.mark.skip('Works for more than 10 minutes - TODO improve it')
def test_node_replacement_analyze_random_nodes_default_number():
    # given
    chain, train_data, test_data, node_to_analyze, result_dir = given_data()

    # when
    node_analysis_result = \
        (NodeReplaceOperationAnalyze(chain=chain,
                                     train_data=train_data,
                                     test_data=test_data,
                                     path_to_save=result_dir).
         analyze(node=node_to_analyze))

    # then
    assert isinstance(node_analysis_result, float)


# ------------------------------------------------------------------------------
# OneOperationAnalyze


def test_one_operation_analyze_analyze():
    # given
    chain, train_data, test_data, node_to_analyze, result_dir = given_data()

    requirements = SensitivityAnalysisRequirements(hyperparams_analysis_samples_size=1)

    # when
    result = OneOperationHPAnalyze(chain=chain, train_data=train_data, requirements=requirements,
                                   test_data=test_data, path_to_save=result_dir). \
        analyze(node=node_to_analyze)

    assert type(result) is dict


# ------------------------------------------------------------------------------
# MultiOperationAnalyze

@patch('fedot.sensitivity.operations_hp_sensitivity.multi_operations_sensitivity.MultiOperationsHPAnalyze.analyze',
       return_value=[{'key': 'value'}])
def test_multi_operations_analyze_analyze(analyze_method):
    # given
    chain, train_data, test_data, node_index, result_dir = given_data()

    # when
    result = MultiOperationsHPAnalyze(chain=chain,
                                      train_data=train_data,
                                      test_data=test_data, path_to_save=result_dir).analyze(sample_size=1)

    # then
    assert type(result) is list
    assert analyze_method.called


# ------------------------------------------------------------------------------
# SA Facade

def test_chain_sensitivity_facade_init():
    # given
    chain, train_data, test_data, node_to_analyze, result_dir = given_data()
    test_log_object = default_log('test_log_chain_sa')

    # when
    sensitivity_facade = ChainSensitivityAnalysis(chain=chain,
                                                  train_data=train_data,
                                                  test_data=test_data,
                                                  nodes_to_analyze=[node_to_analyze],
                                                  path_to_save=result_dir,
                                                  log=test_log_object)
    # then
    assert type(sensitivity_facade) is ChainSensitivityAnalysis


@patch('fedot.sensitivity.chain_sensitivity_facade.ChainSensitivityAnalysis.analyze', return_value=None)
def test_chain_sensitivity_facade_analyze(analyze_method):
    # given
    chain, train_data, test_data, node_to_analyze, result_dir = given_data()

    # when
    sensitivity_analyze_result = ChainSensitivityAnalysis(chain=chain,
                                                          train_data=train_data,
                                                          test_data=test_data,
                                                          nodes_to_analyze=[node_to_analyze],
                                                          path_to_save=result_dir).analyze()

    # then
    assert sensitivity_analyze_result is None
    assert analyze_method.called


# ------------------------------------------------------------------------------
# SA Non-structural analysis

def test_chain_non_structure_analyze_init():
    # given
    chain, train_data, test_data, node_index, result_dir = given_data()
    approaches = [MultiOperationsHPAnalyze]
    test_log_object = default_log('test_log_chain_sa')

    # when
    non_structure_analyzer = ChainAnalysis(chain=chain,
                                           train_data=train_data,
                                           test_data=test_data,
                                           approaches=approaches,
                                           path_to_save=result_dir,
                                           log=test_log_object)

    # then
    assert type(non_structure_analyzer) is ChainAnalysis


@patch('fedot.sensitivity.chain_sensitivity.ChainAnalysis.analyze',
       return_value=[{'key': 'value'}])
def test_chain_analysis_analyze(analyze_method):
    # given
    chain, train_data, test_data, node_index, result_dir = given_data()

    requirements = SensitivityAnalysisRequirements(hyperparams_analysis_samples_size=1)

    # when
    non_structure_analyze_result = ChainAnalysis(chain=chain,
                                                 train_data=train_data,
                                                 test_data=test_data,
                                                 requirements=requirements,
                                                 path_to_save=result_dir).analyze()

    # then
    assert type(non_structure_analyze_result) is list
    assert analyze_method.called


# ------------------------------------------------------------------------------
# Multi-Times-Analysis for Chain size decrease

def test_multi_times_analyze_init_defined_approaches():
    # given
    chain, train_data, test_data, node_index, result_dir = given_data()
    approaches = [NodeDeletionAnalyze]
    test_data, valid_data = train_test_data_setup(test_data, split_ratio=0.5)

    # when
    analyzer = MultiTimesAnalyze(chain=chain,
                                 train_data=train_data,
                                 test_data=test_data,
                                 valid_data=valid_data,
                                 case_name='test_case_name',
                                 path_to_save=result_dir,
                                 approaches=approaches)

    # then
    assert type(analyzer) is MultiTimesAnalyze


@patch('fedot.sensitivity.deletion_methods.multi_times_analysis.MultiTimesAnalyze.analyze',
       return_value=1.0)
def test_multi_times_analyze_analyze(analyze_method):
    # given
    chain, train_data, test_data, node_index, result_dir = given_data()
    test_data, valid_data = train_test_data_setup(test_data, split_ratio=0.5)

    # when
    analyze_result = MultiTimesAnalyze(chain=chain,
                                       train_data=train_data,
                                       test_data=test_data,
                                       valid_data=valid_data,
                                       case_name='test_case_name',
                                       path_to_save=result_dir).analyze()

    # then
    assert type(analyze_result) is float
    assert analyze_method.called
