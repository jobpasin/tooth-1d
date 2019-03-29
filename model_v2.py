import tensorflow as tf
# tf.enable_eager_execution()
import numpy as np


# Default stride of 1, padding:same
def cnn_2d(layer,
           conv_filter_size,  # [Scalar] Kernel size
           num_filters,  # [Scalar]
           activation=tf.nn.relu,
           stride=1,
           name=''):  # Stride of CNN
    # We shall define the weights that will be trained using create_weights function.
    layer = tf.keras.layers.Conv2D(num_filters, conv_filter_size, strides=stride, padding="same",
                                   activation=activation)(layer)
    return layer
    # TODO: Find way to show weight


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


def max_and_cnn_layer(layer, pooling_size, num_filters, activation, name):
    pool = tf.keras.layers.MaxPooling2D(pooling_size, stride, padding="same")(layer)
    conv = tf.keras.layers.Conv2D(num_filters, pooling_size, strides=pooling_size, padding="same",
                                  activation=activation)(layer)
    concat = tf.keras.layers.concatenate([pool, conv], 3)
    return concat


'''
def dropout(layer, dropout_rate, training, name):
    return tf.layers.dropout(layer, rate=dropout_rate, training=training, name=name)
'''


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

    logits = fc_layer(dropout6, 11, activation=params['activation'], name='predict')
    return logits


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

    logits = fc_layer(dropout6, 11, activation=params['activation'], name='predict')
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

    logits = fc_layer(dropout6, 11, activation=params['activation'], name='predict')
    return logits


# Define Model
def my_model(features, labels, mode, params, config):
    # Input: (Batch_size,240,360,4)
    logits = customized_incepnet_v2(features, mode, params)

    # Predict Mode
    predicted_class = tf.argmax(input=logits, axis=1)
    if mode == tf.estimator.ModeKeys.PREDICT:
        predictions = {
            'score': predicted_class[:, tf.newaxis],
            'probabilities': tf.nn.softmax(logits),
            'logits': logits
        }
        return tf.estimator.EstimatorSpec(mode=mode, predictions=predictions)
    loss = tf.compat.v1.losses.sparse_softmax_cross_entropy(labels, logits)  # tf.losses.sparse_categorical_crossentropy
    accuracy = tf.compat.v1.metrics.accuracy(labels, predicted_class)
    my_accuracy = tf.reduce_mean(input_tensor=tf.cast(tf.equal(labels, predicted_class), dtype=tf.float32))
    acc = tf.compat.v1.summary.scalar("accuracy_manual", my_accuracy)  # Number of correct answer
    # acc2 = tf.summary.scalar("Accuracy_update", accuracy[1])

    img1 = tf.compat.v1.summary.image("Input_image1", tf.expand_dims(features[:, :, :, 0], 3))
    img2 = tf.compat.v1.summary.image("Input_image2", tf.expand_dims(features[:, :, :, 1], 3))
    img3 = tf.compat.v1.summary.image("Input_image3", tf.expand_dims(features[:, :, :, 2], 3))
    img4 = tf.compat.v1.summary.image("Input_image4", tf.expand_dims(features[:, :, :, 3], 3))

    ex_prediction = tf.compat.v1.summary.scalar("example_prediction", predicted_class[0])
    # print(predicted_class[0])
    ex_ground_truth = tf.compat.v1.summary.scalar("example_ground_truth", labels[0])
    # print(labels[0])

    d_vars = tf.compat.v1.get_collection(tf.compat.v1.GraphKeys.TRAINABLE_VARIABLES)
    # print(d_vars)
    summary_name = ["conv1", "conv2", "conv3_1", "conv3_2_1", "conv3_2", "conv3_3_1",
                    "conv3_3_2", "conv3_3_3", "conv4", "fc5", "fc6", "predict"]
    if len(summary_name) == int(len(d_vars) / 2):
        for i in range(len(summary_name)):
            tf.compat.v1.summary.histogram(summary_name[i] + "_weights", d_vars[2 * i])
            tf.compat.v1.summary.histogram(summary_name[i] + "_biases", d_vars[2 * i + 1])
    else:
        print("Warning, expected weight&variable not equals")
        print(d_vars)

    summary = tf.compat.v1.summary.histogram("Prediction", predicted_class)
    summary2 = tf.compat.v1.summary.histogram("Ground_Truth", labels)
    # global_step = tf.summary.scalar("Global steps",tf.train.get_global_step())

    # Train Mode
    if mode == tf.estimator.ModeKeys.TRAIN:
        steps = tf.compat.v1.train.get_global_step()
        learning_rate = tf.keras.optimizers.schedules.ExponentialDecay(
            params['learning_rate'],
            decay_steps=20000,
            decay_rate=0.96,
            staircase=True)
        # learning_rate = tf.compat.v1.train.exponential_decay(params['learning_rate'], steps,
        #                                            20000, 0.96, staircase=True)
        optimizer = tf.compat.v1.train.AdamOptimizer(learning_rate=learning_rate)
        train_op = optimizer.minimize(loss, global_step=steps)
        saver_hook = tf.estimator.SummarySaverHook(save_steps=1000, summary_op=tf.compat.v1.summary.merge_all(),
                                                   output_dir=config.model_dir)
        # model_vars = tf.trainable_variables()
        # slim.model_analyzer.analyze_vars(model_vars, print_info=True)
        return tf.estimator.EstimatorSpec(mode=mode, loss=loss, train_op=train_op, training_hooks=[saver_hook])

    # Evaluate Mode
    saver_hook = tf.estimator.SummarySaverHook(save_steps=10, summary_op=tf.compat.v1.summary.merge_all(),
                                               output_dir=config.model_dir + 'eval')
    return tf.estimator.EstimatorSpec(mode=mode, eval_metric_ops={'accuracy': accuracy}, loss=loss,
                                      evaluation_hooks=[saver_hook])