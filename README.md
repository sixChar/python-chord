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

### Visualizer demonstration
[chord-visualizer-in-action.webm](https://github.com/sixChar/python-chord/assets/17972996/3dfd8823-04af-4540-a6d8-18b73d58b920)

### Notes on the visualizer:
- Nodes are represented by squares with their port number next to them and a line to their predecessor.
- They are kept ordered based on which nodes are predecessors to others (i.e. by node id, which is a hash of their address).
- Newly added nodes are given a yellow highlight until they have joined the network (some node has recognized them as that node's predecessor) and some time has passed. This is to help keep track of newly added nodes as the order tends to change once their part of the network. 


NOTE: There's a bug where adding a few nodes and then leaving it for a while cause nodes to fail. This doesn't happen when running the nodes on their own so I think it's something to do with Popen not playing nice with the rest of the program. Since it only affects the visualizer when it's used in a weird way and seems difficult to fix I'm not going to bother.

