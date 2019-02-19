'''Dataset preprocessing.'''
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import concurrent.futures
import os

import numpy as np

import wavenet.utils as utils

BATCH = 10240
RATE = 8000
CHUNK = 1600


def split_into(data, n):
    res = []
    for i in range(n):
        res.append(data[i::n])
    return res


def process_files(files, id, output, rate, chunk_length, batch):
    data = []
    ofilename = os.path.join(output, 'vctk_{}'.format(id))
    with open(ofilename, 'wb') as ofile:
        for filename in files:
            for chunk in utils._preprocess(filename, rate, chunk_length):
                data.append(chunk)

            if len(data) >= batch:
                np.save(ofile, np.array(data))
                data.clear()
        np.save(ofile, np.array(data))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str, default=os.getcwd())
    parser.add_argument('--output', type=str, default='')
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--rate', type=int, default=RATE)
    parser.add_argument('--stacks_num', type=int, default=5)
    parser.add_argument('--layers_num', type=int, default=10)
    parser.add_argument('--target_length', type=int, default=CHUNK)
    parser.add_argument('--flush_every', type=int, default=BATCH)
    args = parser.parse_args()

    files = list(utils.wav_files_in(args.data))
    file_groups = split_into(files, args.workers)

    size = utils.receptive_field_size(args.layers_num, args.stacks_num) + args.target_length

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i in range(args.workers):
            pool.submit(process_files, file_groups[i], i, args.output, args.rate,
                        size, args.flush_every)


if __name__ == '__main__':
    main()
