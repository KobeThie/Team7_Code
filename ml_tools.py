from typing import Tuple
from core import RAWFILES, load_file
import pandas as pd
from sklearn.model_selection import train_test_split
import numpy as np
from sklearn import metrics
import matplotlib.pyplot as plt

BASE_NAMES = [name for name in load_file(RAWFILES.SIGNAL)]

def ml_strip_columns(dataframe,
    accepted_column_names: Tuple[str, ...]=(),
    reject_column_names: Tuple[str, ...]=(),
    inplace=False
) -> pd.DataFrame:
    """Strips columns which contain information we don't want to pass to the ML model"""

    if not inplace:
        dataframe = dataframe.copy()

    # Drops 'year' and 'B0_ID' columns
    columns_names_to_drop = ('year','B0_ID')

    # Drops any columns added during processing not specified to keep
    for name in dataframe:
        if (
            not (name in BASE_NAMES or name in accepted_column_names or name == 'category')
            or name in reject_column_names or name in columns_names_to_drop
        ):
            dataframe.drop(name, inplace=True, axis=1)

    return dataframe

def ml_train_model(training_data, model, **kwargs):
    """Trains a ML model. Requires that the parameter `training_data` contains a column named 'category'
    which will be the value the ML model is trained to predict; this should contain only integers,
    preferably only 0 or 1.
    """

    train_vars = training_data.drop('category',axis=1)
    model.fit(train_vars, training_data['category'].to_numpy(), **kwargs)
    return model

def ml_prepare_test_train(dataset, randomiser_seed = 1) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Takes a dataset and splits it into test and train datasets"""
    # Marek
    train, test = train_test_split(dataset, test_size = 0.2, random_state=randomiser_seed)
    return train, test


def ml_combine_signal_bk(signal_dataset, background_dataset):
    """Combines signal and background dataset, adding category labels
    """
    # Marek
    signal_dataset = signal_dataset.copy()
    background_dataset = background_dataset.copy()
    signal_dataset.loc[:,'category'] = 1
    background_dataset.loc[:,'category'] = 0

    # combine
    dataset = pd.concat((signal_dataset, background_dataset))
    return dataset

def ml_get_model_sig_prob(testData, model):
    if 'category' in testData:
        test_vars = testData.drop('category',axis=1)
    return model.predict_proba(test_vars)[:,1]

def test_false_true_negative_positive(test_dataset, sig_prob, threshold) -> dict:
    # Jiayang

    x = test_dataset['category'].to_numpy()

    x_mask_0 = x == 0
    x_mask_1 = x == 1
    prb_mask_pos = sig_prob >= threshold
    prb_mask_neg = sig_prob < threshold

    signal = np.count_nonzero(x_mask_1)
    background = np.count_nonzero(x_mask_0)
    true_positive =  np.count_nonzero(np.logical_and(x_mask_1, prb_mask_pos))
    false_negative = np.count_nonzero(np.logical_and(x_mask_1, prb_mask_neg))
    false_positive = np.count_nonzero(np.logical_and(x_mask_0, prb_mask_pos))
    true_negative =  np.count_nonzero(np.logical_and(x_mask_0, prb_mask_neg))

    # sanity check
    # total = true_positive + false_negtive + false_positive + true_negative
    # print('total counted:', total, (signal+background))
    # print('total candidates:', len(test_dataset['catagory']))

    # rates
    tpr = true_positive / signal
    fpr = false_positive / background

    fnr = false_negative / signal
    tnr = true_negative / background

    return {
        'true-positive': tpr,
        'false-positive': fpr,
        'true-negative': tnr,
        'false-negative': fnr,
        'signal': signal,
        'background': background
    }


def roc_curve(test_data, sp):
    # Jose
    '''
    Test data needs to be in pandas dataframe format.
    Implement the following model before this function:
        model = XGBClassifier()
        model.fit(training_data[training_columns], training_data['category'])
        sp = model.predict_proba(test_data[training_columns])[:,1]
        model.predict_proba(test_data[training_columns])
    This returns an array of N_samples by N_classes. 
    The first column is the probability that the candiate is category 0 (background).
    The second column (sp) is the probability that the candidate is category 1 (signal).

    The Receiver Operating Characteristic curve given by this function shows the efficiency of the classifier 
    on signal (true positive rate, tpr) against the inefficiency of removing background (false positive 
    rate, fpr). Each point on this curve corresponds to a cut value threshold.
    '''

    fpr, tpr, cut_values = metrics.roc_curve(test_data['category'], sp)
    area = metrics.auc(fpr, tpr)
    
    return {
        'fpr': fpr,
        'tpr': tpr,
        'cut_values': cut_values,
        'area': area
    }

def plot_roc_curve(fpr, tpr, area):
    # Jose
    
    plt.plot([0, 1], [0, 1], color='deepskyblue', linestyle='--', label='Random guess')
    plt.plot(fpr, tpr, color='darkblue', label=f'ROC curve (area = {area:.2f})')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.xlim(0.0, 1.0)
    plt.ylim(0.0, 1.0)
    plt.legend(loc='lower right')
    plt.gca().set_aspect('equal', adjustable='box')
    #plt.show()

def test_sb(test_dataset, sig_prob, threshold):
    # Jiayang

    output = test_false_true_negative_positive(test_dataset, sig_prob, threshold)

    S = output['signal'] * output['true-positive']
    B = output['background'] * output['false-positive']
    metric = S/np.sqrt(S+B)

    return metric
