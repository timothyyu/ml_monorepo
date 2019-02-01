ufcnn
=====

Implementation of Undecimated Fully Convolutional Neural Network for time
series modeling. See the [paper](http://arxiv.org/abs/1508.00317).

This algorithm learns a sequence-to-sequnce predictor in the form of a
multi-layer neural network composed exclusively of convolutional layers.

In order to learn information on wide range of time scales, the convolution
filters are gradually *dilated* on each new level, i.e. zeros are implicitly
inserted between their values. This approach is different from a more
conventional approach of downsampling-upsampling layer pairs. It has an
advantage of providing the translation equivariance --- the desired property
in time series modeling.

You are advised to read [this](http://www.inference.vc/dilated-convolutions-and-kronecker-factorisation/)
excellent note for details about the dilated convolution.

Installation
------------
Clone the repository and append the path to `PYTHONPATH`.

Dependencies
------------
During the development the following setup was used:

- numpy 1.11.0
- tensorflow built from the latest source
- Should work in Python 2 and 3

Example
-------
The examples shows how to create and train the model.
```Python
import tensorflow as tf
from ufcnn import construct_ufcnn, mse_loss
from ufcnn.datasets import generate_tracking

# Generate data.
X_train, Y_train = generate_tracking(200, 500)
X_test, Y_test = generate_tracking(20, 500)

# Create the network.
x, y_hat, *_ = construct_ufcnn(n_outputs=2, n_levels=2)

# Create a placeholder for truth sequences.
y = tf.placeholder(tf.float32, shape=(None, None, 2))

# Define the MSE loss and RMSProp optimizer over it.
loss = mse_loss(y_hat, y)
optimizer = tf.train.RMSPropOptimizer(learning_rate=0.001)
train_step = optimizer.minimize(loss)

# Run several epochs of optimization.
session = tf.Session()
session.run(tf.initialize_all_variables())

print("{:^7}{:^7}".format("Epoch", "Loss"))

batch_size = 20
n_batch = X_train.shape[0] // batch_size
n_epochs = 20

for epoch in range(n_epochs):
    if epoch % 5 == 0:
        mse = session.run(loss, feed_dict={x: X_test, y: Y_test})
        print("{:^7}{:^7.2f}".format(epoch, mse))
    for b in range(n_batch):
        X_batch = X_train[b * batch_size : (b + 1) * batch_size]
        Y_batch = Y_train[b * batch_size : (b + 1) * batch_size]
        session.run(train_step, feed_dict={x: X_batch, y: Y_batch})

mse = session.run(loss, feed_dict={x: X_test, y: Y_test})
print("{:^7}{:^7.2f}".format(n_epochs , mse))
```

Output:
```
 Epoch  Loss  
   0    51.32 
   5    23.35 
  10    20.45 
  15    14.08 
  20    8.97  

```
We see that the optimizer progresses reasonably fast and we can expect some
predicting power if we train the network long enough.
