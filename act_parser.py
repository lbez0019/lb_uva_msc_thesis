import re
import itertools
from collections import defaultdict
from pyparsing import infixNotation, opAssoc, Literal, Word, alphas
from pyparsing import Keyword, nums, alphanums

operands = set()

AND = Literal("&&")
OR = Literal("||")
NOT = Literal("!")

operand = Word(alphas, alphanums+"_")
integer = Word(nums).setParseAction(lambda t: int(t[0]))
comparison_op = Literal("==") | Literal("!=") | Literal("<=") | Literal(">=") | Literal("<") | Literal(">")
comparison_expr = operand + comparison_op + (integer | operand)
expr = infixNotation(comparison_expr | operand,
    [
        (NOT, 1, opAssoc.RIGHT),
        (AND, 2, opAssoc.LEFT),
        (OR, 2, opAssoc.LEFT)
    ]
)


def calculate_permutations(lst):
    permutations = list(itertools.product([True, False], repeat=len(lst)))
    return permutations


def parse_string(input_string):
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
                    split_text = re.split(r"&&(?![^()]*\))", value)
                    value = [element.strip() for element in split_text]
                    result[key].extend(value)
                    current_key = key
                    break
            else:
                result[current_key][-1] += ' ' + line.strip()

    return result


def parse_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    pattern = r'(Act [\w\W]*?\.)'
    acts = re.findall(pattern, content, re.DOTALL)

    return acts


template_path = '../../eflint-server/web-server/test.eflint'  # Replace with the actual file path
parsed_acts = parse_file(template_path)
action_list = []

for act in parsed_acts:
    action = parse_string(act)
    action_list.append(action)

    for key in action:
        print(key)
        print(action[key])
        print("----")

    preconditions = action['Holds when'] + action['Conditioned by']

    print(preconditions)

    # Replace with your own list
    permutations = calculate_permutations(preconditions)
    print(len(permutations))
    for perm in permutations:
        print(perm)


def topological_sort(dependencies):
    graph = defaultdict(list)
    visited = set()
    result = []

    # Build the graph
    for item in dependencies:
        item_name = item["Act"][0]
        holds_when = item["Holds when"]
        creates = item["Creates"]
        graph[item_name].extend(creates)

    # Recursive function to perform the depth-first search
    def dfs(node):
        visited.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                dfs(neighbor)
        result.insert(0, node)

    # Perform topological sort for each item in the graph
    for item_name in list(graph.keys()):  # Use a copy of keys
        print(item_name)
        if item_name not in visited:
            dfs(item_name)

    return result


items = [
    {'Act': ['declare-winner'], 'Actor': ['administrator'], 'Recipient': ['candidate'], 'Holds when': ['administrator', 'candidate', 'test-fact'], 'Conditioned by': ['Not(vote-concluded())', 'voters-done()', '(Forall other-candidate : Count(Foreach vote : vote When vote', 'vote.'], 'Creates': [], 'Terminates': [], 'Obfuscates': []},
    {'Act': ['test-act'], 'Actor': ['tender_id'], 'Recipient': [], 'Holds when': ['tender_id, tender_id2'], 'Conditioned by': ['documents_added("tender")'], 'Creates': ['test-fact.'], 'Terminates': [], 'Obfuscates': []
    }
]

sorted_items = topological_sort(items)
print(sorted_items)
# for item_name in sorted_items:
#     item = next(item for item in items if item[0] == item_name)
#     print(item)