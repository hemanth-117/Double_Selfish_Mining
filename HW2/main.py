import numpy as np
import os
import random
import uuid
from peer import *
from transaction import *
from block import *
from graph import *
from queue import PriorityQueue
import treelib
from treelib import Node, Tree
import networkx as nx
import matplotlib.pyplot as plt
from show import *

def latency(i,j,prop_ij,size):
    c_ij = 5000
    if(i.fast and j.fast):
        c_ij = 100000

    d = np.random.exponential(scale=96/c_ij)
    return prop_ij+((size)/c_ij) + 1000*d


if __name__ == '__main__':
    N = int(input("Enter the number of peers: "))
    Z0 = float(input("fraction of slow peers as Z0: "))
    # Z1 = float(input("fraction of low cpu peers peers as Z1: "))
    t_it = float(input("The interarrival between transactions as t_it: "))
    b_it = float(input("The interarrival between blocks as b_it: "))
    attacker_hashing_power_1 = float(input("fraction of hashing power with attacker1: "))
    attacker_hashing_power_2 = float(input("fraction of hashing power with attacker2: "))
    BLOCKS = int(input("Total no of Blocks to create: "))

    if attacker_hashing_power_1 == 0:
        attacker_hashing_power_1 = 0.0001
    if attacker_hashing_power_2 == 0:
        attacker_hashing_power_2 = 0.0001

    edges = None
    while True:
        edges = create_graph(N)
        if(connected(edges)):
            break

    for i in range(N):
        print(i,":",edges[i])

    N_slow = int(N*Z0)
    # N_low_cpu = int(N*Z1)
    honest_hash_power = float((1-attacker_hashing_power_1-attacker_hashing_power_2)/(N-2))
    uid = 0

    slow_peers = random.sample(range(N), N_slow)
    # low_cpu_peers = random.sample(range(N), N_low_cpu)
    # randomly sample two peers and they are attackers 
    fast_peers = []
    for i in range(N):
        if i not in slow_peers:
            fast_peers.append(i)
    # attackers are only fast
    attackers = random.sample(fast_peers,2)

    peers = []
    start_amount = []
    for i in range(N):
        hash_power = None
        if i == attackers[0]:
            hash_power = attacker_hashing_power_1
        elif i == attackers[1]:
            hash_power = attacker_hashing_power_2
        else:
            hash_power = honest_hash_power
        peers.append(Peer(i, i not in slow_peers, i not in attackers, edges[i], hash_power))
        start_amount.append(float(1000))



    prop_ij = [[0 for j in range(N)] for i in range(N)]

    for i in range(N):
        for j in range(N):
            prop_ij[i][j] = np.random.uniform(10,500)

    peer_blocks = [[] for _ in range(N)]
    peer_pending_block_queue = [[] for _ in range(N)]
    peer_leads = [0 for _ in range(N)]
    peer_secret_blocks = [[] for _ in range(N)]
    peer_transactions = [[] for _ in range(N)]
    peer_transactions_unspent = [[] for _ in range(N)]


    current_time = float(0)


    genisis_block = Block(uid,-1,-1,0,current_time,start_amount)
    uid+=1
    for i in range(N):
        peer_blocks[i].append(genisis_block)

    # there are 4 type of events
    # create transaction [time,0,sender,null,null,-1,starttime]
    # create block [time,1,sender,null,parent_id,null,-1,starttime]
    # receive transaction [time,2,sender,null,transaction,receiver,starttime]
    # receive block [time,3,sender,block,null,receiver,starttime]

    event_queue = PriorityQueue()

    for i in range(N):
        delay = np.random.exponential(scale=t_it)
        task = [current_time+delay,0,i,None,None,-1,current_time]
        event_queue.put(task)

    for i in range(N):

        power = peers[i].hashing_power


        delay = np.random.exponential(scale=b_it/power)
        task = [current_time+delay,1,i,None,genisis_block.block_id,None,-1,current_time]
        event_queue.put(task)

    created_blocks = 0


    while (not event_queue.empty()):
        # create blocks till BLOCKS are created
        # create transactions till BLOCKS are created
        # receive transactions and blocks will be done till the end of the simulation
        event = event_queue.get()
        current_time = event[0]
        event_type = event[1]
        



        if event_type == 0:
            if created_blocks == BLOCKS:
                print("All blocks are created")
                continue
            print("Create transaction")
            sender = event[2]
            possible_recievers = [i for i in range(N) if i != sender]
            receiver = random.choice(possible_recievers)
            # find longest block in recieved blocks 
            max_length = -1
            longest_block = None
            for b in peer_blocks[sender]:
                if b.length > max_length:
                    max_length = b.length
                    longest_block = b

            

            # find the balance of sender in longest block
            amount = longest_block.balances[sender]

            pay = random.random()
            if pay > amount:
                print("Insufficient balance")
                continue
            
            transac_id = uid
            uid+=1
            new_transac = transaction(transac_id,sender,receiver,pay,8000)
            # as it is new add into both Transaction lists
            peer_transactions[sender].append(new_transac)
            peer_transactions_unspent[sender].append(new_transac)


            # create a next create transaction event
            delay = np.random.exponential(scale=t_it)
            task = [current_time+delay,0,sender,None,None,-1,current_time]
            event_queue.put(task)

            # create a receive transaction event for all its neighbours except sender
            for i in edges[sender]:
                delay = latency(peers[sender],peers[i],prop_ij[sender][i],8000)
                task = [current_time+delay,2,sender,None,new_transac,i,current_time]
                event_queue.put(task)


            

        elif event_type == 1:
            if created_blocks == BLOCKS:
                if event[2] in attackers:
                    # broad cast all secret blocks to all neighbours
                    for block in peer_secret_blocks[event[2]]:
                        # add block into receiver's peer_blocks
                        peer_blocks[event[2]].append(block)
                        for i in edges[event[2]]:
                            delay = latency(peers[event[2]],peers[i],prop_ij[event[2]][i],8000*len(block.transactions))
                            task = [current_time+delay,3,event[2],block,None,i,current_time]
                            event_queue.put(task)
                    peer_secret_blocks[event[2]] = []
                    peer_leads[event[2]] = 0
                continue

            print("Create block")
            # check if longest block is still parent_id in the event else continue
            sender = event[2]
            parent_id = event[4]
            max_length = -1
            longest_block = None
            can_create = True
            for b in peer_blocks[sender]:
                if b.length > max_length:
                    max_length = b.length
                    longest_block = b
                elif b.length == max_length and b.time < longest_block.time:
                    longest_block = b

            if longest_block.block_id != parent_id and sender not in attackers:
                print("Discarded create block event")
                can_create = False 

            if sender in attackers:
                # check if length of peer_secret_blocks > = 1
                if len(peer_secret_blocks[sender]) >= 1:
                    # check if last secret block is parent_id
                    last_secret_block = peer_secret_blocks[sender][-1]
                    if last_secret_block.block_id != parent_id:
                        print("Discarded create block event")
                        can_create = False

            if can_create:
                # randomly sample atmost 999 transactions from peer_transactions_unspent[sender]
                transactions = random.sample(peer_transactions_unspent[sender],min(999,len(peer_transactions_unspent[sender])))
                # craete a copy of balances of longest block
                balances = longest_block.balances.copy()
                # create a coin base transaction
                coin_base = transaction(uid,-1,sender,50,8000)
                uid+=1
                transactions.append(coin_base)
                # update the balances
                balances[sender] += 50
                for tran in transactions:
                    if tran.idx != -1:
                        balances[tran.idx] -= tran.amount
                        balances[tran.idy] += tran.amount

                # check if the balances are valid
                valid = True
                for i in range(N):
                    if balances[i] < 0:
                        valid = False
                        break

                if not valid:
                    print("invalid block created")
                    continue

                # update the unspent transactions of sender
                new_unspent = []
                for tran in peer_transactions_unspent[sender]:
                    found = False
                    for t in transactions:
                        if t.transaction_id == tran.transaction_id:
                            found = True
                            break
                    if not found:
                        new_unspent.append(tran)

                peer_transactions_unspent[sender] = new_unspent

                # create a new block
                print("block is created at length ",longest_block.length+1)
                new_block = Block(uid,parent_id,sender,longest_block.length+1,current_time,balances)
                uid+=1
                new_block.transactions = transactions.copy()
                # print(len(new_block.transactions))

                # add this block to peer_blocks[sender]
                created_blocks+=1

                # broadcast this block to all its neighbours
                last_secret_block = None
                if sender not in attackers:
                    peer_blocks[sender].append(new_block)
                    for i in edges[sender]:
                        delay = latency(peers[sender],peers[i],prop_ij[sender][i],8000*len(transactions))
                        task = [current_time+delay,3,sender,new_block,None,i,current_time]
                        event_queue.put(task)
                
                else:
                    peer_secret_blocks[sender].append(new_block)
                    last_secret_block = new_block
                    peer_leads[sender]+=1
                        


            # create a new create block event for sender
            power = peers[sender].hashing_power
            
            delay = np.random.exponential(scale=b_it/power)
            if can_create:
                task = [current_time+delay,1,sender,None,new_block.block_id,None,-1,current_time]
            elif sender not in attackers:
                task = [current_time+delay,1,sender,None,longest_block.block_id,None,-1,current_time]
            elif len(peer_secret_blocks[sender]) >= 1:
                task = [current_time+delay,1,sender,None,peer_secret_blocks[sender][-1].block_id,None,-1,current_time]
            else:
                task = [current_time+delay,1,sender,None,longest_block.block_id,None,-1,current_time]

            event_queue.put(task)

            

            
            



        elif event_type == 2:
            # check if transaction is there in the pper_transactions[receiver]
            found = False
            receiver = event[5]
            r_transaction = event[4]
            for transac in peer_transactions[receiver]:
                if transac.transaction_id == r_transaction.transaction_id:
                    found = True
                    break
            
            # if not found send this transactions to all its neightbouts except sender
            if not found:
                print("Receive transaction")

                new_transac = transaction(r_transaction.transaction_id,r_transaction.idx,r_transaction.idy,r_transaction.amount,r_transaction.size)
                peer_transactions[receiver].append(new_transac)
                # add int unspent if it is not in peer_blocks[receiver]
                is_spent = False
                for block in peer_blocks[receiver]:
                    for tran in block.transactions:
                        if tran.transaction_id == new_transac.transaction_id:
                            is_spent = True
                            break
                
                if not is_spent:
                    peer_transactions_unspent[receiver].append(new_transac)

                for i in edges[receiver]:
                    if i == event[2]:
                        continue
                    delay = latency(peers[receiver],peers[i],prop_ij[receiver][i],8000)
                    task = [current_time+delay,2,receiver,None,new_transac,i,current_time]
                    event_queue.put(task)




    
        elif event_type == 3:
            # check if block is there in the peer_blocks[receiver]
            # event structure [time,3,sender,block,null,receiver,starttime]
            print("Receive block")
            found = False
            receiver = event[5]
            r_block = Block(event[3].block_id,event[3].prev_block_id,event[3].miner_id,event[3].length,event[3].time,event[3].balances)
            r_block.transactions = event[3].transactions.copy()
            for block in peer_blocks[receiver]:
                if block.block_id == r_block.block_id:
                    found = True
                    break
            
            if found:
                print("Block is already received")
                continue

            # find parent block of the r_block
            parent_block = None
            for block in peer_blocks[receiver]:
                if block.block_id == r_block.prev_block_id:
                    parent_block = block
                    break

            if parent_block == None:
                print("Parent block not found")
                # add this block to pending block queue if not already present
                found = False
                for block in peer_pending_block_queue[receiver]:
                    if block.block_id == r_block.block_id:
                        found = True
                        break
                if found:
                    continue
                # add this block to pending block queue
                peer_pending_block_queue[receiver].append(r_block)
                # send it to all its neighbours except sender
                if receiver not in attackers:
                    for i in edges[receiver]:
                        if i == event[2]:
                            continue
                        delay = latency(peers[receiver],peers[i],prop_ij[receiver][i],8000*len(r_block.transactions))
                        task = [current_time+delay,3,receiver,r_block,None,i,current_time]
                        event_queue.put(task)
                # do nothing
                continue

            else:
                #update unspent transactions of receiver
                new_unspent = []
                for tran in peer_transactions_unspent[receiver]:
                    found = False
                    for t in r_block.transactions:
                        if t.transaction_id == tran.transaction_id:
                            found = True
                            break
                    if not found:
                        new_unspent.append(tran)
                peer_transactions_unspent[receiver] = new_unspent
                r_block.length = parent_block.length + 1
                peer_blocks[receiver].append(r_block)
                # send it to all its neighbours except sender
                if receiver not in attackers:
                    for i in edges[receiver]:
                        if i == event[2]:
                            continue
                        delay = latency(peers[receiver],peers[i],prop_ij[receiver][i],8000*len(r_block.transactions))
                        task = [current_time+delay,3,receiver,r_block,None,i,current_time]
                        event_queue.put(task)

            # update the pending block queue of receiver
            while True:
                # check if r_block is parent of any block in pending block queue
                found = False
                check_block = None
                for block in peer_pending_block_queue[receiver]:
                    if block.prev_block_id == r_block.block_id:
                        found = True
                        check_block = block
                        break
                if not found:
                    break
                # remove the block from pending block queue
                peer_pending_block_queue[receiver].remove(check_block)
                # update length of check block
                check_block.length = r_block.length + 1
                # add this block to peer_blocks[receiver]
                peer_blocks[receiver].append(check_block)
                # update the unspent transactions of receiver
                new_unspent = []
                for tran in peer_transactions_unspent[receiver]:
                    found = False
                    for t in check_block.transactions:
                        if t.transaction_id == tran.transaction_id:
                            found = True
                            break
                    if not found:
                        new_unspent.append(tran)
                peer_transactions_unspent[receiver] = new_unspent
                # copy check block to r_block
                r_block = Block(check_block.block_id,check_block.prev_block_id,check_block.miner_id,check_block.length,check_block.time,check_block.balances)
                r_block.transactions = check_block.transactions.copy()

            # find the longest block of receiver
            max_length = -1
            longest_block = None
            for b in peer_blocks[receiver]:
                if b.length > max_length:
                    max_length = b.length
                    longest_block = b
                elif b.length == max_length and b.time < longest_block.time:
                    longest_block = b

            attacker_mining_block = None
            if receiver in attackers:
                # check if length of peer_secret_blocks > = 1
                if len(peer_secret_blocks[receiver]) >= 1:
                    lvc_height = longest_block.length
                    adv_height = peer_secret_blocks[receiver][-1].length

                    if lvc_height > adv_height:
                        peer_secret_blocks[receiver] = []
                        peer_leads[receiver] = 0
                    elif lvc_height == adv_height or lvc_height == adv_height - 1:
                        # mine on his secret block
                        attacker_mining_block = peer_secret_blocks[receiver][-1]
                        # broadcast all secret blocks to all neighbours
                        for block in peer_secret_blocks[receiver]:
                            # add block into receiver's peer_blocks
                            peer_blocks[receiver].append(block)
                            for i in edges[receiver]:
                                delay = latency(peers[receiver],peers[i],prop_ij[receiver][i],8000*len(block.transactions))
                                task = [current_time+delay,3,receiver,block,None,i,current_time]
                                event_queue.put(task)
                        peer_secret_blocks[receiver] = []
                        peer_leads[receiver] = 0
                    elif lvc_height < adv_height - 1:
                        # send all secret blocks o [0:lvc_height] to all neighbours
                        attacker_mining_block = peer_secret_blocks[receiver][-1]
                        for block in peer_secret_blocks[receiver][0:lvc_height]:
                            # add block into receiver's peer_blocks
                            peer_blocks[receiver].append(block)
                            for i in edges[receiver]:
                                delay = latency(peers[receiver],peers[i],prop_ij[receiver][i],8000*len(block.transactions))
                                task = [current_time+delay,3,receiver,block,None,i,current_time]
                                event_queue.put(task)
                        peer_secret_blocks[receiver] = peer_secret_blocks[receiver][lvc_height:]
                        peer_leads[receiver] = adv_height - lvc_height
                    if attacker_mining_block != None:
                        longest_block = attacker_mining_block

            
            
            # create a new create block event for receiver
            power = peers[receiver].hashing_power
            


            delay = np.random.exponential(scale=b_it/power)
            task = [current_time+delay,1,receiver,None,longest_block.block_id,None,-1,current_time]
            event_queue.put(task)





            





        else:
            print("Invalid event type")
            break

    # print all the received blocks of each peer in output_peerid.txt file 
    for i in range(N):
        filename = "output_peer" + str(i) + ".txt"
        # remove the file if it already exists
        if os.path.exists(filename):
            os.remove(filename)
        f = open(filename,"w")
        for block in peer_blocks[i]:
            f.write("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n")
            f.write("Block ID: " + str(block.block_id) + "\n")
            f.write("Previous Block ID: " + str(block.prev_block_id) + "\n")
            f.write("Miner ID: " + str(block.miner_id) + "\n")
            f.write("Length: " + str(block.length) + "\n")
            f.write("Time: " + str(block.time) + "\n")
            f.write("Balances: " + str(block.balances) + "\n")
            f.write("No of Transactions: "+str(len(block.transactions))+" \n")
            f.write("Transactions: \n")
            for tran in block.transactions:
                f.write("Transaction ID: " + str(tran.transaction_id) + "\n")
                f.write("Sender: " + str(tran.idx) + "\n")
                f.write("Receiver: " + str(tran.idy) + "\n")
                f.write("Amount: " + str(tran.amount) + "\n")
                f.write("Size: " + str(tran.size) + "\n")
            f.write("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n")
        f.close()


    # finally create the block tree of each peer using the graphviz library
    # source : https://graphviz.readthedocs.io/en/stable/manual.html
    for i in range(N):
        node_edges = []
        for block in peer_blocks[i]:
            if block.prev_block_id == -1:
                continue
            node_edges.append([block.prev_block_id,block.block_id])
        
        tree = build_tree(node_edges)
        # delete the file if it already exists
        tree.attr('node', shape='circle', width='0.1', height='0.1')  # Adjust node size
        tree.attr('edge', minlen='1') 
        if os.path.exists("output_peer"+str(i)+".png"):
            os.remove("output_peer"+str(i)+".png")
        tree.render("output_peer"+str(i),format='png',cleanup=True)



    # find the longest chain and find the fraction of attackers blocks in this chain
    # attacker1 and attacker2 are the no of blocks in the longest chain by attackers
    # honest is the no of blocks in the longest chain created by other peers
    # as all the peers has the same block chain length, we can take any peer to find the longest chain consider it 0 peer
    attacker1 = 0
    attacker2 = 0
    attacker1_blocks = 0
    attacker2_blocks = 0
    honest = 0
    # first find the longest chain in peer_blocks[0]
    longest_chain = []
    last_block = None
    for block in peer_blocks[0]:
        # if last_block is None, update last_block
        if last_block == None:
            last_block = block
        # if block length is greater than last_block length, update last_block
        elif block.length > last_block.length:
            last_block = block
        # if block length is equal to last_block length, compare the time
        elif block.length == last_block.length and block.time < last_block.time:
            last_block = block
    # add last_block to longest_chain
    longest_chain.append(last_block)
    # print last_block id
    print("Last block id: ",last_block.block_id)
    # find the parent block of last_block till parent block is genisis block
    while last_block.prev_block_id != -1:
        for block in peer_blocks[0]:
            if block.block_id == last_block.prev_block_id:
                last_block = block
                longest_chain.append(last_block)
                break
    # find the nof of blocks created by each attacker
    for block in longest_chain:
        if block.miner_id == attackers[0]:
            attacker1_blocks+=1
        elif block.miner_id == attackers[1]:
            attacker2_blocks+=1
    # find the no of blocks created by attackers and other peers
    # there are two attackers
    attacker1_id = attackers[0]
    attacker2_id = attackers[1]
    for block in longest_chain:
        if block.miner_id == attacker1_id:
            attacker1+=1
        elif block.miner_id == attacker2_id:
            attacker2+=1
        elif block.miner_id not in attackers and block.miner_id != -1:
            honest+=1
    
    print("No of blocks created by attacker1 in longest_chain: ",attacker1)
    print("No of blocks created by attacker2 in longest_chain: ",attacker2)
    # print("No of blocks created by honest peers in longest_chain: ",honest)

    print("Total no of blocks in longest chain: ",attacker1+attacker2+honest)
    print("Total no of blocks created by attacker1 : ",attacker1_blocks)
    print("Total no of blocks created by attacker2 : ",attacker2_blocks)
    print("Total no of blocks created by honest peers : ",BLOCKS-attacker1_blocks-attacker2_blocks)
    # print fraction of each attackers and honest blocks in the longest chain
    if attacker1_blocks == 0:
        print("Fraction of attacker1 blocks in longest chain: 0")
    else:
        print("Fraction of attacker1 blocks in longest chain: ",(attacker1/(attacker1_blocks)))
    if attacker2_blocks == 0:
        print("Fraction of attacker2 blocks in longest chain: 0")
    else:
        print("Fraction of attacker2 blocks in longest chain: ",(attacker2/(attacker1+attacker2_blocks)))
    print("Fraction of honest blocks in longest chain: ",(honest/(BLOCKS-attacker1_blocks-attacker2_blocks)))
    print("Fraction of blocks in longest chain: ",((honest+attacker1+attacker2)/(BLOCKS)))


    # for each peer find percentage of longest chain length to total blocks
    for i in range(N):
        max_length = -1
        for block in peer_blocks[i]:
            if block.length > max_length:
                max_length = block.length
        # print("Peer ",i," longest chain length: ",max_length+1)
        # print("Peer ",i," percentage of longest chain length to total blocks: ",((max_length+1)/(BLOCKS+1))*100)


        



        
    



