#!/usr/bin/env python3

# from ansible.module_utils.basic import *

# def main():
    
#     fields = {"name": {"required": True, "type": "str" }}
    
#     module = AnsibleModule(argument_spec=fields)
#     response = {"hello": module.params.get("name")}
#     module.exit_json(changed=False, meta=response)



# if __name__ == '__main__':
#     main()

##############################################

import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.common.parsing import Conditional
from ansible.module_utils.network.common.utils import ComplexList
from ansible.module_utils.six import string_types
from ansible.module_utils.network.sros.sros import run_commands, sros_argument_spec, check_args

def to_lines(stdout):
    for item in stdout:
        if isinstance(item, string_types):
            item = str(item).split('\n')
        yield item


def parse_commands(module, warnings):
    command = ComplexList(dict(
        command=dict(key=True),
        prompt=dict(),
        answer=dict()
    ), module)
    commands = command(module.params['commands'])
    for index, item in enumerate(commands):
        if module.check_mode and not item['command'].startswith('show'):
            warnings.append(
                'only show commands are supported when using check mode, not '
                'executing `%s`' % item['command']
            )
        elif item['command'].startswith('conf'):
            module.fail_json(
                msg='sros_command does not support running config mode '
                    'commands.  Please use sros_config instead'
            )
    return commands


def main():
    """main entry point for module execution
    """
    argument_spec = dict(
        commands=dict(type='list', required=True),

        wait_for=dict(type='list', aliases=['waitfor']),
        match=dict(default='all', choices=['all', 'any']),

        retries=dict(default=10, type='int'),
        interval=dict(default=1, type='int')
    )

    argument_spec.update(sros_argument_spec)

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    result = {'changed': False}

    warnings = list()
    check_args(module, warnings)
    commands = parse_commands(module, warnings)
    result['warnings'] = warnings

    wait_for = module.params['wait_for'] or list()
    conditionals = [Conditional(c) for c in wait_for]

    retries = module.params['retries']
    interval = module.params['interval']
    match = module.params['match']

    while retries > 0:
        responses = run_commands(module, commands)

        for item in list(conditionals):
            if item(responses):
                if match == 'any':
                    conditionals = list()
                    break
                conditionals.remove(item)

        if not conditionals:
            break

        time.sleep(interval)
        retries -= 1

    if conditionals:
        failed_conditions = [item.raw for item in conditionals]
        msg = 'One or more conditional statements have not been satisfied'
        module.fail_json(msg=msg, failed_conditions=failed_conditions)

    result = {
        'changed': False,
        'stdout': responses,
        'stdout_lines': list(to_lines(responses))
    }

    module.exit_json(**result)


if __name__ == '__main__':
    main()