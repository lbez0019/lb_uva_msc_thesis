class FactGenerator:
    @staticmethod
    def define_fact_payload(value_count, uuid, fact, fact_values):
        if value_count == 1:
            return f'{{ "uuid": "{uuid}", "request-type": "command", "data":	{{ "command": "create", "value": {{' \
                   f'"fact-type" : "{fact}", "value" : {fact_values[0][1]} }} }} }}'
        else:
            sub_values = ""
            for item in fact_values:
                sub_values += f'{{ "fact-type" : "{item[0]}", "value" : {item[1]} }},'
            sub_values = sub_values[:-1]
            return f'{{ "uuid": "{uuid}", "request-type": "command", "data":	{{ "command": "create", "value": {{' \
                   f'"fact-type" : "{fact}", "value" : [{sub_values}] }} }} }}'

    @staticmethod
    def composite_fact_creation( document_handler, composite_facts, composite_fact_values):
        for fact in document_handler.composite_components:
            parsed_fact = fact.lower()
            composite_fact_values[parsed_fact] = []

            for item in document_handler.composite_components[parsed_fact]:
                composite_fact_values[parsed_fact].append([])
                item.sort()
                if not len(item) == 0:
                    fact = f'Fact {parsed_fact} Identified by '
                    for item_property in item:
                        fact += f' {item_property[0]} *'
                        composite_fact_values[parsed_fact][-1].append([item_property[0], item_property[1]])

                    if fact[-1] == '*':
                        fact = fact[:-1] + '.'

                    composite_facts.add(fact)
