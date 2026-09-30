# Lecture des Blueprints du prototype

Carte de demonstration : `/Game/ThirdPerson/Lvl_ThirdPerson`.

## Parcours

Approche du gardien (600 unites) -> reveil -> combat -> mort du gardien -> apparition de Khaimera apres 5 secondes -> trois phases -> victoire ou mort joueur.

## Ou modifier quoi

| Blueprint | Responsabilite | Point d'entree |
|---|---|---|
| BP_DarkKnight_Alert | Inputs, camera, lock, creation HUD | InputActions, Tick |
| BPC_Combat | Combo, buffer, esquive, trace melee | RequestAttack, Dodge, CancelCombat |
| BPC_Stat | PV, endurance, hit-react, stagger du finisher, mort, arbitrage du mouvement | ApplyDamage, ForceFinisherStagger, RefreshMovement |
| BP_Enemy | Gardien dormant et succession du boss | Awaken, SpawnBossNow |
| BP_Boss | Seuils de phases et presentation des armes | AnyDamage, BeginPhaseTransition, ReleaseAxes |
| BP_Boss : Attack01 | Choix melee / feu / attente pendant transition | Fonction interface Attack01 |
| BP_AI_Enemy | Detection et cible du blackboard | OnSeePawn, AcquirePlayerTarget |
| BT_Enemy | Poursuite -> attaque -> repositionnement | Task_ChaseTarget, Task_Attack, Task_Strafe |
| BP_Fireball | Projectile de feu et collision | BeginPlay, ActorBeginOverlap |
| AN_ReleaseFireball | Depart du projectile au bon instant du montage | Received_Notify |
| WBP_HUD | Barres, consignes, annonces et resultat | UpdateBars |

Les graphes principaux sont disposes en blocs commentes, sur deux colonnes. Chaque bloc se lit de gauche a droite. Certains getters partages gardent des fils entre blocs : leur presence ne represente pas un enchainement d'execution. Le fil blanc indique l'ordre.

## Phases de Khaimera

- P1 : au-dessus de 60 % ; melee avec haches.
- P2 : entre 60 et 30 % ; hurlement protege 2,5 s, haches physiques au sol, incantations de feu (notify a 0,55 s), approche a 650 unites.
- P3 : sous 30 % ; hurlement, haches restaurees, melee acceleree, sans strafe intermediaire.

Les transitions et incantations verrouillent le mouvement via BPC_Stat.RefreshMovement. Ne pas sauvegarder une vitesse temporairement nulle comme vitesse de reference. Les haches sont masquees par leurs bones weapon_l/weapon_r ; ne pas changer de mesh ou d'AnimClass au BeginPlay.

## Recompense du combo et camera

Le troisieme coup du combo ne recompense le joueur que si la trace touche effectivement un Actor possedant un BPC_Stat (ou une sous-classe). BPC_Combat appelle alors ForceFinisherStagger : montage HitReact compatible, vitesse nulle et ouverture de 1,15 seconde. Un coup dans le vide ne declenche rien, et une cible morte ignore le stagger.

Lors de chaque pression d'attaque, BP_DarkKnight_Alert transmet `LockedTarget` a `BPC_Combat.AttackTarget`. `FaceAttackTarget` realigne le personnage et son controleur au debut de chaque etape, puis une seconde fois juste avant `DoAttackTrace`. L'assistance ne s'active que sur une cible valide a moins de 650 unites ; elle ne magnetise donc pas une attaque libre vers un ennemi hors lock.

Chaque degat confirme appelle `BPC_Stat.PlayDamageCameraFeedback`. Le Camera Shake du pack Variant Combat est joue a l'echelle0,75 lorsque le joueur est touche et0,45 lorsqu'un ennemi est touche. Ces shakes ne modifient que la position de camera (duree0,35s/0,25s), pas la rotation ni la logique de lock.

Le Spring Arm du BP_ThirdPersonCharacter porte le cadrage epaule reutilise par BP_DarkKnight_Alert : longueur 330, SocketOffset Y=68/Z=48, CameraLagSpeed=7 et FOV=82. Le lock conserve sa logique de rotation existante ; ne recentrer le SocketOffset que si un futur mode de visee l'exige explicitement.

## Ressources de presentation

`/Game/Enemies/Khaimera/Montages/AM_Khaimera_FireCast` et `AM_Khaimera_PhaseChange` reutilisent Cast et Emote_Taunt_Howl_T1 du pack Khaimera. Les haches sous `/Game/Enemies/Khaimera/Props` proviennent de sa geometrie originale. Le projectile reutilise NS_Magma_Shot_Projectile du pack Mixed_Magic_VFX_Pack.

## Maintenance

Les scripts de migration ponctuels ne sont pas des scripts de lancement du jeu : ne pas les relancer. Les assets sauvegardes contiennent le gameplay. Les fichiers Saved/BlueprintReadability_20260930 conservent les graphes avant rangement et les comparaisons de connexions. Les tests automatiques ne remplacent pas la validation humaine du ressenti et de la presentation.
