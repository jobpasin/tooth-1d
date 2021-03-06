import tensorflow as tf
# tf.enable_eager_execution()
import numpy as np
import os
import argparse
from shutil import copy2
import csv
import datetime

from protobuf_helper import protobuf_to_list, protobuf_to_channels
from proto import tooth_pb2
from google.protobuf import text_format

import skopt
from skopt import gp_minimize, forest_minimize
from skopt.space import Real, Categorical, Integer
from skopt.utils import use_named_args

from cifar10_model import my_model
from cifar10_get_data import train_input_fn, eval_input_fn, get_data_from_path

activation_dict = {'0': tf.nn.relu, '1': tf.nn.leaky_relu}  # Declare global dictionary

# These are important parameters
run_params = {'batch_size': 4,
              'checkpoint_min': 5,
              'early_stop_step': 10000,
              'input_path': './data/cifar10.tfrecords',
              'result_path': '/home/pasin/Documents/Pasin/model/cifar10_hyper',
              'config_path': '',
              'steps': 100000}

model_configs = {'learning_rate': 0.0001,
                 'dropout_rate': 0.1,
                 'activation': tf.nn.relu,
                 'channels': [16, 16, 32, 32, 32, 32, 32, 32, 32, 2048, 2048]
                 }


def run(model_params={}):
    # Add exception in case params is missing
    if len(model_params['channels']) != 11:
        raise Exception("Number of channels not correspond to number of layers [Need size of 11, got %s]"
                        % len(model_params['channels']))

    # Type in file name
    train_data_path = run_params['input_path'].replace('.tfrecords', '') + '_train.tfrecords'
    eval_data_path = run_params['input_path'].replace('.tfrecords', '') + '_eval.tfrecords'
    print("Getting training data from %s" % train_data_path)
    print("Saved model at %s" % run_params['result_path_new'])

    tf.logging.set_verbosity(tf.logging.INFO)  # To see some additional info
    # Setting checkpoint config
    my_checkpoint_config = tf.estimator.RunConfig(
        save_checkpoints_secs=run_params['checkpoint_min'] * 60,
        # save_summary_steps=pareval_data_pathams['checkpoint_min'] * 10,
        keep_checkpoint_max=10,
        log_step_count_steps=500,
        session_config=tf.ConfigProto(allow_soft_placement=True)
    )
    # Or set up the model directory
    #   estimator = DNNClassifier(
    #       config=tf.estimator.RunConfig(
    #           model_dir='/my_model', save_summary_steps=100),
    classifier = tf.estimator.Estimator(
        model_fn=my_model,
        params=model_params,
        model_dir=run_params['result_path_new'],
        config=my_checkpoint_config
    )
    train_hook = tf.contrib.estimator.stop_if_no_decrease_hook(classifier, "loss", run_params['early_stop_step'])
    train_spec = tf.estimator.TrainSpec(
        input_fn=lambda: train_input_fn(train_data_path, batch_size=run_params['batch_size']),
        max_steps=run_params['steps'], hooks=[train_hook])
    eval_spec = tf.estimator.EvalSpec(
        input_fn=lambda: eval_input_fn(eval_data_path, batch_size=16), steps=None,
        start_delay_secs=0, throttle_secs=0)
    # classifier.train(input_fn=lambda: train_input_fn(train_data_path, batch_size=params['batch_size']),
    #     max_steps=params['steps'], hooks=[train_hook])
    # eval_result = classifier.evaluate(input_fn=lambda: eval_input_fn(eval_data_path, batch_size=32))

    eval_result = tf.estimator.train_and_evaluate(classifier, train_spec, eval_spec)
    print("Eval result:")
    print(eval_result)
    try:
        accuracy = eval_result[0]['accuracy']
        global_step = eval_result[0]['global_step']
    except TypeError:
        print("Warning, does receive evaluation result")
        accuracy = 0
        global_step = 0

    predictions = classifier.predict(input_fn=lambda: eval_input_fn(eval_data_path, batch_size=1))

    images, expected = get_data_from_path(eval_data_path)
    predict_score = ['Prediction']
    probability_score = ['Probability']
    label_score = ['Label']
    for pred_dict, expec in zip(predictions, expected):
        # print(pred_dict)
        print("Score" + str(pred_dict['score']))
        class_id = pred_dict['score'][0]
        probability = pred_dict['probabilities'][class_id]
        print("Actual score: %s, Predicted score: %s with probability %s" % (expec, class_id, probability))
        predict_score.append(class_id)
        label_score.append(expec)
        probability_score.append(probability)

    # predict_result = zip(label_score, predict_score, probability_score)

    predict_result = zip(label_score, predict_score, probability_score)
    # print(eval_result[0]['accuracy'])
    # print('\nTest set accuracy: {accuracy:0.3f}\n'.format(**eval_result))
    return accuracy, global_step, predict_result


dim_learning_rate = Real(low=1e-5, high=1e-2, prior='log-uniform', name='learning_rate')
dim_dropout_rate = Real(low=0, high=0.875, name='dropout_rate')
dim_activation = Categorical(categories=['0', '1'],
                             name='activation')
dim_channel = Integer(low=1, high=4, name='channels')
dimensions = [dim_learning_rate,
              dim_dropout_rate,
              dim_activation,
              dim_channel]
default_parameters = [1e-3, 0.125, '1', 2]


@use_named_args(dimensions=dimensions)
def fitness(learning_rate, dropout_rate, activation, channels):
    """
    Hyper-parameters:
    learning_rate:     Learning-rate for the optimizer.
    dropout_rate:
    activation:        Activation function for all layers.
    channels
    """
    # Create the neural network with these hyper-parameters
    print("Learning_rate, Dropout_rate, Activation, Channels = %s, %s, %s, %s" % (
        learning_rate, dropout_rate, activation, channels))
    channels_full = [i * channels for i in [16, 16, 32, 16, 16, 16, 16, 16, 16, 512, 512]]
    name = run_params['result_path'] + "/" + datetime.datetime.now().strftime("%Y%m%d_%H_%M_%S") + "/"
    # name = ("%s/learning_rate_%s_dropout_%s_activation_%s_channels_%s/"
    #         % (run_params['result_path'], round(learning_rate, 6), dropout_rate, activation, channels))
    run_params['result_path_new'] = name
    md_config = {'learning_rate': learning_rate,
                 'dropout_rate': dropout_rate,
                 'activation': activation_dict[activation],
                 'channels': channels_full}
    accuracy, global_step, result = run(md_config)
    # accuracy = run_hyper_parameter_wrapper(learning_rate, dropout_rate, activation, channels)

    # Save necessary info to csv file, as reference
    info_dict = run_params.copy()
    info_dict['comments'] = "Try hyper search on cifar10"
    info_dict['learning_rate'] = learning_rate
    info_dict['dropout_rate'] = dropout_rate
    info_dict['activation'] = activation
    info_dict['channels'] = channels
    info_dict['steps'] = global_step
    info_dict['accuracy'] = accuracy
    with open(name + "config.csv", "w") as csvfile:
        writer = csv.writer(csvfile)
        for key, val in info_dict.items():
            writer.writerow([key, val])
    with open(name + "result.csv", "w") as csvfile:
        writer = csv.writer(csvfile)
        for row in result:
            writer.writerow(row)
    return -accuracy


def run_hyper_parameter_optimize(model_config):
    search_result = gp_minimize(func=fitness,
                                dimensions=dimensions,
                                acq_func='EI',  # Expected Improvement.
                                n_calls=20,
                                x0=default_parameters)
    print(search_result)
    print("Best hyper-parameters: %s" % search_result.x)
    searched_parameter = sorted(list(zip(search_result.func_vals, search_result.x_iters)))
    print("All hyper-parameter searched: %s" % searched_parameter)
    hyperparameter_filename = "hyperparameters_" + datetime.datetime.now().strftime("%Y%m%d_%H_%M_%S") + ".csv"
    new_data = []
    field_name = ['accuracy', 'learning_rate', 'dropout_rate', 'activation', 'channels']
    for i in searched_parameter:
        data = {field_name[0]: i[0] * -1,
                field_name[1]: i[1][0],
                field_name[2]: i[1][1],
                field_name[3]: i[1][1],
                field_name[4]: i[1][1]}
        new_data.append(data)
    with open(run_params['result_path'] + '/' + hyperparameter_filename, 'w', newline='') as csvFile:
        writer = csv.DictWriter(csvFile, fieldnames=field_name)
        writer.writeheader()
        writer.writerows(new_data)
    # space = search_result.space
    # print("Best result: %s" % space.point_to_dict(search_result.x))


if __name__ == '__main__':
    # read_file()
    if False:
        md_configs = {'learning_rate': model_configs['learning_rate'],
                      'dropout_rate': model_configs['dropout_rate'],
                      'activation': model_configs['activation'],
                      'channels': model_configs['channels']
                      }
        run_params['result_path_new'] = run_params['result_path']
        run(md_configs)
    else:
        run_hyper_parameter_optimize(model_configs)
    print("train.py completed")
