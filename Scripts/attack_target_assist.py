"""One-time migration: locked target facing at each combo step and impact trace."""
import json
from pathlib import Path
import unreal

ROOT = '/Game/Characters/Dark_Knight/Dark_Knight_Male/Blueprints/'
COMBAT = ROOT + 'BPC_Combat'
PLAYER = ROOT + 'BP_DarkKnight_Alert'
GRAPH = 'EventGraph'
SERVICE = unreal.BlueprintService
OUT = Path(unreal.Paths.project_saved_dir()) / 'AttackAssistBackup_20260930'
MAP = OUT / 'nodes.json'

assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
assert not MAP.exists(), 'Migration already applied.'
OUT.mkdir(parents=True, exist_ok=True)

def save(path):
    assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(path)), path
    assert unreal.EditorAssetLibrary.save_asset(path), path

def unique(path, prefix):
    matches = [n.node_id for n in SERVICE.get_nodes_in_graph(path, GRAPH, 0, '', False)
               if n.node_id.startswith(prefix)]
    assert len(matches) == 1, (path, prefix, matches)
    return matches[0]

def output_target(path, node_id, pin='then'):
    d = SERVICE.get_node_details(path, GRAPH, node_id)
    p = next(x for x in d.output_pins if x.pin_name == pin)
    assert len(p.connections) == 1, (node_id, pin, list(p.connections))
    return str(p.connections[0]).split(':')

class Graph:
    def __init__(self, path):
        self.path = path; self.nodes = []; self.edges = []; self.defaults = []
    def node(self, ref, kind, **params):
        self.nodes.append({'ref': ref, 'type': kind, 'params': params}); return ref
    def fn(self, ref, cls, method): return self.node(ref, 'function_call', **{'class': cls, 'function': method})
    def get(self, ref, var): return self.node(ref, 'variable_get', variable=var)
    def mset(self, ref, cls, var): return self.node(ref, 'member_set', **{'class': cls, 'member': var})
    def event(self, ref, name): return self.node(ref, 'custom_event', name=name)
    def branch(self, ref): return self.node(ref, 'branch')
    def cast(self, ref, cls): return self.node(ref, 'cast', target_class=cls)
    def edge(self, source, target): self.edges.append({'from_': source, 'to': target})
    def default(self, ref, pin, value): self.defaults.append({'node_ref': ref, 'pin_name': pin, 'value': str(value).lower() if isinstance(value, bool) else str(value)})
    def run(self):
        result = SERVICE.build_graph(self.path, GRAPH, self.nodes, self.edges, self.defaults, False, False)
        print('BUILD', self.path, result.success, list(result.errors), list(result.warnings))
        assert result.success and not result.errors and not result.warnings
        return dict(result.ref_to_node_id)

assert SERVICE.add_member_variable(COMBAT, 'AttackTarget', 'Actor', '')
assert SERVICE.add_member_variable(COMBAT, 'AttackAssistRange', 'float', '650.0')

# Compile the event signature first so it is callable in the following graph build.
event_result = SERVICE.build_graph(COMBAT, GRAPH,
    [{'ref': 'FaceEvent', 'type': 'custom_event', 'params': {'name': 'FaceAttackTarget'}}], [], [], False, False)
assert event_result.success and not event_result.errors and not event_result.warnings
face_event = dict(event_result.ref_to_node_id)['FaceEvent']
save(COMBAT)

g = Graph(COMBAT)
g.fn('Owner', 'ActorComponent', 'GetOwner')
g.cast('Character', 'Character')
g.edge('Owner.ReturnValue', 'Character.Object')
g.get('Target', 'AttackTarget')
g.fn('Valid', 'KismetSystemLibrary', 'IsValid')
g.edge('Target.AttackTarget', 'Valid.Object')
g.branch('HasTarget')
g.edge(face_event + '.then', 'HasTarget.execute')
g.edge('Valid.ReturnValue', 'HasTarget.Condition')
g.fn('Distance', 'Actor', 'GetDistanceTo')
g.edge('Character.AsCharacter', 'Distance.self')
g.edge('Target.AttackTarget', 'Distance.OtherActor')
g.get('Range', 'AttackAssistRange')
g.node('InRange', 'comparison', operation='LessEqual', operand_type='Float')
g.edge('Distance.ReturnValue', 'InRange.A')
g.edge('Range.AttackAssistRange', 'InRange.B')
g.branch('RangeGate')
g.edge('HasTarget.then', 'Character.execute')
g.edge('Character.then', 'RangeGate.execute')
g.edge('InRange.ReturnValue', 'RangeGate.Condition')
g.fn('OwnerLocation', 'Actor', 'K2_GetActorLocation')
g.edge('Character.AsCharacter', 'OwnerLocation.self')
g.fn('TargetLocation', 'Actor', 'K2_GetActorLocation')
g.edge('Target.AttackTarget', 'TargetLocation.self')
g.fn('LookAt', 'KismetMathLibrary', 'FindLookAtRotation')
g.edge('OwnerLocation.ReturnValue', 'LookAt.Start')
g.edge('TargetLocation.ReturnValue', 'LookAt.Target')
g.fn('Break', 'KismetMathLibrary', 'BreakRotator')
g.edge('LookAt.ReturnValue', 'Break.InRot')
g.fn('Make', 'KismetMathLibrary', 'MakeRotator')
g.edge('Break.Yaw', 'Make.Yaw')
g.default('Make', 'Pitch', 0.0); g.default('Make', 'Roll', 0.0)
g.fn('RotateActor', 'Actor', 'K2_SetActorRotation')
g.edge('RangeGate.then', 'RotateActor.execute')
g.edge('Character.AsCharacter', 'RotateActor.self')
g.edge('Make.ReturnValue', 'RotateActor.NewRotation')
g.default('RotateActor', 'bTeleportPhysics', False)
g.fn('Controller', 'Pawn', 'GetController')
g.edge('Character.AsCharacter', 'Controller.self')
g.fn('RotateController', 'Controller', 'SetControlRotation')
g.edge('RotateActor.then', 'RotateController.execute')
g.edge('Controller.ReturnValue', 'RotateController.self')
g.edge('Make.ReturnValue', 'RotateController.NewRotation')
face_nodes = g.run()
save(COMBAT)

# Call target-facing immediately before every combo step and every trace notify.
play_step = unique(COMBAT, '6BEF1644')
trace_event = unique(COMBAT, '3D7C8CBE')
play_next, play_pin = output_target(COMBAT, play_step)
trace_next, trace_pin = output_target(COMBAT, trace_event)
assert SERVICE.disconnect_pin(COMBAT, GRAPH, play_step, 'then')
assert SERVICE.disconnect_pin(COMBAT, GRAPH, trace_event, 'then')
g = Graph(COMBAT)
g.fn('FaceStep', 'BPC_Combat_C', 'FaceAttackTarget')
g.fn('FaceTrace', 'BPC_Combat_C', 'FaceAttackTarget')
g.edge(play_step + '.then', 'FaceStep.execute')
g.edge('FaceStep.then', play_next + '.' + play_pin)
g.edge(trace_event + '.then', 'FaceTrace.execute')
g.edge('FaceTrace.then', trace_next + '.' + trace_pin)
call_nodes = g.run()
save(COMBAT)

# Refresh the target reference on every attack press. LockedTarget is cleared by unlock/death.
attack_gate = unique(PLAYER, 'B5CEF447')
request = unique(PLAYER, '660FE2E6')
assert SERVICE.disconnect_pin(PLAYER, GRAPH, attack_gate, 'else')
g = Graph(PLAYER)
g.mset('SetTarget', 'BPC_Combat_C', 'AttackTarget')
g.edge(attack_gate + '.else', 'SetTarget.execute')
g.edge(unique(PLAYER, '3938A55A') + '.CombatComponent', 'SetTarget.self')
g.edge(unique(PLAYER, 'D3E5DBF0') + '.LockedTarget', 'SetTarget.AttackTarget')
g.edge('SetTarget.then', request + '.execute')
player_nodes = g.run()
save(PLAYER)

MAP.write_text(json.dumps({'event': face_event, 'face': face_nodes, 'calls': call_nodes,
                           'player': player_nodes, 'range': 650.0}, indent=2), encoding='utf-8')
print('ATTACK_TARGET_ASSIST_APPLIED')
