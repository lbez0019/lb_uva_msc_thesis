import networkx as nx
import matplotlib.pyplot as plt


class DAGBuilder:
    @staticmethod
    def add_edges_to_graph(graph, expression_tree, creates, action_node):
        def add_edges(node, prev_node):
            for created_item in creates:
                graph.add_edge(node, created_item, action=action_node)  # Set action_node as attribute of edge

        add_edges(expression_tree, action_node)

    def build_dependency_graph(self, items):
        graph = nx.DiGraph()

        for item, conditions in items.items():
            act = conditions['Act']
            creates = conditions['Creates']

            expression_tree = DAGBuilder.rpn_to_expression_tree(act)
            self.add_edges_to_graph(graph, expression_tree, creates, item)

        return graph

    @staticmethod
    def display_valid_scenario(graph, scenario):
        # TODO: ADD EDGE COLOURS
        node_colours = {node: 'lightblue' for node in graph.nodes()}
        edge_colours = []
        edge_traversals = scenario
        last_action = ""
        for action in scenario:
            last_action = action

        final_nodes = graph.successors(last_action)
        for node in final_nodes:
            node_colours[node] = 'lightgreen'
            edge_traversals.append(node)

        for edge in graph.edges:
            origin, destination = edge

            if origin in edge_traversals and destination in edge_traversals:
                edge_colours.append('lightgreen')
            else:
                edge_colours.append('gray')
        DAGBuilder.visualise_graph(graph, node_colours, edge_colours)

    @staticmethod
    def display_invalid_scenario(graph, scenario):
        node_colours = {node: 'lightblue' for node in graph.nodes()}
        node_colours[scenario[1]] = 'red'
        edge_traversals = scenario[0][:(scenario[0].index(scenario[1]) + 1)]

        edge_colours = []
        for edge in graph.edges:
            origin, destination = edge

            if origin in edge_traversals and destination in edge_traversals:
                edge_colours.append('red')
            else:
                edge_colours.append('gray')

        DAGBuilder.visualise_graph(graph, node_colours, edge_colours)

    @staticmethod
    def get_action_from_edge(graph, node, successor):
        for edge in graph.edges():
            if edge[0] == node and edge[1] == successor:
                return graph.edges[node, successor]["action"]

    @staticmethod
    def is_operator(token):
        return token in ['&&', '||', 'Not']

    @staticmethod
    def rpn_to_expression_tree(rpn_expression):
        stack = []
        tokens = rpn_expression.split()

        for token in tokens:
            stack.append(token)

        return stack.pop()

    @staticmethod
    def visualise_graph(dependency_graph, node_colours, edge_colours):
        pos = nx.shell_layout(dependency_graph)
        plt.figure(figsize=(12, 11))

        labels = {node: node for node in dependency_graph.nodes}

        edge_labels = {}
        for u, v, attrs in dependency_graph.edges(data=True):
            if "action" in attrs:
                edge_labels[(u, v)] = attrs["action"]

        nx.draw_networkx(dependency_graph, pos, with_labels=False, node_color=list(node_colours.values()),
                         node_size=1200, arrowsize=30, edge_color=edge_colours, width=2.0)

        label_pos = {k: (v[0], v[1] - 0.09) for k, v in pos.items()}  # Adjust the y-coordinate for the labels
        nx.draw_networkx_labels(dependency_graph, pos=label_pos, labels=labels, font_size=16, font_color='black',
                                verticalalignment='center')

        plt.title("Directed Graph Visualization", fontsize=18)  # Set the font size of the title
        plt.axis("off")
        plt.margins(0.2)
        plt.tight_layout()

        plt.show()

        return dependency_graph
