"""Conservative graph maintenance: prune unreachable non-event nodes, arrange event blocks, annotate.
Every live pin connection is compared before/after. No gameplay rewiring is performed.
"""
import unreal,json
from pathlib import Path
from collections import defaultdict,deque
S=unreal.BlueprintService
OUT=Path(unreal.Paths.project_saved_dir())/'BlueprintReadability_20260930'
OUT.mkdir(exist_ok=True)
assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
NOTES={
'BeginPlay':'Initialisation : references, configuration et timers',
'AnyDamage':'Degats entrants : sante, reactions, mort et changement de phase',
'BeginPhaseTransition':'Transition protegee : immobilisation, animation, puis changement des armes',
'ReleaseAxes':'Phase 2 : laisser tomber les haches / Phase 3 : reprendre les haches',
'FinishPhaseTransition':'Fin de transition : rendre le boss vulnerable et liberer le mouvement',
'BeginFireCast':'Incantation : immobiliser, jouer le montage ; le notify libere le projectile',
'LaunchFireball':'Projectile : verifier le montage actif, viser le joueur, apparaitre a la main',
'FinishFireCast':'Fin de cast : liberer le mouvement sans interrompre une transition',
'ClearPhaseAnnouncement':'Effacer le message temporaire de changement de phase',
'RequestAttack':'Demande attaque : verifier les etats, bufferiser ou engager un coup',
'Dodge':'Esquive : accepter ou bufferiser ; endurance depensee seulement au lancement',
'CancelCombat':'Interruption : vider les buffers, arreter les timers, liberer le mouvement',
'RefreshMovement':'Arbitre du mouvement : mort, hit-stun et attaque bloquent la vitesse de base',
'ApplyDamage':'Sante : ignorer les morts, appliquer les degats, jouer hit-react ou mort',
'DoAttackTrace':'Impact de melee : trace, filtrage et application des degats',
'ForceFinisherStagger':'Recompense du combo : le troisieme impact ouvre une longue fenetre de riposte',
'FaceAttackTarget':'Assistance melee : realigner chaque etape et chaque impact sur la cible verrouillee',
'PlayDamageCameraFeedback':'Impact confirme : secousse differente selon joueur touche ou ennemi touche',
'Awaken':'Reveil du gardien : animation avant activation de son IA',
'OnAwakenFinished':'Fin du reveil : creer le controleur IA',
'SpawnBossNow':'Succession : apparaitre face au joueur, puis retirer le gardien',
'UpdateBars':'HUD : actualiser les barres et le texte de la rencontre',
'AcquirePlayerTarget':'Aggro explicite : cibler le joueur apres une attaque recue',
'Attack01':'Choix attaque : transition / magie en phase 2 / melee en phases 1 et 3',
'Received_Notify':'Notify de cast : transmettre au boss la liberation du projectile',
'ActorBeginOverlap':'Collision projectile : ignorer le lanceur, blesser le joueur, detruire',
'Tick':'Mise a jour : acquisition, verrouillage ou surveillance de proximite',
}
def snapshot(path,graph):
    result={}
    for n in S.get_nodes_in_graph(path,graph,0,'',False):
        d=S.get_node_details(path,graph,n.node_id)
        result[n.node_id]={'title':n.node_title,'type':n.node_type,'x':n.pos_x,'y':n.pos_y,'pure':d.is_pure,
            'in':[(p.pin_name,p.pin_category,list(p.connections)) for p in d.input_pins],
            'out':[(p.pin_name,p.pin_category,list(p.connections)) for p in d.output_pins]}
    return result
def metrics(path,graph):
    report,err=S.analyze_graph_layout(path,graph)
    assert not err,err
    return json.loads(report)
def arrange(path,graph):
    key=path.replace('/','_')+'__'+graph
    before=snapshot(path,graph)
    if len(before)<3:return
    (OUT/(key+'_before.json')).write_text(json.dumps(before,indent=2),encoding='utf-8')
    original_metrics=metrics(path,graph)
    comments={i for i,n in before.items() if 'Comment' in n['type']}
    data={i:n for i,n in before.items() if i not in comments}
    roots={i for i,n in data.items() if any(t in n['type'] for t in ['Event','InputAction','FunctionEntry','FunctionResult','Tunnel'])}
    if not roots:return
    successors={i:{v.split(':')[0] for _,cat,links in n['out'] if cat=='exec' for v in links if v.split(':')[0] in data} for i,n in data.items()}
    live=set(roots);queue=list(roots)
    while queue:
        i=queue.pop()
        for j in successors[i]:
            if j not in live:live.add(j);queue.append(j)
    # Preserve all data dependencies, including impure producers referenced by downstream code.
    queue=list(live)
    while queue:
        i=queue.pop()
        for _,cat,links in data[i]['in']:
            if cat=='exec':continue
            for link in links:
                j=link.split(':')[0]
                if j in data and j not in live:live.add(j);queue.append(j)
    dead=set(data)-live
    # A disconnected graph might be a deliberate utility: only maintain graphs with exec roots.
    for i in dead|comments:assert S.delete_node(path,graph,i),(path,graph,i)
    # Group execution islands. Shared data producers belong to the first consuming block.
    adjacency={i:set() for i in live if not data[i]['pure']}
    for i in adjacency:
        for j in successors[i]:
            if j in adjacency:adjacency[i].add(j);adjacency[j].add(i)
    groups=[];remaining=set(adjacency)
    while remaining:
        first=min(remaining,key=lambda i:(data[i]['y'],data[i]['x']))
        group={first};queue=[first];remaining.remove(first)
        while queue:
            for j in adjacency[queue.pop()]&remaining:remaining.remove(j);group.add(j);queue.append(j)
        groups.append(group)
    def group_title(group):
        titles=[data[i]['title'].split('\n')[0].strip().replace('Event ','') for i in group&roots]
        return ' / '.join(sorted(titles)) or 'Traitement partage'
    groups.sort(key=lambda g:(0 if 'BeginPlay' in group_title(g) or 'Construct' in group_title(g) else 1,group_title(g)))
    assigned=set().union(*groups) if groups else set()
    for group in groups:
        queue=list(group)
        while queue:
            i=queue.pop()
            for _,cat,links in data[i]['in']:
                if cat=='exec':continue
                for link in links:
                    j=link.split(':')[0]
                    if j in live and j not in assigned:assigned.add(j);group.add(j);queue.append(j)
    orphan=live-assigned
    if orphan:groups.append(orphan)
    geometry=[]
    for group in groups:
        err=S.auto_layout_selected_nodes(path,graph,list(group))
        assert not err,err
        report=metrics(path,graph)
        boxes=[n for n in report['nodes'] if n['id'] in group]
        x=min(n['x'] for n in boxes);y=min(n['y'] for n in boxes)
        width=max(n['x']+n['width'] for n in boxes)-x;height=max(n['y']+n['height'] for n in boxes)-y
        geometry.append((group,boxes,x,y,width,height))
    # Blocks in two columns; each row leaves room for its tallest block and comment header.
    col_width=max(v[4] for v in geometry)+450;row_y=150
    for start in range(0,len(geometry),2):
        row=geometry[start:start+2]
        for col,(group,boxes,x,y,width,height) in enumerate(row):
            for n in boxes:assert S.set_node_position(path,graph,n['id'],n['x']-x+col*col_width,n['y']-y+row_y)
            title=group_title(group)
            desc=next((v for k,v in NOTES.items() if k in title),'Flux autonome : lire de gauche a droite ; valeurs partagees via les variables')
            color=(.65,.25,.12) if any(k in title for k in ['Damage','Death','Fire','Axes','Phase']) else (.12,.32,.48)
            assert S.add_comment_around_nodes(path,graph,title+'\n'+desc,list(group),70,*color,.35)
        row_y+=max(v[5] for v in row)+340
    after=snapshot(path,graph)
    for i in live:
        assert i in after
        # Exact preservation of all active data and execution edges.
        for direction in ['in','out']:
            expected=[(name,cat,sorted(v for v in links if v.split(':')[0] in live)) for name,cat,links in before[i][direction]]
            actual=[(name,cat,sorted(links)) for name,cat,links in after[i][direction]]
            assert expected==actual,(path,graph,i,direction)
    final=metrics(path,graph)
    result={'path':path,'graph':graph,'removed':len(dead),'blocks':len(groups),'before':{k:original_metrics[k] for k in ['nodeCount','nodeOverlaps','backwardExecWires','wireCrossings']},'after':{k:final[k] for k in ['nodeCount','nodeOverlaps','backwardExecWires','wireCrossings']},'active_connections_preserved':True}
    (OUT/(key+'_result.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
    assert final['nodeOverlaps']==0,result
    assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(path)),path
    assert unreal.EditorAssetLibrary.save_asset(path),path
