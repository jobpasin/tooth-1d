import tensorflow as tf
# tf.enable_eager_execution()
import numpy as np
import os
import csv
import tensorflow_hub as hub
from utils.custom_hook import EvalResultHook, PrintValueHook

# Default stride of 1, padding:same
def cnn_2d(layer,
           conv_filter_size,  # [Scalar]
           num_filters,  # [Scalar]
           activation=tf.nn.relu,
           stride=1,
           name=''):  # Stride of CNN
    # We shall define the weights that will be trained using create_weights function.
    layer = tf.keras.layers.Conv2D(num_filters, conv_filter_size, strides=stride, padding="same",
                                   activation=activation)(layer)

    # cnn_sum = tf.summary.histogram(name+'_activation',layer)
    return layer


def flatten_layer(layer):  # Flatten from 2D/3D to 1D (not count batch dimension)
    layer = tf.keras.layers.Flatten()(layer)
    return layer


def fc_layer(layer,  #
             num_outputs,
             activation=tf.nn.relu,
             name=''):
    # Let's define trainable weights and biases.
    layer = tf.keras.layers.Dense(num_outputs, activation=activation)(layer)
    return layer


def avg_pool_layer(layer, pooling_size, name=None, stride=-1):
    # Set stride equals to pooling size unless specified
    if stride == -1:
        stride = pooling_size
    return tf.keras.layers.AveragePooling2D(pooling_size, stride, padding="same")(layer)


def max_pool_layer(layer, pooling_size, name=None, stride=-1):
    # Set stride equals to pooling size unless specified
    if stride == -1:
        stride = pooling_size
    return tf.keras.layers.MaxPooling2D(pooling_size, stride, padding="same")(layer)


def max_and_cnn_layer(layer, pl_size, num_filters, activation, name):
    pool = tf.keras.layers.MaxPooling2D(pl_size, strides=pl_size, padding="same")(layer)
    conv = tf.keras.layers.Conv2D(num_filters, pl_size, strides=pl_size, padding="same",
                                  activation=activation)(layer)
    concat = tf.keras.layers.concatenate([pool, conv], 3)
    return concat


'''
def dropout(layer, dropout_rate, training, name):
    return tf.layers.dropout(layer, rate=dropout_rate, training=training, name=name)
'''


# Using average pooling
def customized_incepnet(features, mode, params):
    # (1) Filter size: 5x5x64
    conv1 = cnn_2d(features, 5, params['channels'][0], activation=params['activation'], name="conv1")
    pool1 = avg_pool_layer(conv1, 4, "pool1")
    # Output: 60x90x64

    # (2) Filter size: 3x3x64
    conv2 = cnn_2d(pool1, 3, params['channels'][1], activation=params['activation'], name="conv2")
    pool2 = avg_pool_layer(conv2, 2, "pool2")
    # Output: 30x45x64

    # (3.1) Max Pool, then Filter size: 64
    pool3_1 = max_pool_layer(pool2, 3, "pool3_1", stride=1)  # Special stride to keep same dimension
    conv3_1 = cnn_2d(pool3_1, 1, params['channels'][2], activation=params['activation'], name="conv3_1")
    # Output: 30x45x64

    # (3.2) Filter size: 1x1x64, then 3x3x64
    conv3_2 = cnn_2d(pool2, 1, params['channels'][3], activation=params['activation'], name="conv3_2_1")
    conv3_2 = cnn_2d(conv3_2, 3, params['channels'][4], activation=params['activation'], name="conv3_2")
    # Output: 30x45x64

    # (3.3) Filter size: 1x1x64, then 5x5x64
    conv3_3 = cnn_2d(pool2, 1, params['channels'][5], activation=params['activation'], name="conv3_3_1")
    conv3_3 = cnn_2d(conv3_3, 3, params['channels'][6], activation=params['activation'], name="conv3_3_2")
    conv3_3 = cnn_2d(conv3_3, 3, params['channels'][7], activation=params['activation'], name="conv3_3_3")
    # conv3_3 = cnn_2d(conv3_3, 5, 64)  # Might use 2 3x3 CNN instead, look at inception net paper
    # Output: 30x45x64

    # (3.4) Filter size: 1x1x256
    conv3_4 = cnn_2d(pool2, 1, params['channels'][8], activation=params['activation'], name="conv3_4")
    # Output: 30x45x64

    concat4 = tf.concat([conv3_1, conv3_2, conv3_3, conv3_4], 3)
    pool4 = avg_pool_layer(concat4, 3, name="pool4")
    # Output: 10x15x256 = 38400

    fc5 = flatten_layer(pool4)
    fc5 = fc_layer(fc5, params['channels'][9], activation=params['activation'], name='fc5')
    dropout5 = tf.keras.layers.Dropout(rate=params['dropout_rate'])(fc5)

    fc6 = fc_layer(dropout5, params['channels'][10], activation=params['activation'], name='fc6')
    dropout6 = tf.keras.layers.Dropout(rate=params['dropout_rate'])(fc6)

    logits = fc_layer(dropout6, 1, activation=tf.nn.tanh, name='predict')
    return logits


# Using max pooling
def customized_incepnet_v2(features, mode, params):
    # (1) Filter size: 5x5x64
    conv1 = cnn_2d(features, 5, params['channels'][0], activation=params['activation'], name="conv1")
    pool1 = max_pool_layer(conv1, 4, "pool1")
    # Output: 60x90x64

    # (2) Filter size: 3x3x64
    conv2 = cnn_2d(pool1, 3, params['channels'][1], activation=params['activation'], name="conv2")
    pool2 = max_pool_layer(conv2, 2, "pool2")
    # Output: 30x45x64

    # (3.1) Max Pool, then Filter size: 64
    pool3_1 = max_pool_layer(pool2, 3, "pool3_1", stride=1)  # Special stride to keep same dimension
    conv3_1 = cnn_2d(pool3_1, 1, params['channels'][2], activation=params['activation'], name="conv3_1")
    # Output: 30x45x64

    # (3.2) Filter size: 1x1x64, then 3x3x64
    conv3_2 = cnn_2d(pool2, 1, params['channels'][3], activation=params['activation'], name="conv3_2_1")
    conv3_2 = cnn_2d(conv3_2, 3, params['channels'][4], activation=params['activation'], name="conv3_2")
    # Output: 30x45x64

    # (3.3) Filter size: 1x1x64, then 5x5x64
    conv3_3 = cnn_2d(pool2, 1, params['channels'][5], activation=params['activation'], name="conv3_3_1")
    conv3_3 = cnn_2d(conv3_3, 3, params['channels'][6], activation=params['activation'], name="conv3_3_2")
    conv3_3 = cnn_2d(conv3_3, 3, params['channels'][7], activation=params['activation'], name="conv3_3_3")
    # conv3_3 = cnn_2d(conv3_3, 5, 64)  # Might use 2 3x3 CNN instead, look at inception net paper
    # Output: 30x45x64

    # (3.4) Filter size: 1x1x256
    conv3_4 = cnn_2d(pool2, 1, params['channels'][8], activation=params['activation'], name="conv3_4")
    # Output: 30x45x64

    concat4 = tf.concat([conv3_1, conv3_2, conv3_3, conv3_4], 3)
    pool4 = max_pool_layer(concat4, 3, name="pool4")
    # Output: 10x15x256 = 38400

    fc5 = flatten_layer(pool4)
    fc5 = fc_layer(fc5, params['channels'][9], activation=params['activation'], name='fc5')
    dropout5 = tf.keras.layers.Dropout(rate=params['dropout_rate'])(fc5)

    fc6 = fc_layer(dropout5, params['channels'][10], activation=params['activation'], name='fc6')
    dropout6 = tf.keras.layers.Dropout(rate=params['dropout_rate'])(fc6)

    logits = fc_layer(dropout6, 1, activation=tf.nn.tanh, name='predict')
    return logits


# Add cnn with pooling everywhere
def customized_incepnet_v3(features, mode, params):
    # (1) Filter size: 5x5x64
    conv1 = cnn_2d(features, 5, params['channels'][0], activation=params['activation'], name="conv1")
    pool1 = max_and_cnn_layer(conv1, 4, params['channels'][0], activation=params['activation'], name="pool1")
    # Output: 60x90x64

    # (2) Filter size: 3x3x64
    conv2 = cnn_2d(pool1, 3, params['channels'][1], activation=params['activation'], name="conv2")
    pool2 = max_and_cnn_layer(conv1, 2, params['channels'][1], activation=params['activation'], name="pool2")
    # Output: 30x45x64

    # (3.1) Max Pool, then Filter size: 64
    pool3_1 = max_pool_layer(pool2, 3, "pool3_1", stride=1)  # Special stride to keep same dimension
    conv3_1 = cnn_2d(pool3_1, 1, params['channels'][2], activation=params['activation'], name="conv3_1")
    # Output: 30x45x64

    # (3.2) Filter size: 1x1x64, then 3x3x64
    conv3_2 = cnn_2d(pool2, 1, params['channels'][3], activation=params['activation'], name="conv3_2_1")
    conv3_2 = cnn_2d(conv3_2, 3, params['channels'][4], activation=params['activation'], name="conv3_2")
    # Output: 30x45x64

    # (3.3) Filter size: 1x1x64, then 5x5x64
    conv3_3 = cnn_2d(pool2, 1, params['channels'][5], activation=params['activation'], name="conv3_3_1")
    conv3_3 = cnn_2d(conv3_3, 3, params['channels'][6], activation=params['activation'], name="conv3_3_2")
    conv3_3 = cnn_2d(conv3_3, 3, params['channels'][7], activation=params['activation'], name="conv3_3_3")
    # conv3_3 = cnn_2d(conv3_3, 5, 64)  # Might use 2 3x3 CNN instead, look at inception net paper
    # Output: 30x45x64

    # (3.4) Filter size: 1x1x256
    conv3_4 = cnn_2d(pool2, 1, params['channels'][8], activation=params['activation'], name="conv3_4")
    # Output: 30x45x64

    concat4 = tf.concat([conv3_1, conv3_2, conv3_3, conv3_4], 3)
    total_layer = params['channels'][2] + params['channels'][4] + params['channels'][7] + params['channels'][8]
    pool4 = max_and_cnn_layer(concat4, 3, total_layer, activation=params['activation'], name="pool4")
    # Output: 10x15x256 = 38400

    fc5 = flatten_layer(pool4)
    fc5 = fc_layer(fc5, params['channels'][9], activation=params['activation'], name='fc5')
    dropout5 = tf.keras.layers.Dropout(rate=params['dropout_rate'])(fc5)

    fc6 = fc_layer(dropout5, params['channels'][10], activation=params['activation'], name='fc6')
    dropout6 = tf.keras.layers.Dropout(rate=params['dropout_rate'])(fc6)

    # logits = fc_layer(dropout6, 11, activation=params['activation'], name='predict')
    logits = fc_layer(dropout6, 3, activation=tf.nn.tanh, name='predict')  # Regression with one output
    return logits


def get_loss_weight(labels):  # Calculate loss weight of a single batch
    score_one = tf.reduce_sum(tf.cast(tf.equal(labels, tf.constant(0, dtype=tf.int64)), dtype=tf.float32))
    score_three = tf.reduce_sum(tf.cast(tf.equal(labels, tf.constant(1, dtype=tf.int64)), dtype=tf.float32))
    score_five = tf.reduce_sum(tf.cast(tf.equal(labels, tf.constant(2, dtype=tf.int64)), dtype=tf.float32))
    sum_total = score_one + score_three + score_five
    # Add 1 to all denominator to prevent overflow
    weight = tf.stack(
        [tf.math.divide(sum_total, score_one + 1), tf.math.divide(sum_total, score_three + 1),
         tf.math.divide(sum_total, score_five + 1)],
        axis=0)
    return tf.expand_dims(weight, axis=0)


def custom_l2_reg(loss, lambda_=0.01):
    # Reference: https://stackoverflow.com/questions/55029716/how-to-regularize-loss-function
    ys = tf.reduce_mean(loss)
    l2_norms = [tf.nn.l2_loss(v) for v in tf.trainable_variables()]
    l2_norm = tf.reduce_sum(l2_norms)
    print("L2 norm:", lambda_ * l2_norm)
    print("Loss:", ys)
    loss = ys + lambda_ * l2_norm
    return loss, lambda_ * l2_norm


def adjust_image(data):
    # Reshape to [batch, height, width, channels].
    imgs = tf.reshape(data, [-1, 299, 299, 1])
    # Adjust image size to Inception-v3 input.
    imgs = tf.image.resize_images(imgs, (299, 299))
    # Convert to RGB image.
    imgs = tf.image.grayscale_to_rgb(imgs)
    return imgs


def customized_inceptnet2(features, model, params):
    module = hub.Module("https://tfhub.dev/google/imagenet/inception_v3/feature_vector/1")
    input_layer = adjust_image(features)
    outputs = module(input_layer)
    logits = tf.keras.layers.Dense(3, activation='relu', name="new_dense_8")(outputs)
    return logits


# Define Model
def my_model(features, labels, mode, params, config):
    # Input: (Batch_size,240,360,4)
    params['activation'] = tf.nn.leaky_relu
    logits = customized_inceptnet2(features['image'], mode, params)
    print("Labels", labels)
    print("Logits", logits)
    # logits = tf.squeeze(logits, 1)
    # logits_aft = tf.math.scalar_mul(5, logits) + 5
    # Predict Mode
    predicted_class = tf.argmax(logits, 1)
    if mode == tf.estimator.ModeKeys.PREDICT:
        predictions = {
            'score': predicted_class[:, tf.newaxis],
            'probabilities': tf.nn.softmax(logits),
            'logits': logits
        }
        return tf.estimator.EstimatorSpec(mode=mode, predictions=predictions)

    labels = (labels - 1) / 2  # Convert score from 1,3,5 to 0,1,2
    one_hot_label = tf.one_hot(indices=tf.cast(labels, tf.int32), depth=3)
    labels = tf.cast(labels, tf.int64)

    # Use loss weight based on each batch
    if mode == tf.estimator.ModeKeys.TRAIN:
        loss_weight_raw = get_loss_weight(labels)
        loss_weight = tf.matmul(one_hot_label, loss_weight_raw, transpose_b=True, a_is_sparse=True)
    else:
        loss_weight = 1.0
    # Cross-entropy loss
    loss = tf.losses.sparse_softmax_cross_entropy(labels, logits, weights=loss_weight)  # labels is int of class, logits is vector
    loss, reg_loss = custom_l2_reg(loss, lambda_=0.01)
    # loss = tf.losses.sparse_softmax_cross_entropy(labels, logits)  # Not applicable for score

    accuracy = tf.metrics.accuracy(labels, predicted_class)
    my_accuracy = tf.reduce_mean(tf.cast(tf.equal(labels, predicted_class), dtype=tf.float32))
    acc = tf.summary.scalar("accuracy_manual", my_accuracy)  # Number of correct answer
    # acc2 = tf.summary.scalar("Accuracy_update", accuracy[1])

    # img1 = tf.summary.image("Input_image1", tf.expand_dims(features[:, :, :, 0], 3))
    # img2 = tf.summary.image("Input_image2", tf.expand_dims(features[:, :, :, 1], 3))
    # img3 = tf.summary.image("Input_image3", tf.expand_dims(features[:, :, :, 2], 3))
    # img4 = tf.summary.image("Input_image4", tf.expand_dims(features[:, :, :, 3], 3))

    ex_prediction = tf.summary.scalar("example_prediction", predicted_class[0])
    ex_ground_truth = tf.summary.scalar("example_ground_truth", labels[0])

    trainable_variable_name = [v.name for v in tf.trainable_variables()]

    d_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES)
    # tf.summary for all weight and bias
    summary_weight = []
    for i, t in enumerate(trainable_variable_name):
        summary_weight.append(tf.summary.histogram(t, tf.trainable_variables()[i]))
    steps = tf.train.get_global_step()

    # global_step = tf.summary.scalar("Global steps",tf.train.get_global_step())

    # Train Mode
    if mode == tf.estimator.ModeKeys.TRAIN:
        steps = tf.train.get_global_step()
        learning_rate = tf.train.exponential_decay(params['learning_rate'], steps,
                                                   20000, 0.96, staircase=True)
        optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
        train_op = optimizer.minimize(loss, global_step=steps)
        save_steps = 1000
        saver_hook = tf.train.SummarySaverHook(save_steps=1000, summary_op=tf.summary.merge_all(),
                                               output_dir=config.model_dir)
        # model_vars = tf.trainable_variables()
        # slim.model_analyzer.analyze_vars(model_vars, print_info=True)
        print_input_hook = PrintValueHook(features['image'], "Input value", tf.train.get_global_step(), save_steps)
        print_input_min_hook = PrintValueHook(tf.math.reduce_min(features['image']), "Min Input value", tf.train.get_global_step(), save_steps)
        print_input_name_hook = PrintValueHook(features['name'], "Input name", tf.train.get_global_step(), save_steps)
        print_logits_hook = PrintValueHook(tf.nn.softmax(logits), "Training logits", tf.train.get_global_step(),
                                           save_steps)
        print_label_hook = PrintValueHook(labels, "Labels", tf.train.get_global_step(), save_steps)
        print_lr_hook = PrintValueHook(learning_rate, "Learning rate", tf.train.get_global_step(), save_steps)
        print_loss_hook = PrintValueHook(loss, "Total Loss", tf.train.get_global_step(), save_steps)
        print_reg_loss_hook = PrintValueHook(reg_loss, "Regularization Loss", tf.train.get_global_step(), save_steps)

        print_weight_balance_hook = PrintValueHook(loss_weight_raw, "Loss weight", tf.train.get_global_step(),
                                                   save_steps)
        train_hooks = [saver_hook,
                       print_input_hook, print_input_name_hook,print_input_min_hook,
                       print_logits_hook,print_label_hook,
                       print_lr_hook,
                       print_loss_hook, print_reg_loss_hook,
                       print_weight_balance_hook,
                       ]
        return tf.estimator.EstimatorSpec(mode=mode, loss=loss, train_op=train_op, training_hooks=train_hooks)

    # Evaluate Mode
    print("Evaluation Mode")
    # Create result(.csv) file, if not exist
    # If change any header here, don't forget to change data in EvalResultHook (custom_hook.py)
    if not os.path.isfile(params['result_path']):
        with open(os.path.join(params['result_path'], params['result_file_name']), "w") as csvfile:
            fieldnames = ['Name', 'Label', 'Predicted Class', 'Confident level', 'All confident level']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    # Evaluate Mode
    eval_hooks = []
    if params['result_file_name'] == 'train_result.csv':
        saver_hook = tf.train.SummarySaverHook(save_steps=10, summary_op=tf.summary.merge_all(),
                                               output_dir=os.path.join(config.model_dir, 'train_final'))
    else:
        saver_hook = tf.train.SummarySaverHook(save_steps=10, summary_op=tf.summary.merge_all(),
                                               output_dir=os.path.join(config.model_dir, 'eval'))
    csv_name = tf.convert_to_tensor(os.path.join(params['result_path'], params['result_file_name']), dtype=tf.string)
    print_result_hook = EvalResultHook(features['name'], labels, predicted_class, tf.nn.softmax(logits), csv_name)
    eval_hooks.append(saver_hook)
    eval_hooks.append(print_result_hook)
    return tf.estimator.EstimatorSpec(mode=mode, eval_metric_ops={'accuracy': accuracy}, loss=loss,
                                      evaluation_hooks=eval_hooks)
