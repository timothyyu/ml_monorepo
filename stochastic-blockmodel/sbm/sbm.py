# -*- coding: utf-8 -*-
import logging
import random

import numpy as np


class SBM(object):

    def __init__(self, num_vertices, communities, vertex_labels, p_matrix):
        logging.info('Initializing SBM Model ...')
        self.num_vertices = num_vertices
        self.communities = communities
        self.vertex_labels = vertex_labels
        self.p_matrix = p_matrix
        self.block_matrix = self.generate(self.num_vertices, self.communities, self.vertex_labels, self.p_matrix)

    def detect(self):
        logging.info('SBM detection ...')
        pass

    def generate(self, num_vertices, num_communities, vertex_labels, p_matrix):
        logging.info('Generating SBM (directed graph) ...')
        v_label_shape = (1, num_vertices)
        p_matrix_shape = (num_communities, num_communities)
        block_matrix_shape = (num_vertices, num_vertices)
        block_matrix = np.zeros(block_matrix_shape, dtype=int)

        for row, _row in enumerate(block_matrix):
            for col, _col in enumerate(block_matrix[row]):
                community_a = vertex_labels[row]
                community_b = vertex_labels[col]

                p = random.random()
                val = p_matrix[community_a][community_b]

                if p <= val:
                    block_matrix[row][col] = 1

        return block_matrix

    def recover(self):
        logging.info('SBM recovery ...')
        pass
