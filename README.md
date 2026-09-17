# Francia Souls-Like

Projet personnel d'apprentissage : construire un jeu d'action à la troisième personne façon *souls-like* dans **Unreal Engine 5.8**, en partant d'un tutoriel complet et en testant, en parallèle, une partie du développement pilotée par un assistant IA (**Claude Code**).

## 🎯 Objectif du projet

Ce dépôt n'est pas un jeu commercial : c'est un **terrain d'apprentissage**. Deux axes en parallèle :

1. **Apprendre Unreal Engine et le game design d'un souls-like** en suivant le tutoriel :
   [**Souls-Like Combat System in Unreal Engine 5**](https://www.youtube.com/watch?v=Hs2sM7eFf6Q) — une série complète qui couvre la mise en place d'un personnage jouable, d'un système de combat (combo, esquive, endurance), d'ennemis avec IA, et de la boucle de jeu de base d'un action-RPG à la troisième personne.
2. **Expérimenter le développement assisté par IA** : une bonne partie de la logique Blueprint (combat, IA ennemie, caméra, UI, animation) a été construite, débuggée et itérée en pilotant l'éditeur Unreal directement depuis Claude Code, via un plugin qui expose l'éditeur en MCP (Model Context Protocol). L'idée était de voir jusqu'où on peut aller en délégant l'implémentation à un agent IA tout en gardant la main sur les décisions de design.

## 🕹️ Ce qui est en place

- Personnage jouable à la troisième personne (locomotion 8 directions, strafe, caméra à l'épaule)
- Système de combat : combo d'attaque à l'épée, esquive directionnelle, gestion d'endurance
- Vie / dégâts / mort / réaction aux coups (hit-react), côté joueur et ennemis
- IA ennemie : perception, poursuite, contournement (strafe), attaque, réveil scripté d'un ennemi "endormi", apparition d'un boss après la mort d'un ennemi
- HUD (vie / endurance) en temps réel
- Plusieurs environnements de test (salle du template ThirdPerson, niveau "Necropolis")

Le détail complet des décisions techniques, des bugs rencontrés et de leurs correctifs est journalisé dans [`CLAUDE.md`](CLAUDE.md) — c'est littéralement le carnet de bord de la collaboration avec l'IA, tenu à jour à chaque session.

## 🤖 Le pari "développer avec Claude Code"

Plutôt que d'écrire chaque Blueprint à la main, une grande partie de ce projet a été réalisée en donnant des instructions en langage naturel à Claude Code, qui pilote l'éditeur Unreal via un serveur MCP local (scripts Python exécutés dans l'éditeur : création de nœuds, câblage de graphes, réglage d'assets, tests en Play-In-Editor, lecture de logs...).

Ce que j'en retiens à ce stade :

- **Ça va vite sur la mécanique répétitive** : câbler un combo, un système de dégâts, une IA de poursuite — des tâches qu'un débutant met du temps à comprendre se posent en quelques minutes, ce qui laisse plus de temps pour itérer sur le *feel* du jeu.
- **Les bugs Unreal restent des bugs Unreal** : pins non connectés qui échouent silencieusement, overrides d'instance qui sautent après une édition de CDO, Blend Space cassés créés par script... l'IA se plante sur les mêmes pièges qu'un humain, juste plus vite, et il faut vérifier ses affirmations en testant réellement en jeu plutôt que de la croire sur parole.
- **Le vrai levier, c'est la vérification** : les sessions les plus utiles sont celles où chaque changement est retesté en Play-In-Editor avec des mesures concrètes (position, vitesse, état des variables), pas juste "ça compile donc ça marche".

## 🛠️ Stack technique

- **Unreal Engine 5.8**, Enhanced Input System
- Personnage et animations : pack *Dark Knight*, squelette dédié
- Ennemis : personnages Paragon (Morigesh, Khaimera) retargetés, puis expérimentation avec d'autres packs de personnages (squelette stylisé, créature "alien")
- Environnement : template ThirdPerson par défaut, puis pack *Necropolis*
- Développement piloté en partie par [Claude Code](https://claude.com/claude-code) via un plugin MCP (VibeUE) exposant l'éditeur Unreal en Python scriptable

## 📚 Ressources

- Tutoriel suivi : [Souls-Like Combat System in Unreal Engine 5](https://www.youtube.com/watch?v=Hs2sM7eFf6Q)
- Journal de développement détaillé : [`CLAUDE.md`](CLAUDE.md)
- Notes d'architecture : [`Docs/CombatFlow_Architecture.md`](Docs/CombatFlow_Architecture.md), [`Docs/Boss_StateMachine.md`](Docs/Boss_StateMachine.md)

---

*Projet éducatif — les assets tiers (Paragon, packs de personnages/environnements marketplace) sont utilisés à des fins d'apprentissage et ne sont pas inclus/distribués à des fins commerciales.*
