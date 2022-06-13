#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: dslam_eci_command

short_description: ECI DSLAM devices command module

version_added: "0.1"

description:
    - Executes telnet commands. Each command can have a list of prompts and their respective responses when interactive communications are required.
    - Renders telnet connection plugin's prompt using task vars.

author:
    - Iquall Networks

options:

  command:
      required: true
      description: 
        - List of commands to be executed in the telnet session. 
        - Interactive communication when a list of prompts and their respective responses is provided. See example below.
      vars:
           - name: command
      suboptions:
          type: array of dict type
          description: 
           - list of dict where each key is a regular expression expected and their respective value is the response to send.
           - if the first key is 'cmd', its value will be executed instead of 'command'. This is useful when trying to template cmd because ansible does not template dict keys.

  prompt:
      description: 
        - Expected prompt regex for telnet connections.
        - This prompt overwrites if already provided from inventory.
      type: str
      vars:
          - name: prompt

  cmdtimeout:
      description: 
        - Timeout in seconds for blocking operations like expecting prompt for telnet connections.
        - This timeout overwrites if already provided from inventory.
      type: int
      default: 15
      vars:
          - name: cmdtimeout

  init_delay:
      description: 
        - This parameter has been added since some devices need an initial delay.
        - Performs sleep function.
        - init_delay must be a positive integer in seconds.
      type: int
      default: 0
      vars:
          - name: init_delay

  intercmd_delay:
      description: 
        - Performs sleep function before executing next command.
        - intercmd_delay must be a positive integer in seconds.
      type: int
      default: 0
      vars:
          - name: intercmd_delay
'''

EXAMPLES = '''
---

  - name: testing
    dslam_eci_command:
      prompt: "{{ hostname }}#"
      cmdtimeout: 60
      command:
         - some_command
         - other_command:
            - "prompt1": "response1"
            - "prompt2": "response2"
         - another way to do the same:
            - cmd: other_command
            - "prompt1": "response1"
            - "prompt2": "response2"
         - exit_command

'''

RETURN = '''
command:
  description: the set of commands and their respective responses
  returned: always
  type: list of dicts
  sample: ["cmd1": "...", "cmd2": "..."]

rc:
  description: return code value.
  returned: always
  type: int
  sample: 0

failed:
  description: flag that indicates failure
  returned: failed
  type: boolean
  sample: True

msg:
  description: message that indicates failure
  returned: failed
  sample: "non-zero return code"

'''


from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError
from time import sleep
from jinja2 import Template


ECI_ERROR_RC = ["Unrecognized command"]
CMD_ERROR_RC = ECI_ERROR_RC

class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        if self._task.environment and any(self._task.environment):
            self._display.warning('telnet module does not support the environment keyword')

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        if self._play_context.check_mode:
            # in --check mode, always skip this module execution
            result['skipped'] = True
            return result

        if self._play_context.connection != 'telnet':
            error_msg = 'This module supports only \'telnet\' connections. Connection type \'{conn}\' is not valid'.format(conn=self._play_context.connection)
            raise AnsibleError(error_msg)

        self._get_additional_params()

        if not self._connection._connected:
            self._initialize(task_vars)

        result["command"] = list()
        result["rc"] = 0

        for e in self._commands:
            sleep(self._intercmd_delay)
            cmd = self._parse_command(e)
            status = self._low_level_execute_command(cmd, executable=False)
            stdout = status["stdout"]
            if any(cmd_error in stdout for cmd_error in CMD_ERROR_RC):
                result["rc"] = 1
            
            result["command"].append({ cmd: stdout })

        result['changed'] = True

        if 'rc' in result and result['rc'] != 0:
            result['failed'] = True
            result['msg'] = 'non-zero return code'

        return result


    def _get_additional_params(self):

        self._commands = self._task.args.get('command')
        if not isinstance(self._commands, list):
            raise AnsibleError("Parameter command must be a list type.")

        self._prompt = self._task.args.get('prompt')
        if self._prompt and not isinstance(self._prompt, str) and not isinstance(self._prompt, unicode):
            raise AnsibleError("Parameter prompt must be a str (Expected prompt regex).") 

        init_delay = self._task.args.get('init_delay')
        if init_delay and (not isinstance(init_delay, int) or init_delay < 0):
            raise AnsibleError("Parameter init_delay must be a positive integer type.")

        intercmd_delay = self._task.args.get('intercmd_delay')
        if intercmd_delay and (not isinstance(intercmd_delay, int) or intercmd_delay < 0):
            raise AnsibleError("Parameter intercmd_delay must be a positive integer type.")

        cmdtimeout = self._task.args.get('cmdtimeout')
        if cmdtimeout and (not isinstance(cmdtimeout, int) or cmdtimeout < 0):
            raise AnsibleError('Parameter cmdtimeout must be a positive integer type.')
            
        self._init_delay = init_delay if init_delay and init_delay > 0 else 0
        self._intercmd_delay = intercmd_delay if intercmd_delay and intercmd_delay > 0 else 0
        self._connection._cmdtimeout = cmdtimeout if cmdtimeout and cmdtimeout > 0 else 15
        

    def _initialize(self, task_vars):

        # retorno de carril
        self._connection._carriage_return = '\r'

        # sobreescritura por prompt del playbook
        if self._prompt:
            self._display.vvv('OVERWRITING PROMPT: {p}'.format(p=self._prompt), host=self._play_context.remote_addr)
            self._connection._prompt = [str(self._prompt)]
        else:
        # renderizacion de prompt del inventario
            try:
                t = Template('|'.join(self._connection._prompt))
                rendered = t.render(task_vars['hostvars'][task_vars.get('inventory_hostname')])
                self._display.vvv('RENDERED PROMPT: {p}'.format(p=rendered), host=self._play_context.remote_addr)
                self._connection._prompt = rendered.split('|')
            except:
                default_prompt = "\$\s?$|#\s?$|>\s?$"
                self._display.vvv('ERROR OCCURRED RENDERING PROMPT. USING DEFAULT: {p}'.format(p=default_prompt), host=self._play_context.remote_addr)
                self._connection._prompt = [default_prompt]
                pass

        self._connection._connect()
        # delay de inicializacion
        if self._init_delay:
            self._display.vvv('WAITING INITIALIZATION DELAY: {d} SECONDS'.format(d=self._init_delay), host=self._play_context.remote_addr)
            sleep(self._init_delay)

        # comando de salida
        self._connection._exit_cmd = "logout"


    def _parse_command(self, e):
        self._connection._interactive_prompt = list()
        self._connection._interactive_response = list()
        # comando simple
        if isinstance(e, str) or isinstance(e, unicode):
            cmd = e
        # comando con prompt
        elif isinstance(e, dict):
            # si la primer clave es 'cmd', el comando es su valor
            if e[e.keys()[0]][0].keys()[0] == 'cmd':
                cmd = e[e.keys()[0]][0].values()[0]
                e[e.keys()[0]].pop(0)
            else:
                cmd = e.keys()[0]
            for f in e[e.keys()[0]]:
                self._connection._interactive_prompt.append(f.keys()[0])
                self._connection._interactive_response.append(f[f.keys()[0]])
        else:
            raise AnsibleError("Parameter error: each command can have a list of prompts and their respective responses.")

        return cmd
connection._interactive_response = list()
        # comando simple
        if isinstance(e, str) or isinstance(e, unicode):
            cmd = e
        # comando con prompt
        elif isinstance(e, dict):
            # si la primer clave es 'cmd', el comando es su valor
            if e[e.keys()[0]][0].keys()[0] == 'cmd':
                cmd = e[e.keys()[0]][0].values()[0]
                e[e.keys()[0]].pop(0)
            else:
                cmd = e.keys()[0]
            for f in e[e.keys()[0]]:
                self._connection._interactive_prompt.append(f.keys()[0])
                self._connection._interactive_response.append(f[f.keys()[0]])
        else:
            raise AnsibleError("Parameter error: each command can have a list of prompts and their respective responses.")

        return cmd

