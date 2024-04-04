import networkx as nx
import numpy as np
import random

def create_graph(peers):
    # Create graph
    degree=[0 for i in range(peers)] # Keeping a count of degree of each vertex

    edges=[[] for i in range(peers)] # Actual edges in the graph
    
    visited=[] # Nodes that have achieved their maximum degree
    
    for i in range(peers):
        num=np.random.choice([3,4,5,6]) # Choose the degree of the current node randomly
        
        if num<=degree[i]:
            # If current degree is more than the choice, then skip
            continue
        
        # From all nodes having index greater than i, we remove the visited nodes to get potential neighbors
        unvisited = list(set(range(i+1,peers)).difference(set(visited)))
        
        # From the potential neighbors choose the required number of neighbors, or all of them if not enough neighbors are available
        
        neighbors = np.random.choice(unvisited,min(len(unvisited),num-degree[i]),replace=False)
        
        # Add the neighbors to the current node
        for j in neighbors:
            edges[i].append(j)
            edges[j].append(i)
            degree[i]+=1
            degree[j]+=1
        
        # If the degree of the current node is achieved, then add it to the visited list
        if degree[i]==6:
            visited.append(i)
            
    return edges

# Check if the graph is connected using nx.is_connected
def connected(adj_lists):
    # Create graph
    G = nx.Graph()
    G.add_nodes_from(range(len(adj_lists)))
    # Add edges to each node
    for node, adj_list in enumerate(adj_lists):
        # Add edges to each node
        for target_node in adj_list:
            G.add_edge(node, target_node)
    # Check if the graph is connected
    return nx.is_connected(G)


