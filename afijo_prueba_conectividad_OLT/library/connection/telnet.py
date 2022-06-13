from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


DOCUMENTATION = '''
    connection: telnet

    short_description: connect via telnet client using a persistent connection.

    description:
        - This connection plugin allows ansible to execute tasks on the Ansible 'controller' instead of on a remote host via telnet.
        - Supports interactive communication when a list of prompts and their respective responses is provided.
        - This plugin can import a lot of settings from inventory when defined in 'connection_args'.

    author: Iquall Networks

    version_added: historical

    options:
    
      host:
          required: true
          description: Hostname/ip to connect to.
          vars:
               - name: ansible_host

      user:
          required: true
          description: User to login/authenticate as.
          vars:
              - name: ansible_user

      password:
          description: Authentication password for the user.
          vars:
              - name: ansible_password
      port:
          type: int
          description: Port number on the remote device listening for telnet connections.
          default: 23
          vars:
              - name: ansible_port
      timeout:
          type: int
          description: Timeout in seconds for the connection attempt
          default: 15
          vars:
              - name: ansible_timeout

      connection_args:
          description: Arguments to pass to the telnet connector from inventory
          
          vars:
              - name: connection_args

          suboptions:
            cmdtimeout:
              type: int
              description: Timeout in seconds for blocking operations like expecting prompt.
              default: 15

            login_prompt:
              description: Expected regular expression for login with username input.
              default: '[lL]ogin\\s?:\\s?|[uU]ser\\s?name\\s?:\\s?'

            password_prompt:
              description: Expected regular expression for a password input.
              default: '([uU]ser )?[pP]assword\\s?:\\s?'

            prompt:
              description: Expected prompt regular expression.
              default: '\\$\\s?$|#\\s?$|>\\s?$'

            bad_credentials:
              description: Expected regular expression for a failed authentication.
              default: "incorrect|invalid"

            exit_commands: 
              description: Commands that close the connection and should not wait for any prompt separated by \'|\' .
              default: "exit|logout|quit"


'''

EXAMPLES = '''
# The following is an example of hostvars for 127.0.0.1:

  "127.0.0.1": {
    "ansible_connection": "telnet", 
    "ansible_user": "root", 
    "ansible_password": "pa$sw0rd", 
    "ansible_timeout": 20,
    "connection_args": {
      "cmdtimeout": 25,
      "login_prompt": "[lL]ogin: ",
      "password_prompt": "Password: ",
      "prompt": ":~\\$ |# ",
      "bad_credentials": "incorrect|bad login",
      "exit_commands": "exit|logout",
    },
  }

'''


import os
import shutil
import subprocess
import fcntl
import getpass
import telnetlib
from time import sleep

import ansible.constants as C
from ansible.compat import selectors
from ansible.errors import AnsibleError, AnsibleFileNotFound, AnsibleConnectionFailure
from ansible.module_utils.six import text_type, binary_type
from ansible.module_utils._text import to_bytes, to_native, to_text
from ansible.plugins.connection import ConnectionBase


try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class Connection(ConnectionBase):
    ''' Local based connections '''

    transport = 'telnet'
    has_pipelining = False
    # _remote_is_local es una clave importante, citando plugins/action/__init__.py, linea 273-279
    # Network connection plugins (network_cli, netconf, etc.) execute on the controller, rather than the remote host.
    # As such, we want to avoid using remote_user for paths  as remote_user may not line up with the local user
    # This is a hack and should be solved by more intelligent handling of remote_tmp in 2.7
    #if getattr(self._connection, '_remote_is_local', False):
    #    tmpdir = C.DEFAULT_LOCAL_TMP
    #else:
    #    tmpdir = self._remote_expand_user(remote_tmp, sudoable=False)
    # Lo que explica es que ignora el usuario definido en el inventario para el host en caso de conexion local
    # Por lo que se necesita que sea falso
    # Este parametro no afecta el hecho que intente copiar archivos de ejecucion hacia el host destino
    _remote_is_local = False

    def __init__(self, *args, **kwargs):
        # Necesito heredar de la clase ConnectionBase como primera instancia para obtener sus miembros
        # Como lo es _play_context. Para poder recibir desde el inventario el argumento "telnet_args"
        # se debe agregar el elemento telnet_args=('telnet_args', ) a MAGIC_VARIABLE_MAPPING en 
        # el archivo constants.py
        super(Connection, self).__init__(*args, **kwargs)

        self._host = self._play_context.remote_addr
        self._port = self._play_context.port if hasattr(self._play_context, 'port') else '23'
        self._timeout = self._play_context.timeout if hasattr(self._play_context, 'timeout') else 10

        self._user = self._play_context.remote_user
        self._password = self._play_context.password

        self._cmdtimeout = 15
        self._login_prompt = ["[lL]ogin\s?:\s?|[uU]ser\s?name\s?:\s?"]
        self._password_prompt = ["([uU]ser )?[pP]assword\s?:\s?"]
        self._prompt = ["\$\s?$|#\s?$|>\s?$"]
        self._bad_credentials = ["incorrect|invalid"]
        self._exit_commands = ["exit", "logout", "quit"]
        self._pagination_prompt = []
        self._pagination_delay = 1

        self._carriage_return = ''
        self._interactive_prompt = []
        self._interactive_response = []
        self._exit_cmd = ''
        self._exit_confirm = dict()

        # connection_args (inventario)
        self._parse_connection_args()


    def _connect(self):

        if not self._connected:
            display.vvv(u"ESTABLISH TELNET CONNECTION FOR USER: {0}".format(self._play_context.remote_user), host=self._play_context.remote_addr)
            # Establecer conexion telnet
            try:
                self._tn = telnetlib.Telnet(self._host, self._port, self._timeout)
            except:
                raise AnsibleConnectionFailure("Failed to connect to the host via telnet: \'{host}:{port}\' timeout: {timeout}s".format(
                    host=self._host, port=self._port, timeout=self._timeout))
            
            self._display.vvv("CONNECTION ESTABLISHED", host=self._host)

            self._check_expect(self._tn.expect(self._login_prompt, self._cmdtimeout))
            self._tn.write('{user}{cr}\n'.format(user=to_native(self._user), cr=self._carriage_return))

            if self._password:
                self._check_expect(self._tn.expect(self._password_prompt, self._cmdtimeout))
                self._tn.write('{password}{cr}\n'.format(password=to_native(self._password), cr=self._carriage_return))
            
            index = self._check_expect(self._tn.expect(self._prompt + self._bad_credentials, self._cmdtimeout))[0]
            if index > len(self._prompt)-1:
                raise AnsibleError("Authentication failed (bad credentials)")

            self._display.vvv("LOGGED IN SUCCESSFULY", host=self._host)

            self._connected = True
        return self


    def exec_command(self, cmd, in_data=None, sudoable=True):
        # Heredar este metodo asegura una conexion previa a la ejecucion del comando
        super(Connection, self).exec_command(cmd, in_data=in_data, sudoable=sudoable)

        cmd = cmd.decode('ascii', 'ignore').encode('utf-8')
        self._display.vvv(u"EXEC {0}".format(to_text(cmd)), host=self._host)

        self._tn.write(cmd+self._carriage_return+'\n')

        if self._interactive_prompt and self._interactive_response:
            if len(self._interactive_prompt) != len(self._interactive_response):
                raise AnsibleError("Prompts and Responses length mismatch. Prompts: "+
                                    str(len(self._interactive_prompt))+", Responses: "+
                                    str(len(self._interactive_response)))
            for i in range(len(self._interactive_prompt)):
                text = self._check_expect(self._tn.expect([self._interactive_prompt[i]], self._cmdtimeout))[2]
                p = (str(text)+self._tn.read_very_eager()).decode('ascii', 'ignore').encode('utf-8')
                r = self._interactive_response[i].decode('ascii', 'ignore').encode('utf-8')
                self._display.vvv("{prompt}{response}".format(prompt=p, response=r), host=self._host)
                self._tn.write(r+self._carriage_return+'\n')

        if cmd in self._exit_commands:
            return (0, "", "")
        
        result = self._check_expect(self._tn.expect(self._pagination_prompt+self._prompt, self._cmdtimeout))
        
        if self._pagination_prompt:
            result = self._check_pagination(result)

        rc, output = self._process_output(cmd, result)
        
        return (rc, output, "")


    def put_file(self, in_path, out_path):

        super(Connection, self).put_file(in_path, out_path)

        display.vvv(u"PUT {0} TO {1}".format(in_path, out_path), host=self._play_context.remote_addr)
        if not os.path.exists(to_bytes(in_path, errors='surrogate_or_strict')):
            raise AnsibleFileNotFound("file or module does not exist: {0}".format(to_native(in_path)))
        try:
            shutil.copyfile(to_bytes(in_path, errors='surrogate_or_strict'), to_bytes(out_path, errors='surrogate_or_strict'))
        except shutil.Error:
            raise AnsibleError("failed to copy: {0} and {1} are the same".format(to_native(in_path), to_native(out_path)))
        except IOError as e:
            raise AnsibleError("failed to transfer file to {0}: {1}".format(to_native(out_path), to_native(e)))

    def fetch_file(self, in_path, out_path):

        super(Connection, self).fetch_file(in_path, out_path)

        display.vvv(u"FETCH {0} TO {1}".format(in_path, out_path), host=self._play_context.remote_addr)
        self.put_file(in_path, out_path)

    def close(self):
        if self._tn:
            if self._exit_cmd:
                self._interactive_prompt = self._exit_confirm.keys() if self._exit_confirm else list()
                self._interactive_response = self._exit_confirm.values() if self._exit_confirm else list()
                self._display.vvv("EXIT COMMAND: {cmd}".format(cmd=cmd), host=self._host)
                self.exec_command(self._exit_cmd)
            self._tn.close()
        self._connected = False
        self._display.vvv("TELNET CONNECTION CLOSED", host=self._host)
        

    #
    # Custom methods
    #
    def _process_output(self, cmd, result):
        # result es la terna de 3 elementos que devuelve Telnet.expect()
        # Siendo el elemento 0 el index del elemento que matcheo con el expect
        # el elemento 1 la expresion del elemento match
        # el elemento 2 el texto resultado que es lo que quiero parsear
        terns = result[2].split('\r\n')
        if len(terns) == 1:
            self._display.vvv("PARSED OUTPUT: ", host=self._host)
            return 0, ""
        else:
            self._display.vvv("PARSED PROMPT: "+ str(terns[-1]), host=self._host)
            del terns[0] # el comando ejecutado
            del terns[-1] # la ultima linea: 'user@user-pc:~$'

            parsed_output = list()
            if any(terns):
                for i in xrange(len(terns)):
                    if terns[i]: parsed_output.append(terns[i])
            
            # Si terns resulto vacio, parsed_output sera [], lo que devuelve un string vacio
            self._display.vvv("PARSED OUTPUT: "+ str(parsed_output).decode('ascii', 'ignore').encode('utf-8'), host=self._host)
            return 0, '\r\n'.join(parsed_output).decode('ascii', 'ignore').encode('utf-8')


    def _check_expect(self, result):
        index, match, text = result
        if index == -1:
            raise AnsibleError("TIMEOUT REACHED FOR TELNET EXPECT")
        return result


    def _check_pagination(self, result):
        # funcion auxiliar para eliminar terminos que no corresponden
        def _strip_last_term(b):
            _r = b.split('\r\n')
            # elimino ultimo termino correspondiente al prompt. ej: "Press any key to continue (Q to quit)"
            del _r[-1]
            # elimino caracteres de control. ej: ^M^M
            r = [t.strip('\r\r').strip('\r') for t in _r]
            return '\r\n'.join(r)
        
        index, match, text = result
        # si el index no corresponde al paginado, retorna
        if not index < len(self._pagination_prompt):
            return result

        book = _strip_last_term(text)
        for p in self._page_gen():
            page = _strip_last_term(p)
            book = '\r\n'.join([book, page])

        return index, match, book


    def _page_gen(self):
        # envia espacios hasta que el expect caiga fuera del paging prompt
        index = 0
        while index < len(self._pagination_prompt):
            sleep(self._pagination_delay)
            self._tn.write(' ')
            index, _, text = self._check_expect(self._tn.expect(self._pagination_prompt+self._prompt, self._cmdtimeout))
            yield text

    def _parse_connection_args(self):
        # si hay algun parametro recibido desde el inventario (connection_args), lo settea
        if not hasattr(self._play_context, 'connection_args'):
            self._display.vvv("NO 'connection_args' GIVEN. USING DEFAULTS", host=self._host)
            return
        
        self._display.vvv("BEGIN PARSE 'connection_args'", host=self._host)

        for (key, value) in self._play_context.connection_args.iteritems():
            if key == 'cmdtimeout' or key == 'pagination_delay':
                if not (isinstance(value, int) and value > 0):
                    raise AnsibleError("invalid connection argument. {key}: {value}. \'{key}\' must be a positive integer type".format(key=key, value=self._play_context.connection_args[key]))
            elif not(isinstance(value, str) or isinstance(value, unicode)):
                raise AnsibleError("invalid connection argument. {key}: {value}. \'{key}\' must be str or unicode type.".format(key=key, value=self._play_context.connection_args[key]))
        
        conn_args=[]
        if 'cmdtimeout' in self._play_context.connection_args and self._play_context.connection_args['cmdtimeout']:
            self._cmdtimeout = self._play_context.connection_args['cmdtimeout']
            conn_args.append('cmdtimeout')
        if 'loginPrompt' in self._play_context.connection_args and self._play_context.connection_args['loginPrompt']:
            self._login_prompt = [self._play_context.connection_args['loginPrompt']]
            conn_args.append('loginPrompt')
        if 'passwordPrompt' in self._play_context.connection_args and self._play_context.connection_args['passwordPrompt']:
            self._password_prompt = [self._play_context.connection_args['passwordPrompt']]
            conn_args.append('passwordPrompt')
        if 'prompt' in self._play_context.connection_args and self._play_context.connection_args['prompt']:
            self._prompt = [self._play_context.connection_args['prompt']]
            conn_args.append('prompt')
        if 'paginationPrompt' in self._play_context.connection_args and self._play_context.connection_args['paginationPrompt']:
            self._pagination_prompt = [self._play_context.connection_args['paginationPrompt']]
            conn_args.append('paginationPrompt')
        if 'paginationDelay' in self._play_context.connection_args and self._play_context.connection_args['paginationDelay']:
            self._pagination_delay = self._play_context.connection_args['paginationDelay']
            conn_args.append('paginationDelay')
        if 'badCredentials' in self._play_context.connection_args and self._play_context.connection_args['badCredentials']:
            self._bad_credentials = [self._play_context.connection_args['badCredentials']]
            conn_args.append('badCredentials')
        if 'exitCommands' in self._play_context.connection_args and self._play_context.connection_args['exitCommands']:
            self._exit_commands = [str(x) for x in self._play_context.connection_args['exitCommands'].split('|')]
            conn_args.append('exitCommands')
        
        if conn_args:
            self._display.vvv("PARAMETERS '"+"', '".join(conn_args)+"' SET FROM 'connection_args'.", host=self._host)

        self._display.vvv("DONE.", host=self._host)
