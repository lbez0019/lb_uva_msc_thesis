class Utils:
    @staticmethod
    def compute_jaccard_similarity(selected_actions, scenario_actions):
        set1 = set(selected_actions)
        set2 = set(scenario_actions)

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        similarity = intersection / union
        return similarity

    @staticmethod
    def has_same_elements(list1, list2):
        return sorted(list1) == sorted(list2)

    @staticmethod
    def split_string_until_open_parenthesis(creates):
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

    @staticmethod
    def trim_values_end(values):
        for i in range(len(values)):
            if values[i].endswith('.'):
                values[i] = values[i].rstrip('.')
        return values

    @staticmethod
    def update_with_merge(current_dict, new_dict):
        for key, value in new_dict.items():
            if key in current_dict:
                current_dict[key] += value
            else:
                current_dict[key] = value
        return current_dict
