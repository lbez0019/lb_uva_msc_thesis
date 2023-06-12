import re
import itertools
import networkx as nx
import matplotlib.pyplot as plt


class ActionParser:
    def __init__(self):
        self.operands = set()

    def parse_string(self, input_string):
        lines = input_string.split("\n")
        result = {'Act': [], 'Actor': [], 'Recipient': [], 'Holds when': [], 'Conditioned by': [], 'Creates': [],
                  'Terminates': [], 'Obfuscates': []}
        current_key = ''

        for line in lines:
            line = line.strip()
            if line:
                for key in result.keys():
                    if line.startswith(key + ' '):
                        value = line[len(key) + 1:].strip()

                        if key == 'Holds when' or key == 'Conditioned by':
                            value = self.infix_to_rpn(value)
                            result[key].append(value)
                            # value = self.expr.parseString(value).as_list()
                        else:
                            value = re.split(r"&&(?![^()]*\))", value)
                            value = [element.strip() for element in value]
                            result[key].extend(value)

                        current_key = key
                        break
                else:
                    result[current_key][-1] += ' ' + line.strip()

        return result

    # Shunting Yard implementation
    @staticmethod
    def infix_to_rpn(expression):
        precedence = {'Not': 3, '&&': 2, '||': 1}
        output = []
        operators = []
        tokens = expression.split()

        ignore_next = False  # Flag to ignore the next value

        for token in tokens:
            if token in precedence:
                while operators and operators[-1] != '(' and precedence[token] <= precedence.get(operators[-1], 0):
                    output.append(operators.pop())
                operators.append(token)
            elif token == '(':
                operators.append(token)
            elif token == ')':
                while operators and operators[-1] != '(':
                    output.append(operators.pop())
                operators.pop()  # Discard the '('#
            elif token in ['==', '!=', '<', '>', '<=', '>=']:
                ignore_next = True  # Set the flag to ignore the next value
            else:
                if not ignore_next:
                    output.append(token)
                ignore_next = False

        while operators:
            output.append(operators.pop())

        return ' '.join(output)

    @staticmethod
    def rpn_to_infix(rpn_expression):
        stack = []
        operators = {'Not', '&&', '||', '==', '!=', '<', '>', '<=', '>='}

        for token in rpn_expression.split():
            if token in operators:
                if token == 'Not':
                    operand = stack.pop()
                    infix = f"({token} {operand})"
                    stack.append(infix)
                else:
                    right_operand = stack.pop()
                    left_operand = stack.pop()
                    infix = f"({left_operand} {token} {right_operand})"
                    stack.append(infix)
            else:
                stack.append(token)

        return stack.pop()

    @staticmethod
    def calculate_permutations(operands):
        permutations = list(itertools.product([True, False], repeat=len(operands)))
        return permutations

    # Function to count the number of operands in the parsed expression
    def count_operand_instances(self, parser, expression):
        if isinstance(expression, int) or expression in ['&&', '||', '!', '==', 'Not']:
            return 0

        if isinstance(expression, str):
            parser.operands.add(expression)
            return 1

        count = 0
        for item in expression:
            count += self.count_operand_instances(parser, item)
        return count


class DAGBuilder:
    @staticmethod
    def is_operator(token):
        return token in ['&&', '||', 'Not']

    def rpn_to_expression_tree(self, rpn_expression):
        stack = []
        tokens = rpn_expression.split()

        for token in tokens:
            if self.is_operator(token):
                if token == 'Not':
                    operand = stack.pop()
                    stack.append((token, operand))
                else:
                    right_operand = stack.pop()
                    left_operand = stack.pop()
                    stack.append((token, left_operand, right_operand))
            else:
                stack.append(token)

        return stack.pop()

    def build_dependency_graph(self, items):
        graph = nx.DiGraph()

        for item, conditions in items.items():
            holds_when = conditions['Holds when']
            creates = conditions['Creates']

            for condition in holds_when:
                expression_tree = self.rpn_to_expression_tree(condition)
                self.add_edges_to_graph(graph, expression_tree, creates, item)

        return graph

    @staticmethod
    def add_edges_to_graph(graph, expression_tree, creates, action_node):
        def add_edges(node, prev_node):
            if isinstance(node, tuple):
                operator = node[0]
                for operand in node[1:]:
                    add_edges(operand, prev_node)
            else:
                for created_item in creates:
                    graph.add_edge(node, created_item, action=action_node)  # Set action_node as attribute of edge

        add_edges(expression_tree, action_node)

    @staticmethod
    def get_action_from_edge(graph, node, successor):
        for edge in graph.edges():
            if edge[0] == node and edge[1] == successor:
                return graph.edges[node, successor]["action"]

    def visualise_graph(self, items):
        dependency_graph = self.build_dependency_graph(items)
        pos = nx.shell_layout(dependency_graph)

        edge_labels = {}
        for u, v, attrs in dependency_graph.edges(data=True):
            if "action" in attrs:
                edge_labels[(u, v)] = attrs["action"]

        plt.figure(figsize=(12, 12))

        nx.draw_networkx(dependency_graph, pos, with_labels=True, node_color='lightblue', node_size=1200, font_size=12,
                         arrowsize=30, edge_color='gray')
        nx.draw_networkx_edge_labels(dependency_graph, pos=pos, edge_labels=edge_labels, font_size=9)

        plt.title("Directed Graph Visualization")
        plt.axis("off")
        plt.show()

        return dependency_graph

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


class Executor:

    def parse_file(self, file_path):
        with open(file_path, 'r') as file:
            content = file.read()

        pattern = r'(Act [\w\W]*?\.)'
        acts = re.findall(pattern, content, re.DOTALL)

        return acts

    def trim_values_end(self, values):
        for i in range(len(values)):
            if values[i].endswith('.'):
                values[i] = values[i].rstrip('.')
        return values

    def retrieve_action_list(self):
        template_path = '../../eflint-server/web-server/test.eflint'  # Replace with the actual file path
        parsed_acts = self.parse_file(template_path)
        action_list = []
        action_parser = ActionParser()

        for act in parsed_acts:
            action = action_parser.parse_string(act)
            action_list.append(action)
            preconditions = action['Holds when'] + action['Conditioned by']

        return action_list

    def retrieve_scenarios(self, action_list):
        items = {}
        for dict_item in action_list:
            act = dict_item['Act'][0]
            holds_when = dict_item['Holds when']
            creates = dict_item['Creates']
            creates = self.trim_values_end(creates)
            items[act] = {'Holds when': holds_when, 'Creates': creates}

        dag_builder = DAGBuilder()
        dependency_graph = dag_builder.visualise_graph(items)
        scenarios = dag_builder.topological_sort(dependency_graph)

        return scenarios

    # logic_expression_string = "Not(administrator()) || candidate == candidate2 && test_fact"
    # logic_expression_string = "Not (administrator()) || ( candidate == candidate2 ) && test_fact"
    # parsed_expression = action_parser.infix_to_rpn(logic_expression_string)
