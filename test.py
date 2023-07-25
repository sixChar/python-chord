import asyncio
import time
import os, sys, signal
import random
from node import request_ping
from subprocess import Popen, PIPE
from collections import namedtuple


Node = namedtuple('Node', ['proc','loc'])

def test_schedule(schedule, log_num=0):
    nodes = []
    log_file = open(f'logs/log_{log_num}.txt','w')
    schedule_file = open('logs/schedule_file.txt', 'a')
    try:
        for action in schedule:
            print(f"Doing action: {action}")
            time.sleep(action['delay'])
            if action['type'] == 'spawn':
                node = Popen(
                    [sys.executable, '-u', 'node.py'] + action['args'],
                    stdout=PIPE,
                    stderr=log_file,
                    text=True,
                    bufsize=1
                )
                host, port = node.stdout.readline().strip().split(' ')[-2:]
                host = host[2:-2]
                port = int(port[:-1])
                nodes.append(Node(node, (host,port)))
                print(nodes[-1].loc)

            elif action['type'] == 'ping' and len(nodes) > 0:
                if action['args'][0] >= len(nodes):
                    asyncio.run(ascyncio.wait_for(request_ping(*nodes[-1].loc), 5))
                else:
                    asyncio.run(asyncio.wait_for(request_ping(*nodes[action['args'][0]].loc), 5))
            elif action['type'] == 'kill' and len(nodes) > 0:
                if action['args'][0] >= len(nodes):
                    nodes[-1].proc.send_signal(signal.SIGINT)
                    nodes[-1].proc.wait()
                    nodes.pop()
                else:
                    idx = action['args'][0]
                    nodes[idx].proc.send_signal(signal.SIGINT)
                    nodes[idx].proc.wait()
                    del nodes[idx] 
    except Exception as e:
        schedule_file.write(f"\n{log_num}:\n")
        schedule_file.write(f"Schedule:\n")
        schedule_file.writelines(f"{action}\n" for action in schedule)
        schedule_file.write(f"\nException: \n{str(e)}\n\n")
        
    finally:        
        # Clean up
        for node in nodes:
            node.proc.send_signal(signal.SIGINT)
        for node in nodes:
            node.proc.wait()
        log_file.close()
        schedule_file.close()


def make_action(delay, typ, args):
    return {'delay': delay, 'type': typ, 'args': args}
 

def rand_schedule(num_nodes=None, max_time=100):
    if num_nodes == None:
        num_nodes = random.randint(1, 10)

    spawn_prob = 0.3
    kill_prob = 0.3
    
    nodes_spawned = 0
    nodes_alive = 0
    time = 0
    schedule = []
    while nodes_spawned < num_nodes and time < max_time:
        decider = random.random()
        delay = (random.random() ** (num_nodes - nodes_spawned)) * (max_time - time)
        time += delay
        if nodes_alive <= 0 or decider < spawn_prob:
            args = ['-p', '8889'] if nodes_alive == 0 else ['-k', '127.0.0.1 8889']
            schedule.append(make_action(delay, 'spawn', args))
            nodes_spawned += 1
            nodes_alive += 1
        elif decider < spawn_prob + kill_prob:
            to_kill = random.randint(0, nodes_alive-1)
            schedule.append(make_action(delay, 'kill', [to_kill]))
            nodes_alive = nodes_alive - 1
        else:
            to_ping = random.randint(0, nodes_alive-1)
            schedule.append(make_action(delay, 'ping', [to_ping]))
    while nodes_alive > 0:
        to_kill = random.randint(0, nodes_alive-1)
        schedule.append(make_action(delay, 'kill', [to_kill]))
        nodes_alive = nodes_alive - 1
    return schedule
        


if __name__=="__main__":
    sample_schedule = [
            {'delay': 1.1, 'type': 'spawn', 'args': ['-p', '8889']},
            {'delay': 1.1, 'type': 'spawn', 'args': ['-k', '127.0.0.1 8889']},
            {'delay': 1.1, 'type': 'spawn', 'args': ['-k', '127.0.0.1 8889']},
            {'delay': 10, 'type': 'ping', 'args': [1]},
            {'delay': 1.1, 'type': 'spawn', 'args': ['-k', '127.0.0.1 8889']},
            {'delay': 10, 'type': 'kill', 'args': [1]},
            {'delay': 1.1, 'type': 'spawn', 'args': ['-k', '127.0.0.1 8889']},
            {'delay': 10, 'type': 'kill', 'args': [0]},
            {'delay': 10, 'type': 'kill', 'args': [0]},
            {'delay': 10, 'type': 'kill', 'args': [0]},
            {'delay': 10, 'type': 'kill', 'args': [0]},

    ]

    if 'logs' not in os.listdir():
        os.mkdir('logs')


    for i in range(100):
        schedule = rand_schedule(max_time = 1000)
        test_schedule(schedule, log_num=i)

    


















