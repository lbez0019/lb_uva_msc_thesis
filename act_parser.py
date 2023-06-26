import re
import networkx as nx
import matplotlib.pyplot as plt


class ActionParser:
    def __init__(self):
        self.actions = {}

    @staticmethod
    def parse_file(file_path):
        with open(file_path, 'r') as file:
            content = file.read()

        pattern = r'(?m)^(?!Extend)(Act [\w\W]*?\.)'
        acts = re.findall(pattern, content, re.DOTALL)

        return acts

    def retrieve_action_list(self):
        template_path = '../../eflint-server/web-server/test.eflint'  # Replace with the actual file path
        parsed_acts = self.parse_file(template_path)
        action_list = []

        for act in parsed_acts:
            action = self.parse_string(act)
            action_list.append(action)
            self.actions[action["Act"][0]] = action
            preconditions = action['Conditioned by']

        return action_list

    def parse_string(self, input_string):
        lines = input_string.split("\n")
        result = {'Act': [], 'Actor': [], 'Recipient': [], 'Holds when': [],
                  'Conditioned by': [], 'Creates': [], 'Terminates': [], 'Obfuscates': []}
        current_key = ''

        for line in lines:
            line = line.strip()
            if line:
                for key in result.keys():
                    if line.startswith(key + ' '):
                        value = line[len(key) + 1:].strip()

                        if key == 'Conditioned by':
                            value = self.infix_to_rpn(value)
                            result[key].append(value)

                        else:
                            pattern = r",(?![^()]*\))" # Only commas not within brackets
                            value = re.split(pattern, value)
                            value = [element.strip() for element in value]
                            result[key].extend(value)

                        current_key = key
                        break
                else:
                    result[current_key][-1] += ' ' + line.strip()

        return result

    @staticmethod
    def single_bracketed_token(expression):
        result = ""
        within_brackets = False

        for char in expression:
            if char == '(':
                within_brackets = True
            elif char == ')':
                within_brackets = False

            if within_brackets and char == ' ':
                continue

            result += char

        return result

    @staticmethod
    def join_output_with_operators(output, equality_operators):
        result = output[0]

        for i in range(1, len(output)):
            if output[i] in equality_operators or output[i-1] in equality_operators:
                result += output[i]
            else:
                result += ' ' + output[i]

        return result

    def rpn_to_infix(self, rpn_expression):
        stack = []
        operators = {'Not', '&&', '||', '==', '!=', '<', '>', '<=', '>='}

        rpn_expression = self.single_bracketed_token(rpn_expression)

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

    # Shunting Yard implementation
    @staticmethod
    def infix_to_rpn(expression):
        precedence = {'Not': 3, '&&': 2, '||': 1}
        equality_operators = ['==', '!=', '<', '>', '<=', '>=']
        output = []
        operators = []
        tokens = expression.split()

        for i in range(len(tokens)):
            token = tokens[i]
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
            elif token in equality_operators:
                # operators.append('(')
                output.append(token)
            else:
                if (i + 1) < len(tokens) and tokens[i + 1] in equality_operators:
                    token = '(' + token
                if tokens[i - 1] in equality_operators:
                    token = token + ')'
                output.append(token)

        while operators:
            output.append(operators.pop())

        return ActionParser.join_output_with_operators(output, equality_operators)

    @staticmethod
    def calculate_permutations(operands, operators):
        permutations = []
        for i in range(2 ** len(operands)):
            binary = bin(i)[2:].zfill(len(operands))
            operand_permutation = [operands[j] if bit == '0' else 'True' for j, bit in enumerate(binary)]
            perm_with_ops = ActionParser.interleave(operand_permutation, operators)
            permutations.append(perm_with_ops)

        return permutations

    @staticmethod
    def interleave(lst1, lst2):
        interleaved = []
        min_len = min(len(lst1), len(lst2))
        for i in range(min_len):
            interleaved.append(lst1[i])
            interleaved.append(lst2[i])
        if len(lst1) > min_len:
            interleaved.extend(lst1[min_len:])
        elif len(lst2) > min_len:
            interleaved.extend(lst2[min_len:])

        return interleaved

    def derive_alternative_preconditions(self, expression):
        operators = ['&&', '||']
        # Split the expression into tokens
        tokens = expression.split(' ')
        tokens = [token for token in tokens if token]
        operands = [token for token in tokens if token not in operators]
        parsed_operators = [token for token in tokens if token in operators]

        # Generate permutations using the calculate_permutations function
        permutations = ActionParser.calculate_permutations(operands, parsed_operators)

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
            # if self.is_operator(token):
            #     if token == 'Not':
            #         operand = stack.pop()
            #         stack.append((token, operand))
            #     else:
            #         right_operand = stack.pop()
            #         left_operand = stack.pop()
            #         stack.append((token, left_operand, right_operand))
            # else:
            stack.append(token)

        return stack.pop()

    def build_dependency_graph(self, items):
        graph = nx.DiGraph()

        for item, conditions in items.items():
            act = conditions['Act']
            creates = conditions['Creates']

            expression_tree = self.rpn_to_expression_tree(act)
            self.add_edges_to_graph(graph, expression_tree, creates, item)

        return graph

    @staticmethod
    def add_edges_to_graph(graph, expression_tree, creates, action_node):
        def add_edges(node, prev_node):
            # if isinstance(node, tuple):
            #     operator = node[0]
            #     for operand in node[1:]:
            #         add_edges(operand, prev_node)
            # else:
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
    def trim_values_end(self, values):
        for i in range(len(values)):
            if values[i].endswith('.'):
                values[i] = values[i].rstrip('.')
        return values

    def retrieve_scenarios(self, action_list):
        items = {}
        for dict_item in action_list:
            act = dict_item['Act'][0]
            creates = dict_item['Creates'].copy()
            creates = self.trim_values_end(creates)
            creates = self.split_string_until_open_parenthesis(creates)
            items[act] = {'Act': act, 'Creates': creates}

        dag_builder = DAGBuilder()
        dependency_graph = dag_builder.visualise_graph(items)
        scenarios = dag_builder.topological_sort(dependency_graph)

        return scenarios

    def split_string_until_open_parenthesis(self, creates):
        for i in range(len(creates)):
            item = creates[i]
            tokens = item.split()
            result = ""

            if tokens:
                first_token = tokens[0]
                index = first_token.find('(')
                if index != -1:
                    result = first_token[:index]
                else:
                    result = first_token
            creates[i] = result

        return creates
    # logic_expression_string = "Not(administrator()) || candidate == candidate2 && test_fact"
    # logic_expression_string = "Not (administrator()) || ( candidate == candidate2 ) && test_fact"
    # parsed_expression = action_parser.infix_to_rpn(logic_expression_string)

# executor = Executor()
# action_parser = ActionParser()
# action_list = action_parser.retrieve_action_list()
# scenarios = executor.retrieve_scenarios(action_list)
# print(scenarios)