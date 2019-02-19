# Keras Neural Arithmatic and Logical Unit (NALU)
A Keras implementation of Neural Arithmatic and Logical Unit from the paper [Neural Arithmetic Logic Units](https://arxiv.org/abs/1808.00508).

Contains the layers for `Neural Arithmatic Logic Unit (NALU)` and `Neural Accumulator (NAC)`.

# Usage

Simply add them as normal layers after importing `nalu.py` or `nac.py`.

`NALU` has several additional parameters, the most important of which is whether to apply the gating mechanism or not

- `use_gating` is True by default, enabling the behaviour from the paper.
- Resetting `use_gating` allows the layer to model more complex expressions.

```python
from nalu import NALU


ip = Input(...)
x = NALU(10, use_gating=True)(ip)
...
```

## Note
Generally, NALU does **not** use an activation function after its output - though they may be applied anyway.

# Static Toy Experiments
The static toy test is implemented inside the `experiments` folder, though it is not an exact replica of the paper as the details about how much the extrapolated dataset deviates from the train set is somewhat vague (the paper only mentions that at least one of `a`, `b` and `y` are increased in the extrapolated set, but not by how much and what mechanism.

Here, the extrapolated dataset is built by doubling `X` before performing the operation.

All of the tests are done using either Adam or RMSProp optimizers (RMSProp seems to be extremely useful to solve the toy tasks in particular, taking only 15% of the time that Adam would take on the same setup (though weight initialization cannot be guarenteed to be same in Keras, so that will affect this measure).

Almost all task are performed and weights are provided. Several obtain scores similar to the Table 1 in the paper, however the losses (train and extrapolated test set) of the `Squaring` and `Multiplication` operations are extremely high, and is not affected by either optimizer to any significant degree.

This is possibly due to the way I compute the extrapolated set as the double of `X`, which causes values of `a` and `b` to be vastly out of the training range.

## Results

---------------------------------------------------
| Operation | Train Loss | Extrapolated Test Loss |
|-----------|------------|------------------------|
|  a + b    | 0.0        |       0.0              |
|  a - b    | 0.0        |       0.0              |
|  a * b    | **> 1e5** |      **> 1e5**      |
|  a / b    | 0.006      |       0.0308           |
|  a ^ 2    | **> 1e5** |       **> 1e5**        |
|  sqrt (a) | 0.001      |       0.035            |

# Requirements

- Tensorflow (Tested) | Theanp | CNTK
- Keras 2+

