"""One-time combat polish: third confirmed combo hit staggers, shoulder camera.

Run once with PIE stopped. Backup lives in Saved/CombatPolishBackup_20260930.
"""
import json
from pathlib import Path
import unreal

ROOT = '/Game/Characters/Dark_Knight/Dark_Knight_Male/Blueprints/'
COMBAT = ROOT + 'BPC_Combat'
STAT = ROOT + 'BPC_Stat'
PLAYER_PARENT = '/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
SERVICE = unreal.BlueprintService
GRAPH = 'EventGraph'
OUT = Path(unreal.Paths.project_saved_dir()) / 'CombatPolishBackup_20260930'
MAP = OUT / 'nodes.json'

assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
assert not MAP.exists(), 'Migration already applied; do not run it twice.'

# Reuse the graph builder without executing its historical stages.
namespace = {'stage': '__combat_polish_helpers_only__'}
helper = Path(unreal.Paths.project_dir()) / 'Scripts' / 'refine_combat_flow.py'
exec(helper.read_text(encoding='utf-8'), namespace)
Graph = namespace['Graph']
save = namespace['save']

def node(prefix, path):
    matches = [n.node_id for n in SERVICE.get_nodes_in_graph(path, GRAPH, 0, '', False)
               if n.node_id.startswith(prefix)]
    assert len(matches) == 1, (path, prefix, matches)
    return matches[0]

OUT.mkdir(parents=True, exist_ok=True)

# The normal damage flow already plays each enemy's compatible HitReact montage.
# This event extends that same reaction and movement lock for the finisher.
g = Graph(STAT, 'finisher_stagger_event')
g.event('Event', 'ForceFinisherStagger')
g.get('Dead', 'bIsDead')
g.branch('Alive')
g.e('Event.then', 'Alive.execute')
g.e('Dead.bIsDead', 'Alive.Condition')
g.set('Stunned', 'bIsHitStunned', True)
g.e('Alive.else', 'Stunned.execute')
g.fn('Refresh', 'BPC_Stat_C', 'RefreshMovement')
g.e('Stunned.then', 'Refresh.execute')
g.get('Montage', 'HitReactMontage')
g.fn('Owner', 'ActorComponent', 'GetOwner')
g.cast('Character', 'Character')
g.e('Owner.ReturnValue', 'Character.Object')
g.fn('Play', 'Character', 'PlayAnimMontage')
g.e('Refresh.then', 'Character.execute')
g.e('Character.then', 'Play.execute')
g.e('Character.AsCharacter', 'Play.self')
g.e('Montage.HitReactMontage', 'Play.AnimMontage')
g.d('Play', 'InPlayRate', 0.72)
g.node('Self', 'spawner_key', key='NODE K2Node_Self')
g.fn('Timer', 'KismetSystemLibrary', 'K2_SetTimer')
g.e('Play.then', 'Timer.execute')
g.e('Self.self', 'Timer.Object')
g.d('Timer', 'FunctionName', 'OnHitStunEnd')
g.d('Timer', 'Time', 1.15)
g.d('Timer', 'bLooping', False)
stat_nodes = g.run()
save(STAT)

# Insert the finisher check after confirmed damage. Missing/cast-failed stat components
# fall through to the existing hit-stop, so this remains generic and safe.
apply_damage = node('205ED30D', COMBAT)
time_dilation = node('A394BB3F', COMBAT)
assert SERVICE.disconnect_pin(COMBAT, GRAPH, apply_damage, 'then')
g = Graph(COMBAT, 'third_hit_stagger')
g.get('Combo', 'ComboIndex')
g.node('IsThird', 'comparison', operation='Equal', operand_type='Int')
g.e('Combo.ComboIndex', 'IsThird.A')
g.d('IsThird', 'B', 2)
g.branch('ThirdGate')
g.e(apply_damage + '.then', 'ThirdGate.execute')
g.e('IsThird.ReturnValue', 'ThirdGate.Condition')
g.fn('FindStat', 'Actor', 'GetComponentByClass')
g.e(node('74806C25', COMBAT) + '.HitActor', 'FindStat.self')
g.get('StatClass', 'StatComponentClass')
g.e('StatClass.StatComponentClass', 'FindStat.ComponentClass')
g.cast('Stat', 'BPC_Stat_C')
g.e('ThirdGate.then', 'Stat.execute')
g.e('FindStat.ReturnValue', 'Stat.Object')
g.fn('Stagger', 'BPC_Stat_C', 'ForceFinisherStagger')
g.e('Stat.then', 'Stagger.execute')
g.e('Stat.AsBPC Stat', 'Stagger.self')
g.e('Stagger.then', time_dilation + '.execute')
g.e('Stat.CastFailed', time_dilation + '.execute')
g.e('ThirdGate.else', time_dilation + '.execute')
combat_nodes = g.run()
save(COMBAT)

# Shoulder framing. Camera stays attached to the same control-rotation spring arm,
# so target lock keeps its existing rotation logic.
assert SERVICE.set_component_property(PLAYER_PARENT, 'CameraBoom', 'TargetArmLength', '330.0')
assert SERVICE.set_component_property(PLAYER_PARENT, 'CameraBoom', 'SocketOffset', '(X=0.0,Y=68.0,Z=48.0)')
assert SERVICE.set_component_property(PLAYER_PARENT, 'CameraBoom', 'CameraLagSpeed', '7.0')
assert SERVICE.set_component_property(PLAYER_PARENT, 'FollowCamera', 'FieldOfView', '82.0')
save(PLAYER_PARENT)

MAP.write_text(json.dumps({
    'stat': stat_nodes,
    'combat': combat_nodes,
    'camera': {'arm': 330.0, 'socket': [0.0, 68.0, 48.0], 'lag': 7.0, 'fov': 82.0},
}, indent=2), encoding='utf-8')
print('COMBAT_POLISH_APPLIED')
