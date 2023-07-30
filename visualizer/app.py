from flask import Flask, render_template, jsonify
import asyncio
import sys
import os
import signal
import subprocess
import re

parentdir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(parentdir)
from node import request_successors

app = Flask(__name__)

nodes = []

def cleanup():
    for node in nodes:
        node.send_signal(signal.SIGINT)
    for node in nodes:
        node.wait()


@app.route('/', methods=["GET"])
def root():
    return render_template("index.html")


@app.route('/add')
def add_node():
    global nodes
    if len(nodes) == 0:
        args = ['-p', '8889']
    else:
        args = ['-k', '127.0.0.1 8889']
    # Create a new node using the same executable as is running flask with line-buffered
    # stdout which this program can read from.
    node_proc = subprocess.Popen(
            [sys.executable, '-u', '../node.py'] + args, 
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
    )
    # Use the output of the node to get loc in case where it binds to random port
    host,port = node_proc.stdout.readline().strip().split(' ')[-2:]
    host = host[2:-2]
    port = int(port[:-1])
    nodes.append({'proc':node_proc, 'loc':(host,port)})
    return jsonify({'node':nodes[-1]['loc']})


@app.route('/remove')
def remove_node():
    global nodes
    if len(nodes) > 0:
        to_delete = nodes[-1]['loc']
        nodes[-1]['proc'].send_signal(signal.SIGINT)
        nodes = nodes[:-1]
        return jsonify({'node':to_delete})
    else:
        return jsonify({'node': None})


@app.route('/node-count')
def node_count():
    return f"{len(nodes)}"


@app.route('/node-info')
def node_info():
    global nodes
    ret = {'nodes':[]}
    for i,node in enumerate(nodes):
        successors = asyncio.run(request_successors(*node['loc']))
        ret['nodes'].append({
            'pid': node['proc'].pid,
            'loc': node['loc'],
            'successors': list(dict.fromkeys(successors))
        })
    return jsonify(ret)




