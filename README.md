# BitCoin-Puzzle
This repo contains a couple of Python scripts containing different approaches to solve the "Bitcoin Puzzle" (see https://nickyreinert.medium.com/the-bitcoin-puzzle-66132a735b16 and https://privatekeys.pw/puzzles/bitcoin-puzzle-tx).

All scripts have a main entry point where you need to adjust solving target, e.g:

  if __name__ == '__main__':
      target_address = '1HsMJxNiV7TLxmoF6uJNkydxPFDog4NQum'
      num_workers = 12
      measure_performance(19, 20, target_address, num_workers)

* target_address defines the public wallet address that you are looking for
* num_works defines how many computing units you want to utilize
* the first argument of measure_performance (19) deines the exponent of the lower limit of the search range (2^19)
* the second argument of measure_performance (20) deines the exponent of the lower limit of the search range (2^20 - 1)

# Different evolutions
## bitcoinPuzzle.ipynb
Naive implementation of a solver for the Bitcoin puzzle with no further improvements. It's goal is to understand how the solving algorithm works.

## bitcoinPuzzle-v1.py
An implementation that implements parallel computing. 

## bitcoinPuzzle-v2.py
This contains a small evolution step only explaining how to cut the search range into multiple smaller batches. 

## bitcoinPuzzle-v3.py
Another small step only that explain how to use a global flag to stop as soons as a result has been found. 

## bitcoinPuzzle-v4.pyx and bitcoinPuzzle-v4-setup.py
This step shows how to further decrease processing time by pre-compiling the Python script using Cython. It also implemnent a hack, that randomly picks a batch. 

## bitcoinPuzzle_v5.ipynb
A small notebook comparing the processing time of all required algorithms:
* SECP2556k1
* SHA-256 with hashlib, Crypto.Hash, cryptography and a C implementation via pyopencl
* RIPEMD-160
* BASE-58
