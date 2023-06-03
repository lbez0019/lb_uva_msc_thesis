import networkx as nx
import matplotlib.pyplot as plt



def visualize_graph(graph):
    pos = nx.spring_layout(graph)  # Layout for node positioning
    labels = {node: f"{node}" for node in graph.nodes()}
    print(graph.edges())
    edge_labels = {(u, v): f"{u} to {v}" for u, v in graph.edges()}

    plt.figure(figsize=(10, 6))
    nx.draw_networkx(graph, pos=pos, with_labels=True, labels=labels, node_size=800, node_color="lightblue",
                     edge_color="gray", arrows=True, font_size=12, font_weight="bold")

    nx.draw_networkx_edge_labels(graph, pos=pos, edge_labels=edge_labels, font_size=10)

    plt.title("Directed Graph Visualization")
    plt.axis("off")
    plt.show()


def order_items(items):
    # Create a directed graph
    init_node = 0
    graph = nx.DiGraph()
    graph.add_node(init_node) # Start Node

    # Add nodes to the graph
    for item in items:
        values = items[item]
        creates_nodes = values["Creates"][0]
        for node in creates_nodes:
            graph.add_node(node)  # Convert dict to tuple

    # Add directed edges based on Holds and Creates clauses
    for item in items:
        holds = items[item]["Holds"]
        creates = items[item]["Creates"]

        if not holds:
            graph.add_edge(init_node, creates[0][0], action=item)
            continue

        for hold in holds:
            for create in creates:
                graph.add_edge(hold[0], create[0], action=item)  # Convert dict to tuple

    visualize_graph(graph)

    # Perform topological sorting to generate valid scenarios
    scenarios = []

    # Find all nodes without incoming edges (sources)
    sources = [node for node in graph.nodes if graph.in_degree(node) == 0]

    # Generate scenarios starting from each source node
    for source in sources:
        stack = [(source, [source])]
        action_stack = []

        while stack:
            action_path = []
            if action_stack:
                init_act, action_path = action_stack.pop()
            node, path = stack.pop()

            successors = list(graph.successors(node))

            if successors:
                for successor in successors:
                    action = get_action_from_edge(graph, node, successor)

                    new_action_path = action_path + [action]
                    new_path = path + [successor]
                    action_stack.append((action, new_action_path))
                    stack.append((successor, new_path))
            else:
                scenarios.append(action_path)

    return scenarios


def get_action_from_edge(graph, node, successor):
    for edge in graph.edges():
        if edge[0] == node and edge[1] == successor:
            return graph.edges[node, successor]["action"]


items = {
    "A": {"Holds": [[5]], "Creates": [[1]]},
    "B": {"Holds": [[3], [4]], "Creates": [[2]]},
    # "C": {"Holds": [[1]], "Creates": [[3]]},
    "C": {"Holds": [[1]], "Creates": [[4]]},
    "D": {"Holds": [[1]], "Creates": [[3]]},
    "E": {"Holds": [], "Creates": [[5]]}
}

scenarios = order_items(items)
for scenario in scenarios:
    print(scenario)
