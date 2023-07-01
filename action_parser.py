import re


class ActionParser:
    def __init__(self):
        self.actions = {}

    @staticmethod
    def calculate_permutations(operands, operators, parsed_operators, tokens):
        permutations = []
        for i in range(2 ** len(operands)):
            binary = bin(i)[2:].zfill(len(operands))
            operand_permutation = [operands[j] if bit == '0' else 'True' for j, bit in enumerate(binary)]

            # Reintroduce the operators in their original place
            expression_permutation = []
            operand_index = 0
            operator_index = 0

            for token in tokens:
                if token not in operators:
                    expression_permutation.append(operand_permutation[operand_index])
                    operand_index += 1
                else:
                    expression_permutation.append(parsed_operators[operator_index])
                    operator_index += 1

            permutations.append(expression_permutation)

        return permutations

    @staticmethod
    def derive_alternative_preconditions(expression):
        operators = ['&&', '||']
        # Split the expression into tokens
        tokens = expression.split(' ')
        tokens = [token for token in tokens if token]
        operands = [token for token in tokens if token not in operators]
        parsed_operators = [token for token in tokens if token in operators]

        # Generate permutations using the calculate_permutations function
        permutations = ActionParser.calculate_permutations(operands, operators, parsed_operators, tokens)

        return permutations

    @staticmethod
    def join_output_with_operators(output, equality_operators):
        result = output[0]

        for i in range(1, len(output)):
            if output[i] in equality_operators or output[i-1] in equality_operators:
                result += output[i]
            else:
                result += ' ' + output[i]

        return result

    @staticmethod
    def parse_file(file_path):
        with open(file_path, 'r') as file:
            content = file.read()

        pattern = r'(?m)^(?!Extend)(Act [\w\W]*?\.)'
        acts = re.findall(pattern, content, re.DOTALL)

        return acts

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
                            pattern = r",(?![^()]*\))"  # Only commas not within brackets
                            value = re.split(pattern, value)
                            value = [element.strip() for element in value]
                            result[key].extend(value)

                        current_key = key
                        break
                else:
                    result[current_key][-1] += ' ' + line.strip()

        return result

    def retrieve_action_list(self):
        template_path = './policies/policies.eflint'  # Replace with the actual file path
        parsed_acts = self.parse_file(template_path)
        action_list = []

        for act in parsed_acts:
            action = self.parse_string(act)
            action_list.append(action)
            self.actions[action["Act"][0]] = action

        return action_list

    @staticmethod
    def rpn_to_infix(rpn_expression):
        stack = []
        operators = {'Not', '&&', '||', '==', '!=', '<', '>', '<=', '>='}

        # rpn_expression = self.single_bracketed_token(rpn_expression)

        for token in rpn_expression:
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
