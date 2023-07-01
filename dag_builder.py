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

    def build_graph(self, items):
        dependency_graph = self.build_dependency_graph(items)

        return dependency_graph

    @staticmethod
    def display_valid_scenario(graph, scenario):
        node_colors = {node: 'lightblue' for node in graph.nodes()}
        last_action = ""
        for action in scenario:
            node_colors[action] = 'lightgreen'
            last_action = action
        final_nodes = graph.successors(last_action)
        for node in final_nodes:
            node_colors[node] = 'lightgreen'
        DAGBuilder.visualise_graph(graph, node_colors)

    @staticmethod
    def display_invalid_scenario(graph, scenario):
        node_colors = {node: 'lightblue' for node in graph.nodes()}
        for action in scenario:
            node_colors[action] = 'red'
        DAGBuilder.visualise_graph(graph, node_colors)

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

    def topological_sort(self, dependency_graph):
        # Perform topological sorting to generate valid scenarios
        scenarios = []

        # Find all nodes without incoming edges (sources)
        sources = [node for node in dependency_graph.nodes if dependency_graph.in_degree(node) == 0]

        # Generate scenarios starting from each source node
        for source in sources:
            stack = [(source, [source])]
            action_stack = []

            while stack:
                action_path = []
                if action_stack:
                    init_act, action_path = action_stack.pop()
                node, path = stack.pop()

                successors = list(dependency_graph.successors(node))

                if successors:
                    for successor in successors:
                        action = self.get_action_from_edge(dependency_graph, node, successor)

                        new_action_path = action_path + [action]
                        new_path = path + [successor]
                        action_stack.append((action, new_action_path))
                        stack.append((successor, new_path))
                else:
                    scenarios.append(action_path)

        return scenarios

    @staticmethod
    def visualise_graph(dependency_graph, node_colours):
        pos = nx.shell_layout(dependency_graph)
        plt.figure(figsize=(12, 12))

        edge_labels = {}
        for u, v, attrs in dependency_graph.edges(data=True):
            if "action" in attrs:
                edge_labels[(u, v)] = attrs["action"]

        nx.draw_networkx(dependency_graph, pos, with_labels=False, node_color=list(node_colours.values()),
                         node_size=1200, font_size=12, arrowsize=30, edge_color='gray')
        nx.draw_networkx_edge_labels(dependency_graph, pos=pos, edge_labels=edge_labels, font_size=9)

        plt.title("Directed Graph Visualization")
        plt.axis("off")
        plt.show()

        return dependency_graph
