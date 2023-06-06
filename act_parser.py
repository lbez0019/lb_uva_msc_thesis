import re
import itertools
from collections import defaultdict
from pyparsing import infixNotation, opAssoc, Literal, Word, alphas, Forward
from pyparsing import Keyword, nums, alphanums, Group, Suppress

class ActionParser():
    def __init__(self):
        self.operands = set()

        AND = Literal("&&")
        OR = Literal("||")
        NOT = Keyword("Not", caseless=True) | Literal("!")

        operand = Word(alphas, alphanums+"_")
        integer = Word(nums).setParseAction(lambda t: int(t[0]))
        comparison_op = Literal("==") | Literal("!=") | Literal("<=") | Literal(">=") | Literal("<") | Literal(">")
        comparison_expr = operand + comparison_op + (integer | operand)
        self.expr = Forward()

        function_call = Group(operand + Suppress("(") + Suppress(")"))  # Updated function call pattern
        atom = comparison_expr | function_call | operand
        self.expr <<= infixNotation(atom,
            [
                (NOT, 1, opAssoc.RIGHT),
                (AND, 2, opAssoc.LEFT),
                (OR, 2, opAssoc.LEFT)
            ]
        )

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
                            value = self.expr.parseString(value).as_list()
                        else:
                            value = re.split(r"&&(?![^()]*\))", value)
                            value = [element.strip() for element in value]

                        result[key].extend(value)
                        current_key = key
                        break
                else:
                    result[current_key][-1] += ' ' + line.strip()

        return result




def calculate_permutations(operands):
    permutations = list(itertools.product([True, False], repeat=len(operands)))
    return permutations


# Function to count the number of operands in the parsed expression
def count_operand_instances(action_parser, expression):
    if isinstance(expression, int) or expression in ['&&', '||', '!', '==', 'Not']:
        return 0

    if isinstance(expression, str):
        action_parser.operands.add(expression)
        return 1

    count = 0
    for item in expression:
        count += count_operand_instances(action_parser, item)
    return count

def parse_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    pattern = r'(Act [\w\W]*?\.)'
    acts = re.findall(pattern, content, re.DOTALL)

    return acts


template_path = '../../eflint-server/web-server/test.eflint'  # Replace with the actual file path
parsed_acts = parse_file(template_path)
action_list = []
action_parser = ActionParser()

logic_expression_string = "Not(administrator()) || candidate == 5 && test_fact"
parsed_expression = action_parser.expr.parseString(logic_expression_string)

for act in parsed_acts:
    action = action_parser.parse_string(act)
    action_list.append(action)

    for key in action:
        print(key)
        print(action[key])
        print("----")

    preconditions = action['Holds when'] + action['Conditioned by']

    print(preconditions)

    operand_count = count_operand_instances(action_parser, preconditions)
    # Replace with your own list
    permutations = calculate_permutations(action_parser.operands)
    print(len(permutations))
    for perm in permutations:
        print(perm)

print("end")
# sorted_items = topological_sort(items)
# print(sorted_items)
# for item_name in sorted_items:
#     item = next(item for item in items if item[0] == item_name)
#     print(item)




# def topological_sort(dependencies):
#     graph = defaultdict(list)
#     visited = set()
#     result = []
#
#     # Build the graph
#     for item in dependencies:
#         item_name = item["Act"][0]
#         holds_when = item["Holds when"]
#         creates = item["Creates"]
#         graph[item_name].extend(creates)
#
#     # Recursive function to perform the depth-first search
#     def dfs(node):
#         visited.add(node)
#         for neighbor in graph[node]:
#             if neighbor not in visited:
#                 dfs(neighbor)
#         result.insert(0, node)
#
#     # Perform topological sort for each item in the graph
#     for item_name in list(graph.keys()):  # Use a copy of keys
#         print(item_name)
#         if item_name not in visited:
#             dfs(item_name)
#
#     return result