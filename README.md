# Chord Protocol In Python
A basic implementation of the [Chord protocol](https://pdos.csail.mit.edu/papers/chord:sigcomm01/chord_sigcomm.pdf) in python.

This is NOT a full distributed hash table as that is just one of the possible applications of the chord protocol.

As such, it just manages nodes based on a hash of their location (ip, port) and finds which node is responsible for a given hash.

Namely, a node is responsible for a hash k if the node's hash is the first node hash that comes after k modulo the maximum hash value.

The visualizer is a flask app that starts and kills nodes with a minimalist brower user interface.
When new nodes are added the nodes get a yellow outline for a little while so you can keep track of them as they join the network and the ring gets reordered. Additionally, you can click a node and it will turn and stay green until clicked again.

# Usage
(Note: a virtual environment is recommended)
## To run nodes (no visualizer): 
First install dependencies using pip:
```
pip install -r requirements.txt 
```

For first node in the terminal run:
```
python node.py -p PORT
```
with PORT being some usable port like 8889

And for additional node, open another terminal and run:
```
python node.py -k "127.0.0.1 PORT"
```

The options are as follows:
- p selects which port the node will listen on
- k says to try and join the chord ring with a node running at the given location.

## To use the visualizer:
First go to the visualizer directory and install the dependencies:
```
cd visualizer
pip install -r requirements.txt
```

Then start the server with:
```
flask run
```
Then open a browser and go to "localhost:5000".

NOTE: There's a bug where adding a few nodes and then leaving it for a while cause nodes to fail. This doesn't happen when running the nodes on their own so I think it's something to do with Popen not playing nice with the rest of the program. If I had to guess it would have something to do with multiple processes trying to print at the same time but that's a bit of a wild guess.
