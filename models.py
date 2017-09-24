from keras import backend as K
from keras.models import (
    Sequential,
    Model
)
from keras.layers import (
    Activation,
    AveragePooling2D,
    BatchNormalization,
    Convolution2D,
    Dense,
    Dropout,
    Flatten,
    GlobalAveragePooling2D,
    Input,
    MaxPooling2D,
    merge,
)
from keras.regularizers import l2
from keras.applications import resnet50, InceptionV3


def channel_axis():
    if K.image_dim_ordering() == 'tf':
        return 3
    else:
        return 1

def load_simple_cnn(input_shape, n_classes, weight_decay):
    model = Sequential()

    model.add(Convolution2D(
        64, 3, 3, border_mode='same',
        input_shape=input_shape,
        init='he_normal',
        W_regularizer=l2(weight_decay)))
    model.add(BatchNormalization(
        mode=0,
        axis=channel_axis(),
        gamma_regularizer=l2(weight_decay),
        beta_regularizer=l2(weight_decay)
    ))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Convolution2D(
        64, 3, 3, border_mode='same',
        init='he_normal',
        W_regularizer=l2(weight_decay)))
    model.add(BatchNormalization(
        mode=0,
        axis=channel_axis(),
        gamma_regularizer=l2(weight_decay),
        beta_regularizer=l2(weight_decay)
    ))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Convolution2D(
        64, 3, 3, border_mode='same',
        init='he_normal',
        W_regularizer=l2(weight_decay)))
    model.add(BatchNormalization(
        mode=0,
        axis=channel_axis(),
        gamma_regularizer=l2(weight_decay),
        beta_regularizer=l2(weight_decay)
    ))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))


    model.add(Flatten())
    model.add(Dense(512, W_regularizer=l2(weight_decay), bias=False))
    model.add(BatchNormalization(
        mode=0,
        axis=-1,
        gamma_regularizer=l2(weight_decay),
        beta_regularizer=l2(weight_decay)
    ))
    model.add(Activation('relu'))
    model.add(Dropout(0.5))
    model.add(Dense(n_classes, W_regularizer=l2(weight_decay)))
    model.add(Activation('softmax'))

    return model

def load_resnet(input_shape, n_classes, depth, weight_decay, widen):

    wd = weight_decay

    def bnrelu(x_input):
        x_output = BatchNormalization(
            mode=0,
            axis=channel_axis(),
            gamma_regularizer=l2(wd),
            beta_regularizer=l2(wd))(x_input)
        x_output = Activation('relu')(x_output)
        return x_output

    def basic_block(x, n_input, n_output, stride):

        resmap = bnrelu(x)

        if n_input != n_output:
            x = resmap

        resmap = Convolution2D(
            n_output, 3, 3,
            init='he_normal',
            border_mode='same',
            subsample=(stride, stride),
            bias=False,
            W_regularizer=l2(wd))(resmap)

        resmap = bnrelu(resmap)

        resmap = Convolution2D(
            n_output, 3, 3,
            init='he_normal',
            border_mode='same',
            subsample=(1,1),
            bias=False,
            W_regularizer=l2(wd))(resmap)

        if n_input == n_output:
            skip = x # Identity skip connection
        else:
            skip = Convolution2D(
                n_output, 1, 1,
                init='he_normal',
                border_mode='same',
                subsample=(stride, stride),
                bias=False,
                W_regularizer=l2(wd))(x)

        return merge([resmap, skip], mode='sum')

    def stage(x, n_input, n_output, n_block, stride):
        x = basic_block(x, n_input, n_output, stride)
        for i in range(n_block - 1):
            x = basic_block(x, n_output, n_output, 1)
        return x

    stages = [16, 16*widen, 32*widen, 64*widen]
    if (depth - 4) % 6 != 0:
        error(Exception("depth must be 6n+4."))
    n_block = int((depth - 4) / 6)

    # Create model
    x_input = Input(shape=input_shape)
    x = Convolution2D(
        stages[0], 3, 3,
        init='he_normal',
        border_mode='same',
        subsample=(1,1),
        bias=False,
        W_regularizer=l2(wd))(x_input) # spatial size 32x32
    x = stage(x, stages[0], stages[1], n_block, 1) # spatial size 32x32
    x = stage(x, stages[1], stages[2], n_block, 2) # spatial size 16x16
    x = stage(x, stages[2], stages[3], n_block, 2) # spatial size 8x8
    x = bnrelu(x)
    x = GlobalAveragePooling2D()(x)
    x = Dense(
        n_classes,
        init='glorot_uniform',
        W_regularizer=l2(wd))(x)
    x_output = Activation('softmax')(x)
    model = Model(input=x_input, output=x_output)

    return model


def load_resnet50_imagenet(n_classes, weight_decay):
    base_model = resnet50.ResNet50(weights='imagenet', include_top=False)
    for layer in base_model.layers:
        layer.trainable = False
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(n_classes, W_regularizer=l2(weight_decay))(x)
    x = Activation('softmax')(x)

    return Model(input=base_model.input, output=x)

def load_inception_imagenet(n_classes, weight_decay):
    base_model = InceptionV3(weights='imagenet', include_top=False)

    for layer in base_model.layers:
        layer.trainable = False
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(n_classes, W_regularizer=l2(weight_decay), activation='relu')(x)
    x = Activation('softmax')(x)
    return Model(input=base_model.input, output=x)


def load_model(net_type, input_shape, n_classes, depth, weight_decay, widen):
    if net_type == 'simple':
        model = load_simple_cnn(input_shape, n_classes, weight_decay)
    elif net_type == 'resnet':
        model = load_resnet(input_shape, n_classes, depth, weight_decay, widen)
    elif net_type == 'resnet50imagenet':
        model = load_resnet50_imagenet(n_classes, weight_decay)
    elif net_type == 'inceptionv3':
        model = load_inception_imagenet(n_classes, weight_decay)
    else:
        raise("Invalid net_type.")
    return model
