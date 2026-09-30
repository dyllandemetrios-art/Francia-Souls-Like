"""One-time migration: reuse Variant Combat camera shakes on every confirmed damage event."""
import json
from pathlib import Path
import unreal

STAT = '/Game/Characters/Dark_Knight/Dark_Knight_Male/Blueprints/BPC_Stat'
GRAPH = 'EventGraph'
SERVICE = unreal.BlueprintService
OUT = Path(unreal.Paths.project_saved_dir()) / 'DamageFeedbackBackup_20260930'
MAP = OUT / 'nodes.json'
assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
assert not MAP.exists(), 'Migration already applied.'
OUT.mkdir(parents=True, exist_ok=True)

def save():
    assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(STAT))
    assert unreal.EditorAssetLibrary.save_asset(STAT)

for name, asset in [
    ('PlayerHitCameraShakeClass', '/Game/Variant_Combat/Blueprints/BP_CameraShake_Hit_Player.BP_CameraShake_Hit_Player_C'),
    ('EnemyHitCameraShakeClass', '/Game/Variant_Combat/Blueprints/BP_CameraShake_Hit_Enemy.BP_CameraShake_Hit_Enemy_C')]:
    assert SERVICE.add_member_variable(STAT, name, 'TSubclassOf<CameraShakeBase>', '')
    assert SERVICE.set_variable_default_value(STAT, name, asset)

event_result = SERVICE.build_graph(STAT, GRAPH,
    [{'ref': 'FeedbackEvent', 'type': 'custom_event', 'params': {'name': 'PlayDamageCameraFeedback'}}],
    [], [], False, False)
assert event_result.success and not event_result.errors and not event_result.warnings
event_id = dict(event_result.ref_to_node_id)['FeedbackEvent']
save()

nodes = [
    {'ref':'Owner','type':'function_call','params':{'class':'ActorComponent','function':'GetOwner'}},
    {'ref':'Player','type':'function_call','params':{'class':'GameplayStatics','function':'GetPlayerCharacter'}},
    {'ref':'IsPlayer','type':'comparison','params':{'operation':'Equal','operand_type':'Object'}},
    {'ref':'Gate','type':'branch','params':{}},
    {'ref':'Manager','type':'function_call','params':{'class':'GameplayStatics','function':'GetPlayerCameraManager'}},
    {'ref':'PlayerClass','type':'variable_get','params':{'variable':'PlayerHitCameraShakeClass'}},
    {'ref':'EnemyClass','type':'variable_get','params':{'variable':'EnemyHitCameraShakeClass'}},
    {'ref':'PlayerShake','type':'function_call','params':{'class':'PlayerCameraManager','function':'StartCameraShake'}},
    {'ref':'EnemyShake','type':'function_call','params':{'class':'PlayerCameraManager','function':'StartCameraShake'}},
]
edges = [
    {'from_':'Owner.ReturnValue','to':'IsPlayer.A'}, {'from_':'Player.ReturnValue','to':'IsPlayer.B'},
    {'from_':event_id+'.then','to':'Gate.execute'}, {'from_':'IsPlayer.ReturnValue','to':'Gate.Condition'},
    {'from_':'Gate.then','to':'PlayerShake.execute'}, {'from_':'Gate.else','to':'EnemyShake.execute'},
    {'from_':'Manager.ReturnValue','to':'PlayerShake.self'}, {'from_':'Manager.ReturnValue','to':'EnemyShake.self'},
    {'from_':'PlayerClass.PlayerHitCameraShakeClass','to':'PlayerShake.ShakeClass'},
    {'from_':'EnemyClass.EnemyHitCameraShakeClass','to':'EnemyShake.ShakeClass'},
]
defaults = [
    {'node_ref':'Player','pin_name':'PlayerIndex','value':'0'},
    {'node_ref':'Manager','pin_name':'PlayerIndex','value':'0'},
    {'node_ref':'PlayerShake','pin_name':'Scale','value':'0.75'},
    {'node_ref':'EnemyShake','pin_name':'Scale','value':'0.45'},
]
body = SERVICE.build_graph(STAT, GRAPH, nodes, edges, defaults, False, False)
print('FEEDBACK_BODY', body.success, list(body.errors), list(body.warnings))
assert body.success and not body.errors and not body.warnings
save()

set_health = next(n.node_id for n in SERVICE.get_nodes_in_graph(STAT, GRAPH, 0, '', False)
                  if n.node_id.startswith('B37731F9'))
d = SERVICE.get_node_details(STAT, GRAPH, set_health)
then = next(p for p in d.output_pins if p.pin_name == 'then')
assert len(then.connections) == 1
next_id, next_pin = str(then.connections[0]).split(':')
assert SERVICE.disconnect_pin(STAT, GRAPH, set_health, 'then')
call_result = SERVICE.build_graph(STAT, GRAPH,
    [{'ref':'FeedbackCall','type':'function_call','params':{'class':'BPC_Stat_C','function':'PlayDamageCameraFeedback'}}],
    [{'from_':set_health+'.then','to':'FeedbackCall.execute'}, {'from_':'FeedbackCall.then','to':next_id+'.'+next_pin}],
    [], False, False)
print('FEEDBACK_CALL', call_result.success, list(call_result.errors), list(call_result.warnings))
assert call_result.success and not call_result.errors and not call_result.warnings
save()

MAP.write_text(json.dumps({'event':event_id,'body':dict(body.ref_to_node_id),
                           'call':dict(call_result.ref_to_node_id)},indent=2),encoding='utf-8')
print('DAMAGE_CAMERA_FEEDBACK_APPLIED')
