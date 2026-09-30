"""Finish the partially-created combat polish graph after UE rejected a class pin default."""
import json
from pathlib import Path
import unreal

SERVICE = unreal.BlueprintService
ROOT = '/Game/Characters/Dark_Knight/Dark_Knight_Male/Blueprints/'
COMBAT = ROOT + 'BPC_Combat'
STAT = ROOT + 'BPC_Stat'
PLAYER_PARENT = '/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
GRAPH = 'EventGraph'
OUT = Path(unreal.Paths.project_saved_dir()) / 'CombatPolishBackup_20260930'

assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
assert not (OUT / 'nodes.json').exists(), 'Repair already applied.'

def unique(title):
    matches = [n.node_id for n in SERVICE.get_nodes_in_graph(COMBAT, GRAPH, 0, '', False)
               if n.node_title.split('\n')[0] == title]
    # The nodes created by the failed build are the only Find Component by Class and
    # Equal (Integer) nodes in this small inserted island at this point.
    return matches

find_candidates = unique('Get Component by Class')
if not find_candidates:
    find_candidates = unique('GetComponentByClass')
assert find_candidates, 'Inserted FindStat node missing.'
find_stat = find_candidates[-1]

result = SERVICE.build_graph(
    COMBAT, GRAPH,
    [{'ref': 'StatClass', 'type': 'variable_get', 'params': {'variable': 'StatComponentClass'}}],
    [{'from_': 'StatClass.StatComponentClass', 'to': find_stat + '.ComponentClass'}],
    [], False, False)
print('REPAIR_BUILD', result.success, list(result.errors), list(result.warnings))
assert result.success and not result.errors and not result.warnings

assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(STAT))
assert unreal.EditorAssetLibrary.save_asset(STAT)
assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(COMBAT))
assert unreal.EditorAssetLibrary.save_asset(COMBAT)

assert SERVICE.set_component_property(PLAYER_PARENT, 'CameraBoom', 'TargetArmLength', '330.0')
assert SERVICE.set_component_property(PLAYER_PARENT, 'CameraBoom', 'SocketOffset', '(X=0.0,Y=68.0,Z=48.0)')
assert SERVICE.set_component_property(PLAYER_PARENT, 'CameraBoom', 'CameraLagSpeed', '7.0')
assert SERVICE.set_component_property(PLAYER_PARENT, 'FollowCamera', 'FieldOfView', '82.0')
assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(PLAYER_PARENT))
assert unreal.EditorAssetLibrary.save_asset(PLAYER_PARENT)

(OUT / 'nodes.json').write_text(json.dumps({
    'stat_event': 'ForceFinisherStagger',
    'combat_find_stat': find_stat,
    'combat_stat_class': dict(result.ref_to_node_id).get('StatClass'),
    'camera': {'arm': 330.0, 'socket': [0.0, 68.0, 48.0], 'lag': 7.0, 'fov': 82.0},
}, indent=2), encoding='utf-8')
print('COMBAT_POLISH_REPAIRED')
