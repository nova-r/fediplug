'''Mastodon interface.'''

LISTEN_TO_HASHTAG = 'fediplug'

import click
import lxml.html as lh
from lxml.html.clean import clean_html
import mastodon
import re
from itertools import cycle

from fediplug.cli import options
import fediplug.keyring as keyring
from fediplug.buttplugio import trigger_actuators

Mastodon = mastodon.Mastodon


def api_base_url(instance):
    '''Create an API base url from an instance name.'''

    return 'https://' + instance

class StreamListener(mastodon.StreamListener):
    '''Listens to a Mastodon timeline and adds buttplug instructions the given queue.'''

    def __init__(self, plug_client, instance, users, event_loop):
        self.plug_client = plug_client
        self.instance = instance
        self.users = users
        self.event_loop = event_loop
        self.regular_expression = re.compile(r"((?:\b(?:\d+s)(?:\s|\b))+(?:\d+%)?)+")
        # extracts commands from captured toots for usage in buttplug.io actuator
        # if no power % is given, a default will be set later
        # examples:
        # input: "#fediplug @nova_ have fun :) 10s 50% 4s 5s"
        # output: ["10s 50%", "4s 5s"]
        #
        # input: "60% 10s @maeve 5s 7s 10% foo bar 8s baz 20% 30s 1337."
        # output: ["10s 5s 7s 10%", "8s 20%", "30s"]
        #
        # input: "10s6 80%"
        # output: []
        #
        # watch out for this quirk: 
        # input "10s 70%8"
        # output: ["10s 70%"]
        # TODO: fix this, it should match the 70% because there isnt a word boundary after it

        if options['debug']:
            print(rf'listener initialized with users={self.users}')

    def on_update(self, status):
        if options['debug']:
            print(rf'incoming status: acct={status.account.acct}')

        if self.users and normalize_username(status.account.acct, self.instance) not in self.users:
            # TODO: only do this if no toot from self.users with #fediplug has been captured yet, else check in_reply_to_ID
            if options['debug']:
                print('skipping status due to username filtering')
            return

        tags = extract_tags(status)
        if options['debug']:
            print(rf'expecting: {LISTEN_TO_HASHTAG}, extracted tags: {tags}')

        if LISTEN_TO_HASHTAG in tags:
            # TODO: if Hashtag matches and toot is from mentioned account, then get toot ID

            ''' Here we extract the instructions for the butplug'''
            buttplug_instructions = extract_buttplug_instructions(status, self.regular_expression)
            if buttplug_instructions:  # check if buttplug_instructions is not empty
                for buttplug_instruction in buttplug_instructions:
                    click.echo(f'queueing instructions {buttplug_instruction}')
                    self.event_loop.run_until_complete(trigger_actuators(self.plug_client, buttplug_instruction))    

def register(instance):
    '''Register fediplug to a Mastodon server and save the client credentials.'''

    client_id, client_secret = Mastodon.create_app('fediplug', scopes=['read'], api_base_url=api_base_url(instance))
    keyring.set_credential(instance, keyring.CREDENTIAL_CLIENT_ID, client_id)
    keyring.set_credential(instance, keyring.CREDENTIAL_CLIENT_SECRET, client_secret)

def build_client(instance, client_id, client_secret, access_token=None):
    '''Builds a Mastodon client.'''

    return Mastodon(api_base_url=api_base_url(instance),
                    client_id=client_id, client_secret=client_secret, access_token=access_token)

def get_auth_request_url(instance, client_id, client_secret):
    '''Gets an authorization request URL from a Mastodon instance.'''

    return build_client(instance, client_id, client_secret).auth_request_url(scopes=['read'])

def login(instance, client_id, client_secret, grant_code):
    '''Log in to a Mastodon server and save the user credentials.'''

    client = build_client(instance, client_id, client_secret)
    access_token = client.log_in(code=grant_code, scopes=['read'])
    keyring.set_credential(instance, keyring.CREDENTIAL_ACCESS_TOKEN, access_token)

def stream(instance, users, client_id, client_secret, access_token, plug_client, event_loop):
    '''Stream statuses and add them to a queue.'''

    client = build_client(instance, client_id, client_secret, access_token)
    users = [normalize_username(user, instance) for user in users]
    listener = StreamListener(plug_client, instance, users, event_loop)
    
    click.echo(f'==> Streaming from {instance}')
    client.stream_user(listener)

def extract_tags(toot):
    '''Extract tags from a toot.'''

    return [tag['name'] for tag in toot['tags']]

def normalize_username(user, instance):
    user = user.lstrip('@')
    parts = user.split('@')
    if options['debug']:
        print(rf'parts: {parts}')

    if len(parts) == 1 or parts[1] == instance:
        return parts[0]
    else:
        return user

def extract_buttplug_instructions(status, regular_expression):
    '''Extract buttplug instruction informations from a toot.'''
    toot = lh.fromstring(status['content'])
    toot = clean_html(toot)
    toot = toot.text_content()
    instructions = regular_expression.findall(toot)
    actuator_commands = []  # List of tuples with (duration in seconds, power in range 0..1)
    for instruction in instructions:
        commands = instruction.strip().split(" ")
        print(commands)
        if commands[-1][-1] != "%":
            commands.append("100%")
        commands = [int(command[:-1]) for command in commands]
        power = commands.pop()/100  # convert power from % to range 0..1
        commands = list(zip(commands, cycle([power])))
        print(commands)
        actuator_commands.extend(commands)
    print(rf'extracted buttplug_instruction: {actuator_commands}')
    return actuator_commands