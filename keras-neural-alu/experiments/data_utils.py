import numpy as np

# Make index selection deterministic as well
np.random.seed(0)

static_index = np.arange(0, 100, dtype=np.int64)
np.random.shuffle(static_index)


def generate_static_dataset(op_fn, num_samples=1000, mode='interpolation',
                            seed=0):
    """
    Generates a dataset given an operation and a mode of working.
    Used to generate the synthetic static dataset.

    # Arguments:
        op_fn: A function which accepts 2 numpy arrays as arguments
            and returns a single numpy array as the result.
        num_samples: Number of samples for the dataset.
        mode: Can be one of `interpolation` or `extrapolation`
        seed: random seed

    Returns:

    """
    assert mode in ['interpolation', 'extrapolation']
    assert callable(op_fn)

    np.random.seed(seed)  # make deterministic

    print("Generating dataset")

    # Get the input stream
    X = np.random.rand(num_samples, 100)

    if mode == 'extrapolation':
        X *= 2.

    # Select the slices on which we will perform the operation
    a_index, b_index = static_index[:(len(static_index) // 2)], static_index[(len(static_index) // 2):]
    a = X[:, a_index]
    b = X[:, b_index]

    # Get the sum of the slices
    a = np.sum(a, axis=-1, keepdims=True)
    b = np.sum(b, axis=-1, keepdims=True)

    # perform the operation on the slices in order to get the target
    Y = op_fn(a, b)

    return X, Y


def generate_recurrent_dataset(op_fn, num_samples=1000, mode='interpolation'):
    """
        Generates a recurrent dataset given an operation and a mode
        of working. Used to generate the synthetic static dataset.

        # Arguments:
            op_fn: A function which accepts 2 numpy arrays as arguments
                and returns a single numpy array as the result.
            num_samples: Number of samples for the dataset.
            num_timesteps: Number of timesteps of the dataset.
            mode: Can be one of `interpolation` or `extrapolation`

        Returns:

        """
    assert mode in ['interpolation', 'extrapolation']
    assert callable(op_fn)

    np.random.seed(0)  # make deterministic

    if mode == 'interpolation':
        num_timesteps = 10
    else:
        num_timesteps = 1000

    # Get the input stream
    X = np.random.random(size=(num_samples, num_timesteps, 10))

    # Select the slices on which we will perform the operation
    a_index, b_index = static_index[:num_samples // 2], static_index[num_samples // 2:]
    a = X[:, :, a_index]
    b = X[:, :, b_index]

    # Get the sum of the slices
    a = np.sum(a, axis=[1, 2], keepdims=True)
    b = np.sum(b, axis=[1, 2], keepdims=True)

    X = np.concatenate([a, b], axis=1)

    # perform the operation on the slices in order to get the target
    Y = op_fn(a, b)

    return X, Y


if __name__ == '__main__':
    fn = lambda x, y: x + y
    x, y = generate_static_dataset(fn)
