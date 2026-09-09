"""Versioned JSON object graph for complete careers, preserving shared identities.

Only data classes already imported by the game can be restored. No module named
by a save is imported, no constructors run, and no pickle is accepted.
"""
import collections
import enum
import sys
import types

from game.game_time import current_game_time


EXCLUDED = {
    'ui', 'GAME_LOG', 'sound_manager', 'scene_backdrop', 'ui_shell', 'ui_signals',
    'OPPORTUNITY_CATALOG', 'SCRIPT_DIR', '_poi_venue_id_map', '_local_action_lookup',
    '_raw_interaction_map', 'running', 'game_state', 'selected_poi', 'selected_npc',
    'performance_manager', 'travel_manager', 'active_performance', 'transit_session',
    'simulation_busy',
}


def _registry():
    result = {'types.SimpleNamespace': types.SimpleNamespace}
    for module_name, module in list(sys.modules.items()):
        if not module_name.startswith('game.') or module is None:
            continue
        for name, value in vars(module).items():
            if isinstance(value, type) and value.__module__ == module_name:
                result[module_name + '.' + name] = value
    return result


def encode_game(game):
    registry = _registry()
    nodes, identities = [], {}

    def encode(value):
        if value is game:
            return {'game': True}
        if value is current_game_time:
            return {'clock': True}
        if isinstance(value, enum.Enum):
            return {'enum': type(value).__module__ + '.' + type(value).__name__, 'name': value.name}
        if value is None or type(value) in (bool, str, int, float):
            return value
        if id(value) in identities:
            return {'ref': identities[id(value)]}
        index = len(nodes)
        identities[id(value)] = index
        node = {}
        nodes.append(node)
        if isinstance(value, dict):
            node.update(kind='dict', items=[[encode(k), encode(v)] for k, v in value.items()])
        elif isinstance(value, (list, tuple, set, frozenset, collections.deque)):
            node.update(kind=type(value).__name__, items=[encode(v) for v in value])
            if isinstance(value, collections.deque):
                node['maxlen'] = value.maxlen
        else:
            class_name = type(value).__module__ + '.' + type(value).__name__
            if class_name not in registry:
                raise ValueError('Unsupported career data: ' + class_name)
            node.update(kind='object', cls=class_name, attrs={k: encode(v) for k, v in vars(value).items()})
        return {'ref': index}

    roots = {k: encode(v) for k, v in vars(game).items()
             if k not in EXCLUDED and not k.endswith('_menu_state')}
    return {'schema': 1, 'roots': roots, 'nodes': nodes}


def decode_game(archive, game):
    if archive.get('schema') != 1:
        raise ValueError('Unsupported career archive version')
    nodes = archive['nodes']
    if not isinstance(nodes, list) or len(nodes) > 250000:
        raise ValueError('Invalid career archive')
    registry, cache, filling = _registry(), {}, set()
    for i, node in enumerate(nodes):
        kind = node['kind']
        if kind == 'object':
            cls = registry.get(node['cls'])
            if cls is None or issubclass(cls, enum.Enum):
                raise ValueError('Unknown career data class')
            cache[i] = types.SimpleNamespace() if cls is types.SimpleNamespace else object.__new__(cls)
        elif kind == 'dict': cache[i] = {}
        elif kind == 'list': cache[i] = []
        elif kind == 'set': cache[i] = set()
        elif kind == 'deque': cache[i] = collections.deque(maxlen=node.get('maxlen'))
        elif kind not in ('tuple', 'frozenset'): raise ValueError('Unknown archive node')

    def decode(value):
        if not isinstance(value, dict): return value
        if value.get('game'): return game
        if value.get('clock'): return current_game_time
        if 'enum' in value:
            cls = registry.get(value['enum'])
            if cls is None or not issubclass(cls, enum.Enum): raise ValueError('Unknown enumeration')
            return cls[value['name']]
        i = value['ref']
        if type(i) is not int or not 0 <= i < len(nodes): raise ValueError('Invalid archive reference')
        node = nodes[i]
        if i in filling: return cache[i]
        filling.add(i)
        kind = node['kind']
        if kind in ('tuple', 'frozenset'):
            factory = tuple if kind == 'tuple' else frozenset
            cache[i] = factory(decode(v) for v in node['items'])
        elif kind == 'dict': cache[i].update((decode(k), decode(v)) for k, v in node['items'])
        elif kind == 'object':
            for k, v in node['attrs'].items():
                if k.startswith('__'): raise ValueError('Invalid object attribute')
                object.__setattr__(cache[i], k, decode(v))
        elif kind == 'set': cache[i].update(decode(v) for v in node['items'])
        else: cache[i].extend(decode(v) for v in node['items'])
        return cache[i]

    roots = {k: decode(v) for k, v in archive['roots'].items() if k not in EXCLUDED}
    from game.player import Player
    if not isinstance(roots.get('player'), Player) or not isinstance(roots.get('WORLD_MAP'), dict):
        raise ValueError('Save does not contain a complete career')
    return roots
