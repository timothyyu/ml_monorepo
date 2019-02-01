# stochastic-blockmodel

## Overview
I wanted to have some practice implementing a stochastic block model, and some algorithms that deal with its detection and model recovery. This project will allow one to generate, detect, and recover them.

## Definition
From [Wikipedia](https://en.wikipedia.org/wiki/Stochastic_block_model):

The stochastic block model takes the following parameters:

* The number *n* of vertices
* a partition of the vertex set {1, ..., n} into disjoint subsets {C_1, ..., C_r} called communities
* a symmetric r x r matrix P of edge probabilities.
The edge set is then sampled at random as follows: any two vertices u in C_i and v in C_j are connected by an edge with probability P_ij.

## Generate
One can generate an SBM by doing the following:

```python
from sbm.sbm import SBM

num_vertices = 5  # number of unique vertices
num_communities = 3  # number of communities
community_labels = [0, 1, 1, 0, 2]  # community label assigned to each vertices
p_matrix = [
  [.5, .3, .2],
  [.6, .2, .2],
  [.2, .4, .4],
]

model = SBM(num_vertices, num_communities, community_labels, p_matrix)

print model.block_matrix
```
The SBM.block_matrix returned is a 2D numpy array representing the edges that are present (1), and not present (0).
```python
array([[1, 1, 0, 0, 0],
       [1, 0, 0, 1, 0],
       [0, 0, 0, 1, 0],
       [1, 1, 0, 1, 0],
       [0, 1, 0, 1, 1]])
```

## Detection

## Recovery

## Papers
Here are a list of papers that I have found resourceful (some overlapping topics):
* http://tuvalu.santafe.edu/~aaronc/courses/5352/fall2013/csci5352_2013_L16.pdf
* https://arxiv.org/abs/1503.00609v2
* http://arxiv.org/abs/1512.09080v3
* https://arxiv.org/abs/1405.3267v4
* https://arxiv.org/abs/1506.03729v1
* https://arxiv.org/abs/1202.1499v4
