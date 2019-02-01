# -*- coding: utf-8 -*-
import tensorflow as tf
import numpy as np
from custom_lstm import CustomBasicLSTMCell
from constants import FEATURES_LIST, SEQUENCE_LENGTH

# Actor-Critic Network Base Class
# (Policy network and Value network)

class GameACNetwork(object):
  def __init__(self,
               action_size,
               device="/cpu:0"):
    self._device = device
    self._action_size = action_size

  def prepare_loss(self, entropy_beta):
    with tf.device(self._device):
      # taken action (input for policy)
      self.a = tf.placeholder("float", [None, self._action_size])
    
      # temporary difference (R-V) (input for policy)
      self.td = tf.placeholder("float", [None])
      
      # policy entropy
      entropy = -tf.reduce_sum(self.pi * tf.log(self.pi), reduction_indices=1)

      ##self.pi = tf.Print(self.pi, [self.pi], message="This is self.pi: ", summarize=40)
      ##self.a = tf.Print(self.a, [self.a], message="This is self.a: ", summarize=40)
      
      # policy loss (output)  (add minus, because this is for gradient ascent)
      policy_loss = - tf.reduce_sum( tf.reduce_sum( tf.mul( tf.log(self.pi), self.a ), reduction_indices=1 ) * self.td + entropy * entropy_beta )

      # R (input for value)
      self.r = tf.placeholder("float", [None])
      
      # value loss (output)
      # (Learning rate for Critic is half of Actor's, so multiply by 0.5)
      ##print("HHH",self.r.get_shape())
      ##print("HHH",self.v.get_shape())
      ##self.r = tf.Print(self.r, [self.r], message="This is self.r: ", summarize=40)
      ##self.v = tf.Print(self.v, [self.v], message="This is self.v: ", summarize=40)
      value_loss = 0.5 * tf.nn.l2_loss(self.r - self.v)

      # gradienet of policy and value are summed up
      self.total_loss = policy_loss + value_loss

  def run_policy_and_value(self, sess, s_t):
    raise NotImplementedError()
    
  def run_policy(self, sess, s_t):
    raise NotImplementedError()

  def run_value(self, sess, s_t):
    raise NotImplementedError()    

  def get_vars(self):
    raise NotImplementedError()

  def sync_from(self, src_netowrk, name=None):
    src_vars = src_netowrk.get_vars()
    dst_vars = self.get_vars()

    sync_ops = []

    with tf.device(self._device):
      with tf.op_scope([], name, "GameACNetwork") as name:
        for(src_var, dst_var) in zip(src_vars, dst_vars):
          sync_op = tf.assign(dst_var, src_var)
          sync_ops.append(sync_op)

        return tf.group(*sync_ops, name=name)

  # weight initialization based on muupan's code
  # https://github.com/muupan/async-rl/blob/master/a3c_ale.py
  def _fc_weight_variable(self, shape):
    """
        shape[0] ... number of input channels 
        shape[1] ... number of nodes 
    """
    input_channels = shape[0]
    d = 1.0 / np.sqrt(input_channels)
    initial = tf.random_uniform(shape, minval=-d, maxval=d)
    return tf.Variable(initial)

  def _fc_bias_variable(self, shape, input_channels):
    """
        shape[0] ... number of nodes 
        input channels ... number of input channels 
    """
    d = 1.0 / np.sqrt(input_channels)
    initial = tf.random_uniform(shape, minval=-d, maxval=d)
    return tf.Variable(initial)  

  def _conv_weight_variable(self, shape):
    """ shape: 
           shape[0] w ... width of a filter
           shape[1] h ... height of a filter
           shape[2]   ... number of input channels
           shape[3]   ... number of filters in output
    """
    w = shape[0] #width of a filter
    h = shape[1] #height of a filter 
    input_channels = shape[2] #number of input channels

    d = 1.0 / np.sqrt(input_channels * w * h)
    initial = tf.random_uniform(shape, minval=-d, maxval=d)
    return tf.Variable(initial)

  def _conv_bias_variable(self, shape, w, h, input_channels):
    """ shape: 
           shape[0]  ... number of output channels
            w ... width of a filter
            h ... height of a filter
            input_channels  ... number of input channels
    """
    d = 1.0 / np.sqrt(input_channels * w * h)
    initial = tf.random_uniform(shape, minval=-d, maxval=d)
    return tf.Variable(initial)

  def _conv2d(self, x, W, stride):
    return tf.nn.conv2d(x, W, strides = [1, stride, stride, 1], padding = "VALID")

# Actor-Critic FF Network

class GameACFFNetwork(GameACNetwork):
  def __init__(self,
               action_size,
               device="/cpu:0"):
    GameACNetwork.__init__(self, action_size, device)
    print("Initializing Conv FF Network ")
    
    with tf.device(self._device):

      # 8 ... length of a filter
      # 2nd dim is 1 since we have a one dimensional input
      # 16 filters in total
      self.W_conv1 = self._conv_weight_variable([8, 1, len(FEATURES_LIST), 16])  # stride=4
      self.b_conv1 = self._conv_bias_variable([16], 8, 1, len(FEATURES_LIST))

      # 32 filters in total
      # with a size of 1x1 - does this make sense?
      self.W_conv2 = self._conv_weight_variable([1, 1, 16, 32]) # stride=2
      self.b_conv2 = self._conv_bias_variable([32], 1, 1, 16)

      self.W_fc1 = self._fc_weight_variable([2592, 256])
      self.b_fc1 = self._fc_bias_variable([256], 2592 )

      # 256 must be larger than SEQUENCE_LENGTH
      # weight for policy output layer
      self.W_fc2 = self._fc_weight_variable([256, action_size])
      self.b_fc2 = self._fc_bias_variable([action_size], 256)

      # weight for value output layer
      self.W_fc3 = self._fc_weight_variable([256, 1])
      self.b_fc3 = self._fc_bias_variable([1], 256)

      self.s = tf.placeholder("float", [None, SEQUENCE_LENGTH, 1, len(FEATURES_LIST)])

      h_conv1 = tf.nn.relu(self._conv2d(self.s, self.W_conv1, 1) + self.b_conv1)
      h_conv2 = tf.nn.relu(self._conv2d(h_conv1, self.W_conv2, 2) + self.b_conv2)

      h_conv2_flat = tf.reshape(h_conv2, [-1, 2592])
      h_fc1 = tf.nn.relu(tf.matmul(h_conv2_flat, self.W_fc1) + self.b_fc1)

      # policy (output)
      self.pi = tf.nn.softmax(tf.matmul(h_fc1, self.W_fc2) + self.b_fc2)
      # value (output)
      v_ = tf.matmul(h_fc1, self.W_fc3) + self.b_fc3
      self.v = tf.reshape( v_, [-1] )
      #print("SHAPE ", self.v.get_shape())

  def run_policy_and_value(self, sess, s_t):
    pi_out, v_out = sess.run( [self.pi, self.v], feed_dict = {self.s : [s_t]} )
    return (pi_out[0], v_out[0])

  def run_policy(self, sess, s_t):
    pi_out = sess.run( self.pi, feed_dict = {self.s : [s_t]} )
    return pi_out[0]

  def run_value(self, sess, s_t):
    v_out = sess.run( self.v, feed_dict = {self.s : [s_t]} )
    return v_out[0]

  def get_vars(self):
    return [self.W_conv1, self.b_conv1,
            self.W_conv2, self.b_conv2,
            self.W_fc1, self.b_fc1,
            self.W_fc2, self.b_fc2,
            self.W_fc3, self.b_fc3]

# ActorCritic dilated Conv network

class GameACDilatedNetwork(GameACFFNetwork):

  def __init__(self,
               action_size,
               device="/cpu:0"):
    print("Initializing Dilated Conv Network")
    GameACNetwork.__init__(self, action_size, device)

    
    with tf.device(self._device):
      filter_length = 5

      self.W_dilconv1 = self._conv_weight_variable([filter_length, 1, len(FEATURES_LIST), 16])  # stride=4
      self.b_dilconv1 = self._conv_bias_variable([16], filter_length, 1, len(FEATURES_LIST))

      # 32 filters in total
      # with a size of 1x1 - does this make sense?
      self.W_dilconv2 = self._conv_weight_variable([filter_length, 1, 16, 32]) # stride=2
      self.b_dilconv2 = self._conv_bias_variable([32], filter_length, 1, 16)

      self.W_dilconv3 = self._conv_weight_variable([filter_length, 1, 32, 32]) # stride=2
      self.b_dilconv3 = self._conv_bias_variable([32], filter_length, 1, 32)

      #self.W_fc1 = self._fc_weight_variable([64896, 256]) # When using only 2 dilated levels
      #self.b_fc1 = self._fc_bias_variable([256], 64896 )

      self.W_fc1 = self._fc_weight_variable([SEQUENCE_LENGTH * 32, 256]) # for 3 dilation levels
      self.b_fc1 = self._fc_bias_variable([256], SEQUENCE_LENGTH * 32, )

      # 256 must be larger than SEQUENCE_LENGTH
      # weight for policy output layer
      self.W_fc2 = self._fc_weight_variable([256, action_size])
      self.b_fc2 = self._fc_bias_variable([action_size], 256)
 
      # end of replacement
      # weight for value output layer
      self.W_fc3 = self._fc_weight_variable([256, 1])
      self.b_fc3 = self._fc_bias_variable([1], 256)

      self.s = tf.placeholder("float", [None, SEQUENCE_LENGTH, 1, len(FEATURES_LIST)])

      #h_dilconv1 = tf.nn.relu(self._conv2d(self.s, self.W_dilconv1, 1) + self.b_dilconv1)
      dilation1 = 1
      dilation2 = 2
      dilation3 = 4
      filter_length1 = filter_length
      filter_length2 = filter_length
      filter_length3 = filter_length
      h_dilconv1 = tf.nn.relu(self._dilconv(self.s, self.W_dilconv1, self.b_dilconv1, filter_length1, dilation1))
      h_dilconv2 = tf.nn.relu(self._dilconv(h_dilconv1, self.W_dilconv2, self.b_dilconv2, filter_length2, dilation2))
      h_dilconv3 = tf.nn.relu(self._dilconv(h_dilconv2, self.W_dilconv3, self.b_dilconv3, filter_length3, dilation3))
      print("Dilated output shape: {}".format(h_dilconv3.get_shape()))

      #h_conv2_flat = tf.reshape(h_dilconv2, [-1, 64896]) # when using 2 dilated levels
      h_conv2_flat = tf.reshape(h_dilconv3, [-1, SEQUENCE_LENGTH * 32])

      h_fc1 = tf.nn.relu(tf.matmul(h_conv2_flat, self.W_fc1) + self.b_fc1)

      # policy (output)
      self.pi = tf.nn.softmax(tf.matmul(h_fc1, self.W_fc2) + self.b_fc2)
      # value (output)
      v_ = tf.matmul(h_fc1, self.W_fc3) + self.b_fc3
      self.v = tf.reshape( v_, [-1] )
      print("SHAPE ", self.v.get_shape())

  def get_vars(self):
    return [self.W_dilconv1, self.b_dilconv1,
            self.W_dilconv2, self.b_dilconv2,
            self.W_fc1, self.b_fc1,
            self.W_fc2, self.b_fc2,
            self.W_fc3, self.b_fc3]

  def _dilconv(self, x, w, b, filter_length, dilation):
    print("Tensor before padding: {}".format(x))
    padding = [[0, 0], [dilation * (filter_length - 1), 0], [0, 0], [0, 0]]
    x = tf.pad(x, padding)
    print("Tensor after padding: {}".format(x))

    if dilation == 1:
        x = tf.nn.conv2d(x, w, [1, 1, 1, 1], padding='VALID')
    else:
        print("x.shape", x.get_shape())
        print("w.shape", w.get_shape())
        x = tf.nn.atrous_conv2d(x, w, dilation, padding='VALID')
    print("Tensor after (dil)conv: {}".format(x))

    return x + b

# Actor-Critic LSTM Network

class GameACLSTMNetwork(GameACNetwork):
  def __init__(self,
               action_size,
               thread_index, # -1 for global
               device="/cpu:0" ):
    GameACNetwork.__init__(self, action_size, device)    
    print("Initializing LSTM Network ")

    with tf.device(self._device):
      self.W_conv1 = self._conv_weight_variable([8, 1, len(FEATURES_LIST), 16])  # stride=4
      self.b_conv1 = self._conv_bias_variable([16], 8, 1, len(FEATURES_LIST))

      self.W_conv2 = self._conv_weight_variable([1, 1, 16, 32]) # stride=2
      self.b_conv2 = self._conv_bias_variable([32], 1, 1, 16)

      self.W_fc1 = self._fc_weight_variable([2592, 256])
      self.b_fc1 = self._fc_bias_variable([256], 2592 )

      # lstm
      self.lstm = CustomBasicLSTMCell(256)

      # 256 must be larger than SEQUENCE_LENGTH
      # weight for policy output layer
      self.W_fc2 = self._fc_weight_variable([256, action_size])
      self.b_fc2 = self._fc_bias_variable([action_size], 256)

      # weight for value output layer
      self.W_fc3 = self._fc_weight_variable([256, 1])
      self.b_fc3 = self._fc_bias_variable([1], 256)

      # state (input)
      #self.s = tf.placeholder("float", [None, 84, 84, 4])
      self.s = tf.placeholder("float", [None, SEQUENCE_LENGTH, 1, len(FEATURES_LIST)])
    
      h_conv1 = tf.nn.relu(self._conv2d(self.s, self.W_conv1, 1) + self.b_conv1)
      h_conv2 = tf.nn.relu(self._conv2d(h_conv1, self.W_conv2, 2) + self.b_conv2)

      h_conv2_flat = tf.reshape(h_conv2, [-1, 2592])
      h_fc1 = tf.nn.relu(tf.matmul(h_conv2_flat, self.W_fc1) + self.b_fc1)
      # h_fc1 shape=(5,256)
      ##h_fc1 = tf.Print(h_fc1, [h_fc1], message="NN This is h_fc1: ", summarize=40)

      h_fc1_reshaped = tf.reshape(h_fc1, [1,-1,256])
      # h_fc_reshaped = (1,5,256)

      self.step_size = tf.placeholder(tf.float32, [1])

      self.initial_lstm_state = tf.placeholder(tf.float32, [1, self.lstm.state_size])
      
      scope = "net_" + str(thread_index)

      # time_major = False, so output shape is [batch_size, max_time, cell.output_size]
      lstm_outputs, self.lstm_state = tf.nn.dynamic_rnn(self.lstm,
                                                        h_fc1_reshaped,
                                                        initial_state = self.initial_lstm_state,
                                                        sequence_length = self.step_size,
                                                        time_major = False,
                                                        scope = scope)

      # lstm_outputs: (1,5,256), (1,1,256)
      
      lstm_outputs = tf.reshape(lstm_outputs, [-1,256])

      # policy (output)
      self.pi = tf.nn.softmax(tf.matmul(lstm_outputs, self.W_fc2) + self.b_fc2)
      ##self.pi = tf.Print(self.pi, [self.pi], message="NN This is self.pi: ", summarize=40)
      
      # value (output)
      v_ = tf.matmul(lstm_outputs, self.W_fc3) + self.b_fc3
      ##v_ = tf.Print(v_, [v_], message="NN This is v_ ", summarize=40)
      self.v = tf.reshape( v_, [-1] )
      ##self.v = tf.Print(self.v, [self.v], message="NN This is self.v: ", summarize=40)

      # in OK  tensorflow/core/kernels/logging_ops.cc:79] NN This is self.v: [-0.036351625]
      #I tensorflow/core/kernels/logging_ops.cc:79] NN This is self.pi: [0.49193981 0.50806022]
      #I tensorflow/core/kernels/logging_ops.cc:79] NN This is self.v: [-0.03456594]

      self.reset_state()
      print("Initializing Network finished")
      
  def reset_state(self):
    self.lstm_state_out = np.zeros([1, self.lstm.state_size])

  def run_policy_and_value(self, sess, s_t):
    pi_out, v_out, self.lstm_state_out = sess.run( [self.pi, self.v, self.lstm_state],
                                                   feed_dict = {self.s : [s_t],
                                                                self.initial_lstm_state : self.lstm_state_out,
                                                                self.step_size : [1]} )
    # pi_out: (1,3), v_out: (1)
    return (pi_out[0], v_out[0])

  def run_policy(self, sess, s_t):
    pi_out, self.lstm_state_out = sess.run( [self.pi, self.lstm_state],
                                            feed_dict = {self.s : [s_t],
                                                         self.initial_lstm_state : self.lstm_state_out,
                                                         self.step_size : [1]} )
                                            
    return pi_out[0]

  def run_value(self, sess, s_t):
    prev_lstm_state_out = self.lstm_state_out
    v_out, _ = sess.run( [self.v, self.lstm_state],
                         feed_dict = {self.s : [s_t],
                                      self.initial_lstm_state : self.lstm_state_out,
                                      self.step_size : [1]} )
    
    # roll back lstm state
    self.lstm_state_out = prev_lstm_state_out
    return v_out[0]

  def get_vars(self):
    return [self.W_conv1, self.b_conv1,
            self.W_conv2, self.b_conv2,
            self.W_fc1, self.b_fc1,
            self.lstm.matrix, self.lstm.bias,
            self.W_fc2, self.b_fc2,
            self.W_fc3, self.b_fc3]


