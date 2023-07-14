'''
    Implementation of the chord protocol in python.
'''
import asyncio
from asyncio import wait_for
import argparse
import json
from hashlib import sha256
from typing import Optional, Callable, Awaitable, cast
from typing_extensions import TypeAlias
from enum import IntEnum, auto

StreamReader: TypeAlias = asyncio.streams.StreamReader
StreamWriter: TypeAlias = asyncio.streams.StreamWriter

# Timeout before giving open on opening a connection
CONNECTION_TIMEOUT: float = 5.0
# Timeout before giving up on a request_**** method
REQUEST_TIMEOUT: float = 10.0
# Interval between running stabilize method
STABILIZE_INTERVAL: float = 3.0
# Interval between running fix_fingers method
FIX_FINGERS_INTERVAL: float = 3.0
# Interval between checking if predecessor is still alive
CHECK_PREDECESSOR_INTERVAL: float = 3.0
# Interval between retrying to join the network if an attempt to join fails
RETRY_JOIN_INTERVAL: float = 5.0

# All hashes (ids) < max hash
MAX_HASH: int = 2**256 - 1
# Bytes to transmit a hash
NUM_HASH_BYTES: int = 32
# Maximum number of direct successors to keep track of 
MAX_NUM_SUCCESSORS: int = 32


# Maximum number of entries in the finger table
MAX_NUM_FINGER: int = 256
# Finger table for faster lookup e.g. [node responsible for my_id + 1, ..., my_id + 2^i ]
finger_table: list[tuple[bytes, tuple[str, int]]] = []
# Indec of next entry in finger table to look up
next_fix: int = 0

# List of immediate successors (e.g. [successor, successor's successor, ...])
succ_list: list[tuple[bytes, tuple[str, int]]] = []
# Id of this node's predecessor
pred_id: Optional[bytes] = None
# (host, port) of predecessor
pred_loc: Optional[tuple[str, int]] = None

# We're casting None to other types here because we know these should be set at the start and this way the type checker doesn't complain
# for every use of the variable that isn't explicitly cast.
# Ip address that this node reads requests from
my_host: str = cast(str, None)
# Port that this node reads requests from
my_port: int = cast(int, None)
# My node id
my_id: bytes = cast(bytes, None)

'''
  Codes for the different requests the node can receive
'''
class Request(IntEnum):
    PING = 1
    NOTIFY = auto()
    REQUEST_PRED = auto()
    REQUEST_SUCC = auto()
    CLOSEST_PRECEDING = auto()

'''
  Generate the hash of (host, port) i.e. the node id
'''
def hash(host: str, port: int) -> bytes:
    return sha256(json.dumps((host, port)).encode()).digest()

'''
    Checks if the test_id is in the open interval (low_id, high_id) on the ring.
    If right_closed is true then the interval is (low_id, high_id]
'''
def id_between(test_id: bytes, low_id: bytes, high_id: bytes, right_closed: bool = False) -> bool:
    # Note that an id a is between b and c on the ring if b < a < c or (because ring
    # wraps)  a < b < c or c < b < a
    if right_closed:
        return (test_id > low_id and test_id <= high_id) or \
                (low_id >= high_id and (test_id > low_id or test_id <= high_id)) or \
                (low_id == high_id)
    else:
        return (test_id > low_id and test_id < high_id) or \
                (low_id >= high_id and (test_id > low_id or test_id < high_id)) or \
                (low_id == high_id and test_id != low_id)


'''
    Get the hash that results from adding to_add to idn modulo the maximum hash
'''
def add_to_id(idn: bytes, to_add: int) -> bytes:
    id_int = int.from_bytes(idn, "big", signed=False)
    result = (id_int + to_add) % MAX_HASH
    return result.to_bytes(NUM_HASH_BYTES, 'big')


'''
    Reads a variable lengh number of bytes from reader where the first 4
    bytes define the length of the message
'''
async def read_msg(reader: StreamReader) -> bytes:
    msg_len = int.from_bytes(await reader.read(4), 'big')
    msg = await reader.read(msg_len)
    return msg


'''
    Returns the length of msg (in 4 bytes) concatenated with msg         
'''
def add_len(msg: bytes) -> bytes:
    msg_len = len(msg).to_bytes(4, 'big')
    return msg_len + msg


'''
    Find the node who's id is the first in the ring that comes after find_id.
'''
async def find_successor(find_id: bytes) -> tuple[bytes, tuple[str, int]]:
    global succ_list
    # Try to get the successor's successor. If this fails then delete it and go to
    # next in successor list
    while len(succ_list) > 0:
        curr_id, (curr_host, curr_port) = succ_list[0]
        try:
            next_node = await wait_for(
                    request_successors(curr_host, curr_port), 
                    REQUEST_TIMEOUT
            )
            break
        except Exception as e:
            succ_list = succ_list[1:]
            if len(finger_table) > 0:
                finger_table[0] = succ_list[0]
    # If no more successors alive, then make this node it's own successor and return this node since it's now the only node in the ring.
    if len(succ_list) == 0:
        succ_list = [(my_id, (my_host, my_port))]
        return (my_id, (my_host, my_port))

    if next_node != None:
        # Next node should be a list of length 1 so we let the type checker know it's 
        # not None and take it out of the list.
        next_host, next_port = cast(list[tuple[str, int]], next_node)[0]  
    else:
        return (curr_id, (my_host, my_port))

    while True:
        if next_host == None or next_port == None:
            # curr doesn't know any other nodes so they are the only node and therefore responsible for
            # all keys including this one or there is a break in the ring
            return (curr_id, (curr_host, curr_port))
        else:
            # Neither next_host nor next_port are None, let the type checker know
            next_host, next_port = cast(str, next_host), cast(int, next_port)
            next_id = hash(next_host, next_port)
            # If the id we are looking for is between curr and it's successor next then
            # next is responsible for it.
            if id_between(find_id, curr_id, next_id, right_closed=True):
                return next_id, (next_host, next_port)
        curr_id = next_id
        curr_host = next_host
        curr_port = next_port
        try:
            # Try to get the closest node before the find_id that curr knows about
            next_host, next_port = await wait_for(
                  request_closest_preceding(find_id, curr_host, curr_port),
                  REQUEST_TIMEOUT
            )
        except Exception as e:
            raise Exception(((curr_host, curr_port), e))


'''
    Send a requst to the node at host:port to get the closest node before the find_id
    that the node at host:port knows about.
'''
async def request_closest_preceding(find_id: bytes, host: str, port:int) -> tuple[Optional[str], Optional[int]]:
    reader: StreamReader
    writer: StreamWriter
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), CONNECTION_TIMEOUT)
    except Exception as e:
        print(f"Failure to connect to {host}:{port} : {e}")
        raise e        

    # Tell the other node what id we are looking for.
    message = Request.CLOSEST_PRECEDING.to_bytes(1, "big") + add_len(find_id)
    writer.write(message)
    await writer.drain()

    loc = json.loads((await read_msg(reader)).decode())
    if loc == None:
        return None, None
    else:
        return loc


'''
    Handle a request to get the node that this node knows about that is the closest to
    a transmitted id while still being before it in the ring.
'''
async def handle_closest_preceding(reader: StreamReader, writer: StreamWriter) -> None:
    print("Request for closest preceding.")
    find_id = await read_msg(reader)
    # Search the finger table for the largest node that is between this node and
    # find_id. That is: my_id < node_id < find_id (modulo)
    for n_id, n_loc in reversed(finger_table):
        if id_between(n_id, my_id, find_id):
            message = add_len(json.dumps(n_loc).encode())
            writer.write(message)
            await writer.drain()
            writer.close()
            return
    # Send back the location. Id is not included since that can easily be calculated by
    # requester.
    message = add_len(json.dumps((my_host, my_port)).encode())
    writer.write(message)
    await writer.drain()
    writer.close()
    return


'''
    Join the network that the node at host:port is a part of.
'''
async def join(host: str, port: int):
    global succ_list, finger_table
    succ_list.append((hash(host, port), (host, port)))
    # Repeatedly try to join until success
    while True:
        print(f"Attempting to join at {host}:{port} ...  ", end="")
        try:
            succ_list[0] = await find_successor(my_id)
            finger_table.append(succ_list[-1])
            print("Success!")
            break
        except Exception as e:
            print("Failed!")
            print(e)
            print("Waiting {RETRY_JOIN_INTERVAL} seconds before retrying.")
            await asyncio.sleep(RETRY_JOIN_INTERVAL)


'''
    Update this node's successor list to the most current state and let it's successor
    know about itself.
'''
async def stabilize() -> None:
    global succ_list, finger_table
    while len(succ_list) > 0:
        # Try to stabilize with successor. If it fails delete and move onto next in 
        # successor list.
        try:
            succ_id, succ_loc = succ_list[0]
            x_host, x_port = await wait_for(
                    request_predecessor(*succ_loc),
                    REQUEST_TIMEOUT
            )
            # If successor doesn't have a predecessor tell it about us.
            if x_host == None or x_port == None:
                await wait_for(
                        request_notify(*succ_loc),
                        REQUEST_TIMEOUT
                )
            else:
                x_host, x_port = cast(str, x_host), cast(int, x_port)
                x_id = hash(x_host, x_port)
                # If successor's predecessor (x) is after us update them to be our successor
                if id_between(x_id, my_id, succ_id):
                    succ_list[0] = (x_id, (x_host, x_port))
                    if len(finger_table) > 0:
                        finger_table[0] = (succ_id, succ_loc)
                    else:
                        finger_table.append((succ_id, succ_loc))
                # If we are a closer successor than x let our successor know about us.
                elif x_id != my_id:
                    await wait_for(
                            request_notify(*succ_loc),
                            REQUEST_TIMEOUT
                    )
            # Get our successor's successor list (succ's list)
            succs_succ_addrs =  await wait_for(
                    request_successors(*succ_list[0][1], 0),
                    REQUEST_TIMEOUT
            )
            # If succ's list is not None update our list to be [successor, succ's list]
            # with the last entries cut off to fit the maximum number of successors
            # we're keeping track of.
            if succs_succ_addrs != None:
                succs_succ_addrs = cast(list[tuple[str, int]], succs_succ_addrs)
                succs_succ_list = list(map(lambda x: (hash(*x), x), succs_succ_addrs))
                succ_list = [succ_list[0]] + succs_succ_list[:MAX_NUM_SUCCESSORS-1]
            break
        except Exception as e:
            print(f"Error stabilizing with successor:{succ_list[0][1]} : {e}\nSkipping to next in successor list.")
            if len(finger_table) > 0 and len(succ_list) > 0:
                if finger_table[0][0] == succ_list[0][0]:
                    # Remove immediate successor from finger table if it failed
                    finger_table = finger_table[1:]
            if len(succ_list) > 0:
                succ_list = succ_list[1:]
            else:
                succ_list = [(my_id, (my_host, my_port))]
                break
    print(succ_list[0], len(finger_table))


'''
    Update the finger table to reflect the current state of the network. 
'''
async def fix_fingers():
    global next_fix, finger_table, succ_list
    if len(finger_table) > 0 or len(succ_list) > 0:
        try:
            next_fix = next_fix + 1
            if next_fix >= MAX_NUM_FINGER:
                # Reset to start
                next_fix = 0
            elif next_fix >= len(finger_table):
                test_id, test_loc = await find_successor(add_to_id(my_id, 2 ** next_fix))
                # If the finger table is empty or the node that would be the next added to the finger table
                # is between the last finger table entry and this node add a new finger table entry
                if len(finger_table) == 0 or id_between(test_id, finger_table[-1][0], my_id):
                    finger_table.append((test_id, test_loc))
                else:
                    # Reset to start
                    next_fix = 0
            else:
                finger_table[next_fix] = await find_successor(add_to_id(my_id, 2 ** next_fix))
        except Exception as e:
            # If failed to contact successor, replace successor with next in list
            if e.args[0][0] == succ_list[0][1]:
                succ_list = succ_list[1:]
                finger_table[0] = succ_list[0]


'''
    Check if predecessor is alive and if not forget it.
'''
async def check_predecessor():
    global pred_id, pred_loc
    if pred_id != None and pred_loc != None:
        try:
            resp = (await wait_for(request_ping(*pred_loc), REQUEST_TIMEOUT)).decode()
            print(f"Response to ping: {resp}")
        except Exception as e:
            pred_id, pred_loc = None, None


'''
    Send a request for a ping to the node at host:port.    
'''
async def request_ping(host: str, port: int) -> bytes:
    reader: StreamReader
    writer: StreamWriter
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), CONNECTION_TIMEOUT)
    except Exception as e:
        print(f"Failure to connect to {host}:{port} : {e}")
        raise e        

    writer.write(Request.PING.to_bytes(1, "big"))
    await writer.drain()
    

    return await read_msg(reader)


'''
    Handle a ping request.
'''
async def handle_ping(reader: StreamReader, writer: StreamWriter):
    print("Request for ping.")
    # Send back any message as string
    message = "pong".encode()
    writer.write(add_len(message))
    await writer.drain()
    writer.close()


'''
    Send a request to the node at host:port to notify said node that we believe
    this node is it's immediate predecessor in the ring
'''
async def request_notify(host: str, port: int) -> None:
    reader: StreamReader
    writer: StreamWriter
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), CONNECTION_TIMEOUT)
    except Exception as e:
        print(f"Failure to connect to {host}:{port} : {e}")
        raise e        

    message = Request.NOTIFY.to_bytes(1, "big") + \
                add_len(json.dumps((my_host, my_port)).encode())
    writer.write(message)
    await writer.drain()

    resp = await read_msg(reader)
    print(f"Response to notify: {resp.decode()}")


'''
    Handle a request from a node that thinks it is this node's immediate predecessor
'''
async def handle_notify(reader: StreamReader, writer: StreamWriter) -> None:
    print("Request for notify.")
    global pred_id, pred_loc
    peername = writer.get_extra_info("peername")
    cand_loc = tuple(json.loads((await read_msg(reader)).decode()))

    if type(cand_loc[0]) != str or type(cand_loc[1]) != int:
        writer.write(add_len(b"\x01refused: location sent doesn't not match type (str, int)"))
        await writer.drain()
        writer.close()
        return

    cand_loc = cast(tuple[str, int], cand_loc)
    cand_id = hash(*cand_loc)

    if peername[0] != cand_loc[0]:
        # Check that cand ip matches sender (i.e. notify is sent from the notifier)
        writer.write(add_len(b"\x01refused: ip doesn't match sender"))
    elif pred_id == None or pred_loc == None:
        # If no predecessor then cand is accepted
        pred_id, pred_loc = cand_id, cand_loc
        writer.write(add_len(b"\x00accepted"))
    else:
        pred_id, pred_loc = cast(bytes, pred_id), cast(tuple[str, int], pred_loc)
        if id_between(cand_id, pred_id, my_id):
            # If the notifier is between pred and this node, it replaces pred
            pred_id, pred_loc = cand_id, cand_loc
            writer.write(add_len(b"\x00accepted"))
        else:
            writer.write(add_len(b"\x01refused: is not between current predecessor and self"))
    await writer.drain()
    writer.close()



'''
    Send a request to the node at host:port for the location of it's current predecessor.
'''
async def request_predecessor(host: str, port: int) -> tuple[Optional[str], Optional[int]]:
    reader: StreamReader
    writer: StreamWriter
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), CONNECTION_TIMEOUT)
    except Exception as e:
        print(f"Failure to connect to {host}:{port} : {e}")
        raise e        
    message = Request.REQUEST_PRED.to_bytes(1, 'big')
    writer.write(message)
    await writer.drain()

    loc = json.loads((await read_msg(reader)).decode())
    if loc != None:
        return loc
    else: 
        return None, None

'''
    Handle a request for the location of this node's predecessor.
'''
async def handle_request_predecessor(reader: StreamReader, writer: StreamWriter) -> None:
    print("Request for predecessor")
    if pred_id != None:
        to_send = pred_loc
    else:
        to_send = None
    writer.write(add_len(json.dumps(to_send).encode()))
    await writer.drain()
    writer.close()


'''
    Send a request to the node at host:port for the first n nodes in it's successor 
    list. If n == 0 full list is returned.
'''
async def request_successors(host: str, port: int, n: int = 1) -> Optional[list[tuple[str, int]]]:
    reader: StreamReader
    writer: StreamWriter
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), CONNECTION_TIMEOUT)
    except Exception as e:
        print(f"Failure to connect to {host}:{port} : {e}")
        raise e        

    message = Request.REQUEST_SUCC.to_bytes(1, 'big') + n.to_bytes(1, 'big')
    writer.write(message)
    await writer.drain()

    resp = json.loads((await read_msg(reader)).decode())
    if len(resp) == 0:
        return None
    else:
        resp = cast(list[tuple[str, int]], resp)
        return list(map(cast(Callable, tuple), resp))


'''
    Handle a request for this node's first n successors where n is a one byte 
    transmitted integer. If n == 0 then send the whole list back.
'''
async def handle_request_successors(reader: StreamReader, writer: StreamWriter) -> None:
    global succ_list
    n = int.from_bytes(await reader.read(1), 'big')
    if n > len(succ_list):
        n = len(succ_list)
    elif n == 0:
        n = len(succ_list)
    # Only send the location of the successors. The id's can be calculated by the requester
    to_send = list(map(lambda x: x[1], succ_list[:n]))
    message = add_len(json.dumps(to_send).encode())
    writer.write(message)
    await writer.drain()
    writer.close()
                

'''
    General method to interpret any incoming request and pass it off to the appropriate
    method.
'''
async def handle_request(reader: StreamReader, writer: StreamWriter) -> None:
    peername = writer.get_extra_info("peername")
    print(f"Got request from {peername}")
    req_code = int.from_bytes(await reader.read(1), 'big')
    if req_code == Request.PING:
        await handle_ping(reader, writer)
    elif req_code == Request.NOTIFY:
        await handle_notify(reader, writer)
    elif req_code == Request.REQUEST_PRED:
        await handle_request_predecessor(reader, writer)
    elif req_code == Request.REQUEST_SUCC:
        await handle_request_successors(reader, writer)
    elif req_code == Request.CLOSEST_PRECEDING:
        await handle_closest_preceding(reader, writer)


'''
    Repeatedly run a function with a given interval.
'''
async def repeat(func, interval=5):
    await asyncio.sleep(interval)
    while True:
        await asyncio.sleep(interval)
        await func()


'''
    Run the node and take requests at the given host:port. If known is given this node
    will try to join the known node's network.
'''
async def run_node(
            host: str = '127.0.0.1', 
            port: int = 0, 
            known: Optional[tuple[str, int]]=None
        ) -> None:
    global my_host, my_port, my_id, succ_list

    server: asyncio.Server = await asyncio.start_server(handle_request, host=host, port=port)
    my_host, my_port = server.sockets[0].getsockname()
    my_id = sha256(json.dumps((my_host,my_port)).encode()).digest()
    addrs: str = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    # If no node is known then we are starting a new ring and this node is it's own
    # successor
    if known is not None:
        await join(*known)
    else:
        succ_list = [(my_id, (my_host, my_port))]

    async with server:
        await asyncio.gather(
                server.serve_forever(), 
                repeat(check_predecessor, interval=CHECK_PREDECESSOR_INTERVAL),
                repeat(stabilize, interval=STABILIZE_INTERVAL),
                repeat(fix_fingers, interval=FIX_FINGERS_INTERVAL)
        )
    



if __name__=="__main__":
    parser = argparse.ArgumentParser(
        prog='node.py',
        description='Implements a chord node'
    )

    parser.add_argument('-p', '--port', default=0, type=int)
    parser.add_argument('-k', '--known', default=None)

    args = parser.parse_args()
    if args.known != None:
        args.known = (lambda s: (s[0], int(s[1])))(args.known.split(" "))
    host = '127.0.0.1'


    asyncio.run(run_node(host, args.port, known=args.known))




