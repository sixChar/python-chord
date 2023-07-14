# Chord Protocol In Python
A basic implementation of the [Chord protocol](https://pdos.csail.mit.edu/papers/chord:sigcomm01/chord_sigcomm.pdf) in python.

This is NOT a full distributed hash table as that is just one of the possible applications of the chord protocol.

As such, it just manages nodes based on a hash of their location (ip, port) and finds which node is responsible for a given hash.

Namely, a node is responsible for a hash k if the node's hash is the first node hash that comes after k modulo the maximum hash value.

