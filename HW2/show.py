import graphviz
def build_tree(edges):
    dot = graphviz.Digraph()
    for edge in edges:
        parent, child = edge[0], edge[1]
        parent = str(parent)
        child = str(child)
        dot.edge(parent, child)
    return dot