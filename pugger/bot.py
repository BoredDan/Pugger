import discord
import asyncio
import configparser
from pkg_resources import resource_filename
from pugger.model import Pickup
from pugger.model import role_to_key

client = discord.Client()
pickup_store = {}

@client.async_event
def on_ready():
    print('Logged in as ' + client.user.name + '(' + client.user.id + ')')
    print('------')

@client.async_event
def on_message(message):
    if message.author != client.user and not message.channel.is_private:
        if message.channel.permissions_for(message.server.me).manage_messages:
            yield from client.delete_message(message)
        
        if message.content.startswith('!pug new'):
            args = message.content.replace('!pug new', '', 1).split()
            yield from create_pickup(message.channel, *args)
        elif message.content.startswith('!pug join'):
            args = message.content.replace('!pug join', '', 1).split()
            yield from add_player(message.channel, message.author, *args)
        elif message.content.startswith('!pug leave'):
            args = message.content.replace('!pug leave', '', 1).split()
            yield from remove_player(message.channel, message.author, *args)
        elif message.content.startswith('!pug delete'):
            args = message.content.replace('!pug delete', '', 1).split()
            yield from delete_pickup(message.channel, *args)
        elif message.content.startswith('!pug list'):
            yield from list_pickup_store(message.channel, message.author)
            
@client.async_event
def on_channel_delete(channel):
    if channel.id in pickup_store:
        del pickup_store[channel.id]

@client.async_event
def on_member_remove(member):
    yield from remove_player_from_server(member)
                
@client.async_event
def on_member_update(before, after):
    #TODO: Consider adding idle, probably as an option
    if after.status == discord.Status.offline or after.status == discord.Status.do_not_disturb:
        yield from remove_player_from_server(after)
        
def generate_embed(pickup):
    server = client.get_channel(pickup.channel_id).server

    embed = discord.Embed(description = pickup.name_and_id, type = 'rich', timestamp = pickup.timestamp)
    embed.set_footer(text = pickup.id)
    
    for role in sorted(pickup.roles, key = lambda role: (role or chr(0x10FFFF)).lower()):
        player_list = ''
        for player_id in pickup.unpicked_players_in(role):
            player = server.get_member(player_id)
            if player_list:
                player_list += '\n- ' + player.name
            else:
                player_list = '- ' + player.name
        if not role:
            if len(pickup.roles) > 1:
                role = 'No Role'
            else:
                role = 'Unpicked'
        if not player_list:
            player_list = "~~   ~~"
        embed.add_field(name = "__" + role + "__", value = player_list)
        
    if len(pickup.roles) > 1:
        player_list = ''
        for player_id in pickup.unpicked_players:
            player = server.get_member(player_id)
            if player_list:
                player_list += '\n- ' + player.name
            else:
                player_list = '- ' + player.name
        if not player_list:
            player_list = "~~   ~~"
        embed.add_field(name = '__All Unpicked__', value = player_list, inline = False)
        
    
    return embed
        
@asyncio.coroutine
def update_display(pickup):
    pickup_embed = generate_embed(pickup)
    
    pickup_message = pickup_store[pickup.channel_id][pickup.id]['display']

    yield from client.edit_message(pickup_message, '', embed = pickup_embed)
        
@asyncio.coroutine
def create_pickup(channel, *args):
    pickup_embed = discord.Embed(description = 'Creating new pickup', type = 'rich')
    pickup_message = yield from client.send_message(channel, embed = pickup_embed)
    
    pickup = Pickup(channel.id)
    if not pickup.channel_id in pickup_store:
        pickup_store[pickup.channel_id] = {}
    pickup_store[pickup.channel_id][pickup.id] = {'pickup' : pickup, 'display' : pickup_message}
    
    yield from update_display(pickup)
    
    print("Created " + pickup.unique_id)
        
@asyncio.coroutine
def delete_pickup(channel, *args):
    if channel.id in pickup_store:
        if len(pickup_store[channel.id]) == 1:
            pickup_key_tuple = list(pickup_store[channel.id].keys())[0], 
            if not args:
                args = pickup_key_tuple
            elif args[0].upper() != pickup_key_tuple[0]:
                args = pickup_key_tuple + args
        if args:
            delete_message = yield from client.send_message(channel, 'Deleting pickup ' + args[0].upper())
            deleted_message = False
            
            if args[0].upper() in pickup_store[channel.id]:
                pickup = pickup_store[channel.id][args[0].upper()]['pickup']
                yield from client.delete_message(pickup_store[channel.id][args[0].upper()]['display'])
                del pickup_store[channel.id][args[0].upper()]
                deleted_message = True
            
            yield from client.delete_message(delete_message)
            
            if deleted_message:
                print("Deleted " + pickup.unique_id)
        
@asyncio.coroutine
def add_player(channel, player, *args):
    if channel.id in pickup_store and pickup_store[channel.id]:
        if len(pickup_store[channel.id]) == 1:
            pickup_key_tuple = list(pickup_store[channel.id].keys())[0], 
            if not args:
                args = pickup_key_tuple
            elif args[0].upper() != pickup_key_tuple[0]:
                args = pickup_key_tuple + args
        if args:
            add_message = yield from client.send_message(channel, 'Adding ' + player.name + ' to ' + args[0].upper())
            
            added_player = False
            
            if args[0].upper() in pickup_store[channel.id]:
                pickup = pickup_store[channel.id][args[0].upper()]['pickup']
                
                roles = set()
                role = ''
                #add list roles to the set where "" encapsulate all multi word roles
                for arg in args[1:]:
                    if role: #means we have started concatenating a multi word role
                        role += ' ' #is not the first word so safe to add space
                        if arg.endswith('"'): #last word so finish concatenating and add
                            role += arg.rstrip('"')
                            roles.add(role)
                            role = ''
                        else: #is not the last word so concantinate and delay addin
                            role += arg
                    elif arg.startswith('"'): #we are starting a "" encapsulated role
                        if arg.endswith('"'): #is a single word so simply strip "'s and add
                            roles.add(arg.lstrip('"').rstrip('"'))
                        else: #is a multi word role so start concatenating the role and delay adding
                            role = arg.lstrip('"')
                    else: #is a single word role so just add
                        roles.add(arg)
                roles.add(None)
                pickup.add_player(player.id, roles)
                added_player = True
                yield from update_display(pickup)
            
            yield from client.delete_message(add_message)
            
            if added_player:
                if roles:
                    for role in roles:
                        if role and pickup.has_role(role):
                            print("Addded " + player.id + " to " + role_to_key(role) + " in " + pickup.unique_id)
                else:
                    print("Addded " + player.id + " to " + pickup.unique_id + " with no role")
        
@asyncio.coroutine
def remove_player(channel, player, *args):
    if channel.id in pickup_store and pickup_store[channel.id]:
        if len(pickup_store[channel.id]) == 1:
            pickup_key_tuple = list(pickup_store[channel.id].keys())[0], 
            if not args:
                args = pickup_key_tuple
            elif args[0].upper() != pickup_key_tuple[0]:
                args = pickup_key_tuple + args
        if args:
            add_message = yield from client.send_message(channel, 'Removing ' + player.name + ' from ' + args[0].upper())

            removed_player = False
            
            if args[0].upper() in pickup_store[channel.id]:
                pickup = pickup_store[channel.id][args[0].upper()]['pickup']
                
                roles = set()
                role = ''
                #add list roles to the set where "" encapsulate all multi word roles
                for arg in args[1:]:
                    if role: #means we have started concatenating a multi word role
                        role += ' ' #is not the first word so safe to add space
                        if arg.endswith('"'): #last word so finish concatenating and add
                            role += arg.rstrip('"')
                            roles.add(role)
                            role = ''
                        else: #is not the last word so concatenate and delay adding
                            role += arg
                    elif arg.startswith('"'): #we are starting a "" encapsulated role
                        if arg.endswith('"'): #is a single word so simply strip "'s and add
                            roles.add(arg.lstrip('"').rstrip('"'))
                        else: #is a multi word role so start concatenating the role and delay adding
                            role = arg.lstrip('"')
                    else: #is a single word role so just add
                        roles.add(arg)
                 
                pickup.remove_player(player.id, roles)
                removed_player = True
                yield from update_display(pickup)
            
            yield from client.delete_message(add_message)
            
            if removed_player:
                if roles:
                    for role in (set(map(role_to_key, roles)) & set(map(role_to_key, pickup.roles))):
                        print("Removed " + player.id + " from " + role_to_key(role) + " in " + pickup.unique_id)
                else:
                    print("Removed " + player.id + " from " + pickup.unique_id)
        
@asyncio.coroutine
def remove_player_from_channel(channel, player):
    if channel.id in pickup_store:
        for id in pickup_store[channel.id]:
            yield from remove_player(channel, player, id)
        
@asyncio.coroutine
def remove_player_from_server(player):
    for channel in player.server.channels:
        yield from remove_player_from_channel(channel, player)
        
@asyncio.coroutine
def list_pickup_store(channel, user, format = None):
    if channel.id in pickup_store and pickup_store[channel.id]:
        yield from client.send_message(user, "Current pickups for #" + channel.name + " in " + channel.server.name + ':')
        for id in pickup_store[channel.id]:
            pickup = pickup_store[channel.id][id]['pickup']
            yield from client.send_message(user, embed = generate_embed(pickup))
    else:
        yield from client.send_message(user, "No active pickups for #" + channel.name + " in " + channel.server.name +'.')
        
def init(*args):
    config_file = resource_filename(__name__, 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_file)
    if 'discord' in config and 'token' in config['discord']:
        client.run(config['discord']['token'])
    else:
        print("No discord bot token given in config file!")

if __name__ == '__main__':
    init()