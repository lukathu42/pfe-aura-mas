# AURA-MAS — Rapport Technique et Théorique Approfondi

**Projet :** *AURA-MAS : Surveillance Intelligente Multi-Agents Agentique* — un mémoire de Master (PFE) en IA & Science des Données, par Soufyane Belmana.

---

## 1. Résumé Exécutif & Objectif Fondamental

### Le problème du monde réel

La vidéosurveillance physique sur des sites semi-fermés (entrepôts, campus, cours industrielles) souffre aujourd'hui de trois défaillances structurelles :

1. **La fatigue liée aux alertes** — les détecteurs d'objets/mouvements naïfs par caméra se déclenchent en permanence, et les opérateurs humains finissent par les ignorer ou les désactiver.
2. **L'aveuglement mono-capteur** — une caméra ou un microphone isolé n'a aucun moyen de corroborer ce qu'il perçoit ; un bris de verre suivi trente secondes plus tard par une personne entrant dans une zone restreinte constitue, pour un capteur isolé, deux non-événements sans rapport.
3. **Une automatisation opaque et non redevable** — les systèmes de « sécurité IA » à boîte noire qui génèrent automatiquement des récits d'incidents risquent l'hallucination, et n'offrent aucune traçabilité sur qui — humain ou modèle — a pris une décision de confinement, ce qui est intenable dans un domaine à enjeux juridiques et liés à la vie privée.

AURA-MAS est un banc d'essai de recherche conçu pour répondre, empiriquement, à une question de thèse précise : **l'organisation des capteurs périphériques en un système multi-agents coordonné (avec allocation de tâches par enchères, fusion tardive multimodale, et une couche d'explication LLM encadrée par des règles) surpasse-t-elle de manière mesurable un pipeline de détection centralisé, mono-processus**, sur les critères de délai d'alerte, de F1, de taux de fausses alertes et de surcoût de coordination ? Le code source n'est pas un produit de sécurité en production — c'est un **appareil expérimental ablatable** : chaque choix architectural (coordination activée/désactivée, enchères vs. round-robin, explication par gabarit vs. par LLM) est un drapeau en ligne de commande, afin que la thèse puisse exécuter des comparaisons contrôlées et rapporter les écarts.

### Concept de domaine/produit

Une **pile de surveillance hiérarchique, multi-agents, du périphérique au cloud, privilégiant la vie privée** :

- **Couche périphérique (Edge)** — des agents par capteur (`CameraAgent`, `AudioAgent`) exécutent la perception localement et ne transmettent jamais d'images brutes hors de l'appareil.
- **Couche de coordination** — un `FusionAgent` fusionne les preuves corroborantes entre capteurs/modalités ; un `CoordinatorAgent` exécute des enchères de type contract-net pour missionner des caméras disponibles afin de re-vérifier des événements ambigus ; un `PolicyAgent` est le seul décideur, déterministe, pour les alertes ; un `ExplanationAgent` rédige un rapport d'incident en langage naturel a posteriori, sous contraintes anti-hallucination (guardrails).
- **Couche de gouvernance** — une console opérateur Streamlit, un flux d'audit en ajout seul (append-only), et un dépôt de preuves anonymisées (recadrages floutés uniquement) referment la boucle humaine (human-in-the-loop) et de conformité.

### Aperçu de la pile technique

| Domaine | Choix |
|---|---|
| Langage | Python 3.11 |
| Détection & suivi d'objets | Ultralytics YOLO11n + ByteTrack (`model.track(tracker="bytetrack.yaml")`) |
| Anomalie visuelle zéro-shot | OpenAI CLIP (ViT-B/32), scoring par prompts zéro-shot |
| Classification d'événements audio | Google YAMNet (TF-Hub) avec un repli DSP léger en dépendances (z-score d'énergie/flatness spectrale par FFT) |
| Messagerie | MQTT (Eclipse Mosquitto) pour les événements périphériques haute fréquence + le trafic de coordination ; Redis Streams pour les journaux d'alertes/d'audit durables ; un `LocalBus` pub/sub en mémoire, fait maison, pour les tests et les démos mono-machine |
| Explication LLM | API Chat Completions compatible OpenAI (modèles de classe GPT-4o-mini, ou Ollama local), sortie structurée en mode JSON |
| UI opérateur | Streamlit |
| Tests | pytest, entièrement hors-ligne/synthétique (sans modèles, sans vidéo, <5s) |
| Infra | Docker Compose (Mosquitto + Redis) |
| Vie privée | Pipeline de flou gaussien OpenCV (localisation de personnes via HOG ou YOLO) |

---

## 2. Fondements Théoriques & Abstractions Fondamentales

### 2.1 Théorie des systèmes multi-agents : agents BDI allégés sur un bus partagé

Chaque agent (`aura_mas/agents/base.py`) est un agent réactif minimal, inspiré du modèle **Croyance–Désir–Intention (BDI)** :

```python
class Agent:
    def __init__(self, agent_id, bus, tick_interval=0.0):
        self.beliefs: Dict[str, Any] = {}   # modèle du monde local, mutable
        ...
    def setup(self): ...   # s'abonner aux topics, charger les modèles  (câblage du Désir)
    def tick(self):  ...   # ré-évaluation périodique                  (exécution de l'Intention)
```

Il n'existe pas d'état global partagé — chaque agent ne connaît que ce qu'il perçoit directement (un flux vidéo/audio) ou ce qui lui parvient via le bus. C'est un modèle classique d'**agentivité faible** (autonomie + aptitude sociale via le passage de messages + réactivité via `tick`/callbacks), délibérément *pas* une implémentation BDI forte (pas de planificateur explicite orienté objectifs ni de bibliothèque de plans) — approprié pour une thèse d'architecture système plutôt que de théorie des agents.

### 2.2 Protocole Contract-Net (CNP) pour l'allocation de tâches

Le `CoordinatorAgent` implémente un **Contract Net à tour unique** (Smith, 1980) manuel pour résoudre le problème « quelle caméra doit re-vérifier cette hypothèse ambiguë ? » :

```
Manager (Coordinator)          Contractants (CameraAgents)
      |--- annonce de tâche --------->|  (TOPIC_TASKS)
      |<-- enchère (score d'utilité de vue) --|  (TOPIC_BIDS)
      |--- attribution (meilleure enchère gagne) --->|  (TOPIC_AWARDS)
      |<-- résultat de vérification ---|  (TOPIC_VERIFICATIONS)
```

La fonction d'enchère (`CameraAgent._view_score`) est une fonction d'utilité artisanale combinant trois facteurs — le fait que la caméra soit un capteur *différent* de celui ayant initialement soulevé l'événement (pour éviter d'interroger le même témoin potentiellement biaisé), l'occupation actuelle (drapeau `_busy` comme contrainte de capacité), et le chevauchement estimé du champ de vision avec la zone de l'événement. C'est une simple **fonction d'utilité multi-attributs**, pas un optimum appris ou théorique-des-jeux — l'enchère garantit une *allocation efficace étant donné des enchères auto-déclarées*, mais l'enchère n'est pas adversariale/stratégique (aucun mécanisme de type VCG assurant la compatibilité des incitations n'est nécessaire, puisque tous les agents sont coopératifs, appartenant au même système).

Le **planificateur round-robin** (mode `mas-rules`) est le groupe témoin délibéré pour l'ablation — il isole la *valeur d'une enchère* de la *valeur d'avoir une coordination quelconque*.

### 2.3 Fusion multimodale de capteurs : OR-bruité pondéré par fiabilité

Le cœur théorique de la « thèse multimodale » (contribution C3 de la thèse) se trouve dans `FusionAgent._fuse_confidence` :

```
P(incident) = 1 − ∏ᵢ (1 − wₘ(i) · conf(eᵢ))
```

Il s'agit du **modèle causal bayésien classique OR-bruité (Noisy-OR)** : chaque événement `eᵢ` est traité comme une « cause » indépendante et imparfaite (bruitée) du même incident sous-jacent, et le modèle calcule la probabilité qu'*au moins un* d'entre eux l'indique correctement. `wₘ` est un a priori de fiabilité fixe par modalité (vidéo 0,9, audio 0,7) — une simplification de la fusion bayésienne complète de capteurs, mais qui possède la propriété mathématique dont la thèse a besoin : **la confiance est monotone non-décroissante avec les preuves corroborantes**, et un bonus fixe de +0,05 est ajouté en cas de corroboration inter-modalités et inter-capteurs, plafonné à 1,0. Cela traduit directement l'intuition « deux témoins indépendants sont plus convaincants qu'un seul » sans nécessiter de vraisemblances jointes apprises ni de données d'entraînement multimodales étiquetées — approprié étant donné que le système exécute des détecteurs zéro-shot/à base de règles par modalité, et non un classifieur de fusion entraîné.

Les événements sont regroupés en **hypothèses** via un regroupement temporel glissant en ligne, indexé par `(famille_incident, zone)` — un algorithme simple de clustering en fenêtre glissante, pas un modèle général de processus ponctuel/détection de rupture, choisi pour son coût de mise à jour en O(1) et son interprétabilité (auditable par un humain).

### 2.4 Raisonnement spatial par zones

`CameraAgent.ZoneRuleEngine` implémente des primitives classiques de **géométrie computationnelle / vision par ordinateur pour la surveillance** :
- **Test point-dans-polygone** via le lancer de rayon (l'algorithme standard de comptage de croisements pair-impair) pour tester si le point de pied d'un objet suivi se trouve à l'intérieur d'une zone restreinte.
- **Machine à états de temps de séjour** par `(track_id, zone)` pour la détection de flânerie (loitering), avec un horodatage `first_seen` réinitialisé chaque fois que la piste sort de la zone.
- **Détection d'objet statique via persistance suivie par IoU** : un objet est « abandonné » si sa boîte englobante conserve un IoU élevé (>0,6, c.-à-d. n'a pas bougé) sur une durée soutenue.

### 2.5 Détection d'anomalie zéro-shot (CLIP)

`ClipAnomalyScorer` est une instanciation légère de la famille d'idées **VadCLIP** (détection d'anomalie vidéo zéro-shot à base de CLIP) : plutôt que d'entraîner un classifieur d'anomalie supervisé, il projette la trame et une banque fixe de prompts en langage naturel « normal » vs « anormal » dans l'espace d'embedding conjoint de CLIP, et prend la masse softmax sur les prompts anormaux comme score d'anomalie. C'est une **stratégie de généralisation zéro-shot, à vocabulaire ouvert** — de nouveaux types d'anomalies peuvent être ajoutés en écrivant de nouveaux prompts, sans réentraînement ni données d'anomalie étiquetées. Le côté audio dispose d'un repli symétrique, encore moins coûteux : la **détection de nouveauté par z-score** sur une base de référence glissante d'énergie court-terme et de flatness spectrale — aucun poids de modèle, utile lorsque TensorFlow/YAMNet n'est pas installé.

### 2.6 IA agentique avec guardrails (machine à états façon LangGraph, encadrée par des règles)

`ExplanationAgent` est architecturalement l'élément le plus intéressant théoriquement (contribution C4 de la thèse). Il modélise la tension bien connue en « IA agentique pour domaines critiques pour la sécurité » : les LLM sont utiles pour la synthèse en langage naturel mais peu fiables pour les *décisions* et sujets à l'hallucination. La conception résout cela par deux garanties structurelles, pas seulement par le prompt :

1. **Ordonnancement causal strict** — le pipeline d'explication ne s'exécute qu'*après* que `PolicyAgent.on_hypothesis` a déjà décidé ALERTE/SUPPRESSION. Le LLM peut décrire une décision ; il ne peut jamais la prendre ni y opposer son veto. C'est imposé par le *flux de contrôle* (l'explainer est invoqué à l'intérieur de `PolicyAgent`, en aval de la vérification de seuil), pas par une instruction de prompt — une distinction importante, puisque les instructions de prompt sont précisément la classe de guardrail que cette conception se refuse explicitement à considérer comme fiable.
2. **Vérification de l'ancrage/guardrail** — `_guardrail_check` traite la sortie JSON du LLM comme non fiable et vérifie mécaniquement que chaque identifiant de preuve cité (motif `ev_[hex]` scanné à la fois dans le texte libre *et* dans le champ structuré `cited_evidence`) est un sous-ensemble des identifiants réellement fournis dans le prompt. Toute référence fabriquée → rejet → repli vers un gabarit déterministe. C'est une instance pratique de **génération ancrée par récupération (retrieval-grounded generation) avec détection programmatique d'hallucination**, moins coûteuse et plus auditable qu'un second appel LLM-juge.

Le pipeline lui-même est une petite machine à états explicite (le docstring du module la dessine littéralement comme un graphe façon LangGraph : `collect_evidence → describe → draft_report → guardrail_check`, avec une arête `échec → fallback_template` depuis chaque nœud), même si elle est codée à la main en Python simple plutôt qu'avec la véritable bibliothèque LangGraph (présente uniquement comme dépendance optionnelle commentée).

---

## 3. Architecture Système de Haut Niveau

### 3.1 Cartographie des composants

```
                         ┌───────────────────────────────────────────┐
                         │     Couche 3 — Gouvernance/Opérateur        │
                         │  Console Streamlit · Journal d'audit (Redis)│
                         │  Dépôt de preuves anonymisées (JPEG, floutées)│
                         └───────────────▲─────────────────────────┬─┘
                                          │ lire alertes             │ ack/rejeter
                                          │                         ▼
                         ┌────────────────┴───────────────────────────┐
                         │            Redis Streams (durable)          │
                         │      aura:alerts       aura:audit           │
                         └────────────────▲───────────────────────────┘
                                          │ ajouter
        ┌─────────────────────────────────┴──────────────────────────────┐
        │                Couche 2 — Coordination du Site                  │
        │                                                                  │
        │   FusionAgent ──hypothèse──▶ PolicyAgent ──alerte──▶ Explanation │
        │        ▲                          │  ▲                Agent     │
        │        │                          │  └── vérifier(zone grise) ──┐  │
        │        │                          ▼                         │  │
        │        │                    CoordinatorAgent ◀───────────────┘  │
        └────────┼──────────────────────────┬───────────────────────────┘
                  │ événements (QoS1)        │ tâches/enchères/attributions/vérifs
        ┌─────────┴──────────────────────────┴───────────────────────────┐
        │                        Bus MQTT (ou LocalBus)                    │
        └──────▲───────────────────────▲───────────────────────▲─────────┘
               │                       │                        │
       ┌───────┴──────┐       ┌────────┴──────┐         ┌───────┴───────┐
       │ CameraAgent   │       │ CameraAgent   │         │  AudioAgent   │
       │ cam_01        │       │ cam_02        │         │  mic_01       │
       │ YOLO+ByteTrack│       │ ...           │         │ YAMNet/DSP    │
       │ Zones+CLIP    │       │               │         │               │
       └───────────────┘       └───────────────┘         └───────────────┘
        Couche 1 — Perception Périphérique (frontière vie privée : les trames brutes s'arrêtent ici)
```

### 3.2 Organisation des répertoires et séparation logique

```
aura_mas/
  core/         infrastructure agnostique du transport
    bus.py        schémas de messages (Detection/Event/Alert), constantes de topics,
                   interface BaseBus + 3 implémentations (Local/MQTT), AlertStore
    privacy.py     anonymize_and_save() — le point de passage obligé unique pour
                   toute trame quittant un agent périphérique
  agents/       un fichier par rôle d'agent, chacun n'important que core/ et base.py
    base.py                cycle de vie générique de l'Agent (setup/tick/start/stop)
    camera_agent.py         perception périphérique + règles de zone + CLIP + enchères
    audio_agent.py           perception périphérique (audio) + YAMNet/DSP
    fusion_agent.py           regroupement d'hypothèses multimodal (OR-bruité)
    coordinator_agent.py     enchère contract-net / round-robin
    policy_agent.py          l'unique autorité de rédaction d'alertes
    explanation_agent.py     narration LLM d'incident encadrée par des règles
  scenarios/    replay.py = racine d'orchestration/câblage (le « main() » du MAS) ;
                *.json manifestes décrivant capteurs/zones/vérité terrain
  eval/         metrics.py — scoring hors-ligne des runs de replay vs. vérité terrain
  dashboard/    app.py — UI Streamlit lecture/ack, entièrement découplée (ne lit que
                depuis AlertStore, ne parle jamais directement aux agents)
  tests/        test_pipeline.py — tests d'intégration synthétiques, sans modèle
```

C'est une **séparation en couches/hexagonale** propre : `core/` est l'intérieur stable (contrats de messages + transport), `agents/` est la logique métier, et `scenarios/`, `eval/`, `dashboard/` sont trois pilotes indépendants du même noyau — aucun d'eux ne s'importe mutuellement, seulement `core` et `agents`. Note : des fichiers `.py` identiquement nommés existent à plat à la racine du dépôt (`bus.py`, `camera_agent.py`, etc.) à côté de `aura_mas/` — ce sont des copies d'export figées dans le temps (probablement issues du processus de rédaction de la thèse/génération de figures, `AURA-MAS_Code.zip`), pas une seconde implémentation ; `aura_mas/`, tel qu'importé par `scenarios/replay.py` et la suite de tests, est la source de vérité faisant autorité.

### 3.3 Chemin d'exécution canonique — traçage d'un événement d'intrusion

En utilisant `scenarios/intrusion_01.json` et `--mode mas-auction` comme parcours concret :

1. **`replay.run_scenario`** analyse le manifeste, construit un `bus` (MQTT ou `LocalBus`), un `AlertStore`, et câble les quatre agents de la Couche 2 : `coordinator`, `explainer` (si `--llm`), `policy` (détient des références vers `store`, `coordinator`, `explainer`), `fusion` (son callback `on_hypothesis` *est* `policy.on_hypothesis` — un callback Python direct, pas un aller-retour via le bus, pour une latence faible sur le chemin de décision critique).
2. Deux `CameraAgent` et un `AudioAgent` sont démarrés, chacun sur son propre thread, lisant `data/clips/*.mp4|wav` et se cadençant sur le temps réel (`realtime=True` sauf si `mode == "centralized"`).
3. `cam_01._process_frame` exécute `YOLO.track(...)`, obtient une piste `person` à l'intérieur du polygone de `zone_A` → `ZoneRuleEngine.evaluate` déclenche `intrusion` → `_emit_event` appelle `anonymize_and_save` (floute la personne, ne persiste jamais la trame brute) et publie un `Event(event_type="intrusion", modality="video", confidence=0.8...)` sur `TOPIC_EVENTS`.
4. `mic_01` détecte indépendamment `audio_glass_break` à peu près au même horodatage et publie son propre `Event` sur le même topic.
5. `FusionAgent._on_event` reçoit les deux. `intrusion` et `audio_glass_break` sont tous deux associés par `EVENT_FAMILIES` à `"security"`, et partagent tous deux `zone_A`, ils atterrissent donc dans le **même bucket `Hypothesis`** (clé `"security:zone_A"`). `_fuse_confidence` calcule l'OR-bruité sur les deux événements plus les bonus inter-modalités/inter-capteurs — la confiance s'élève au-dessus de ce que produirait chaque capteur seul.
6. À son `tick()` d'une seconde, une fois que `now - hyp.last_ts > window_seconds` (6s), `FusionAgent` vidange l'hypothèse et appelle directement `policy.on_hypothesis(hyp)`.
7. **`PolicyAgent.on_hypothesis`** — l'unique autorité : si la confiance tombe dans la zone grise du coordinateur (0,35–0,75), il déclenche `coordinator.request_verification(hyp)` (un tour bloquant de contract-net contre `cam_02`, puisqu'elle n'était pas le capteur d'origine), ajustant la confiance de ±0,15/0,20 selon le résultat de la vérification ; applique ensuite `ALERT_THRESHOLDS` par sévérité, puis un cooldown par `(zone, event_type)` pour supprimer les répétitions ; chaque branche — alerte ou suppression — est écrite dans `store.audit(...)`.
8. Si une alerte se déclenche, `PolicyAgent` appelle `explainer.explain(alert, hyp)` (ou, sans `--llm`, `_template_explanation`) pour joindre un récit lisible par un humain, puis `store.append(alert)` — écriture durable sur Redis Streams (ou repli JSONL).
9. `replay.run_scenario`'s `timed_append` monkey-patché enregistre également l'alerte avec le temps d'horloge murale dans un `alerts_log` en mémoire, qui fait partie du `results/run_*.json` que `eval/metrics.evaluate_run` consomme pour scorer précision/rappel/F1/délai-d'alerte par rapport à la `ground_truth` du manifeste.
10. Indépendamment, le **tableau de bord Streamlit** interroge `AlertStore.read_alerts()` et affiche l'alerte, ses images de preuve floutées, et son explication ; les clics d'accusé de réception/rejet de l'opérateur sont ajoutés au flux d'audit — refermant la boucle humaine.

---

## 4. Patrons de Conception & Paradigmes Architecturaux

### Paradigme architectural

**Système multi-agents hiérarchique piloté par événements** — trois couches de gouvernance explicites (Périphérie → Coordination → Gouvernance), communiquant exclusivement via un bus publish/subscribe asynchrone entre les Couches 1↔2, avec un callback direct en mémoire utilisé uniquement pour le saut Fusion→Policy sensible à la latence. Ce n'est *ni* des microservices (tout peut tourner dans un seul processus via `LocalBus`) *ni* un monolithe (chaque agent est instanciable, testable et remplaçable indépendamment — voir les drapeaux d'ablation `mode`). C'est plus proche d'un **modèle d'acteurs allégé** : chaque `Agent` possède un état mutable privé (`self.beliefs`) et ne communique que via des messages, bien que les threads partagent le GIL Python plutôt que d'être isolés comme de véritables acteurs, et un verrouillage explicite (`threading.Lock`) est utilisé partout où un état de dictionnaire partagé (`_hypotheses`, `_bids`) est modifié depuis plusieurs threads de callback.

### Patrons de conception utilisés

| Patron | Où | Pourquoi |
|---|---|---|
| **Stratégie (Strategy)** | `make_bus(kind=...)` retourne `MqttBus`/`LocalBus` ; `CoordinatorAgent.mode ∈ {auction, roundrobin, off}` | Permuter le transport ou la politique d'allocation sans toucher aux appelants — c'est *exactement* le mécanisme d'ablation |
| **Méthode Modèle (Template Method)** | `Agent.start()` appelle `self.setup()` puis lance optionnellement `_tick_loop()` ; les sous-classes redéfinissent `setup()`/`tick()` | Cycle de vie uniforme pour 5 agents très différents |
| **Observateur / Pub-Sub** | `BaseBus.subscribe/publish`, `LocalBus._match` (émulation de wildcards MQTT) | Découple les producteurs (caméras) des consommateurs (fusion) — N:M sans références directes |
| **Pipeline / Chaîne de Responsabilité** | `ExplanationAgent.explain` : `_collect_evidence → _describe → _draft_report → _guardrail_check → (_fallback)` | Chaque étape peut échouer de manière sûre vers l'étape suivante |
| **Dépôt (Repository)** | `AlertStore` abstrait Redis Streams vs. fichier JSONL derrière `append/audit/read_alerts` | Les appelants (`PolicyAgent`, tableau de bord) ne savent jamais quel backend est actif |
| **Fabrique (Factory)** | `make_bus()`, chargement paresseux des modèles (`YOLO(...)`, `ClipAnomalyScorer()` uniquement dans `setup()`) | Diffère les dépendances coûteuses/optionnelles (torch, tensorflow) jusqu'à leur première utilisation réelle, gardant le noyau testable sans elles |
| **Objet Nul / dégradation gracieuse** | Repli YAMNet → DSP, CLIP indisponible → désactivé, échec du guardrail LLM → gabarit, Redis indisponible → JSONL | Idiome récurrent dans toute la base de code : chaque dépendance ML/infra a un repli déterministe et léger en dépendances, si bien que *le système ne bloque jamais faute d'infrastructure manquante* |
| **Commande / DTO de message** | Dataclasses `Detection`, `Event`, `Alert` avec `to_json`/`from_json` | Format sur le fil agnostique du transport ; le même schéma fonctionne sur MQTT, Redis, ou `LocalBus` en mémoire |
| **Enchère / Contract-Net** (comportemental, pas GoF) | `CoordinatorAgent` | Voir §2.2 |

L'idiome de repli mérite sa propre mise en avant : c'est la décision architecturale la plus cohérente de toute la base de code, et c'est ce qui rend possible la **suite de tests hors-ligne** — `aura_mas/tests/test_pipeline.py` exerce les wildcards du bus, la fusion OR-bruitée, les enchères de coordination, les seuils/cooldown de politique, le scoring des métriques, et le guardrail d'explication, entièrement avec des objets `Event`/`Hypothesis` synthétiques, en moins de 5 secondes, sans aucune dépendance GPU/modèle/réseau.

---

## 5. Analyse Approfondie du Code : Fichiers Critiques

### 1. `aura_mas/core/bus.py` — le système nerveux et le contrat du système
Le seul fichier dont dépend transitivement tout autre module. Définit les trois dataclasses de format sur le fil (`Detection`, `Event`, `Alert`) qui constituent *l'intégralité* du contrat inter-agents — n'importe quel agent peut être remplacé tant qu'il parle ces formes JSON. `BaseBus` est une interface à 4 méthodes ; `LocalBus` réimplémente la sémantique des wildcards de topics MQTT (`+`/`#`) en Python pur, afin que les tests et les démos mono-processus se comportent de manière identique au véritable broker. `AlertStore` découple la durabilité (Redis Streams avec `xadd` prêt pour les groupes de consommateurs, ou JSONL) de chaque lecteur/écrivain. **À surveiller :** `make_bus("auto", ...)` — le repli try/except MQTT→LocalBus est la raison pour laquelle l'ensemble du système se dégrade gracieusement lorsque Mosquitto ne tourne pas.

### 2. `aura_mas/agents/policy_agent.py` — le point de passage de la responsabilité
Explicitement documenté comme « le SEUL composant autorisé à créer des alertes ». Pipeline déterministe en six étapes : re-vérification déclenchée par la coordination → seuil basé sur la sévérité → cooldown/hystérésis → écriture d'audit obligatoire (même pour les suppressions) → construction de l'alerte → explication en aval (non décisionnaire). **À surveiller :** `on_hypothesis` — cette unique méthode est la frontière décisionnelle sur laquelle repose l'affirmation « IA agentique encadrée par des règles » de toute la thèse ; l'exception de l'explainer est capturée localement afin qu'une panne du LLM ne puisse jamais empêcher une alerte d'être enregistrée (`except Exception: ... alert.explanation = self._template_explanation(...)`).

### 3. `aura_mas/agents/fusion_agent.py` — la thèse multimodale, en code
Implémente le combinateur OR-bruité (§2.3) et le regroupement `Hypothesis` en fenêtre glissante. **À surveiller :** `_fuse_confidence` (méthode statique, facilement testable en isolation unitaire — voir `test_fusion_noisy_or_increases_with_corroboration`) et le duo `tick()`/`flush_all()` — `tick()` est piloté par le temps pour le fonctionnement en direct, `flush_all()` est le vidage déterministe en fin de replay afin que les runs de scénario par lots ne perdent pas la dernière hypothèse ouverte dans une course contre l'arrêt des threads.

### 4. `aura_mas/agents/camera_agent.py` — le module le plus dense en fonctionnalités
Combine quatre capacités distinctes : (a) l'inférence YOLO11n+ByteTrack (`_process_frame`), (b) le `ZoneRuleEngine` géométrique (intrusion/flânerie/objet abandonné), (c) le scoring optionnel d'anomalie zéro-shot par CLIP, et (d) le côté *contractant* du contract-net (`_on_task_announce` enchérit, `_on_award` exécute `_verify` — une passe de re-détection délibérément plus précise à `imgsz=960` par rapport à la résolution par défaut de la passe de streaming). **À surveiller :** `_view_score` (la fonction d'enchère) et `_verify` (ce que « gagner l'enchère » provoque réellement — une seconde passe d'inférence plus coûteuse, qui constitue le véritable arbitrage coût/bénéfice que l'enchère est censée justifier).

### 5. `aura_mas/agents/coordinator_agent.py` — le mécanisme d'allocation
`request_verification` est un appel **bloquant** du point de vue de l'appelant (Policy), piloté en interne par pub/sub : publier la tâche → dormir `bid_window` secondes en collectant les enchères sur un dictionnaire protégé par verrou → choisir `max(bids, key=bid)` → publier l'attribution → interroger (`_await_verification`, intervalle de 50ms, délai de 3s) jusqu'à ce qu'une vérification correspondante arrive ou expire. **À surveiller :** la branche `mode` dans `request_verification` (`auction` vs `roundrobin`) est exactement le bascule que le tableau d'ablation de la thèse (`mas-rules` vs `mas-auction`) mesure — même signature d'appel, algorithme d'allocation différent, permettant à `eval/metrics.py` de produire une comparaison à périmètre égal.

### 6. `aura_mas/agents/explanation_agent.py` — la frontière LLM critique pour la sécurité
Voir §2.6 pour la théorie. **À surveiller :** le scan d'hallucination par regex de `_guardrail_check` (`re.findall(r"ev_[0-9a-f]{6,}", ...)`) — c'est le mécanisme concret, pas une instruction de prompt, qui empêche le LLM d'inventer des preuves ; `test_explanation_guardrail_rejects_fabricated_evidence` est la spécification exécutable de cette garantie.

### 7. `aura_mas/scenarios/replay.py` — la racine de composition
Pas un fichier de « logique métier », mais l'unique endroit où tous les agents sont réellement câblés ensemble, donc le moyen le plus rapide de comprendre le flux de données en exécution sans lire cinq fichiers. **À surveiller :** le dictionnaire `mode` (`{"mas-auction": "auction", "mas-rules": "roundrobin", "mas-nocoord": "off", "centralized": "off"}`) et la branche `if mode == "centralized": ... th.start(); th.join()` séquentielle vs. parallèle — ce simple `if` constitue littéralement la comparaison architecturale « MAS centralisé vs. hiérarchique » que la thèse mesure en temps d'horloge murale.

---

## 6. Gestion des Données & de l'État

### Localité de l'état
Il n'y a **aucun état global partagé ni base de données centrale** pour le fonctionnement en direct — les `self.beliefs`/attributs d'instance de chaque agent sont le seul état mutable, et tout état inter-agents est soit (a) des messages transitoires sur le bus, soit (b) des enregistrements durables dans `AlertStore`. C'est une conséquence délibérée de la conception MAS : l'état est distribué par construction, ce qui est exactement ce que le mode de référence « centralisé » supprime (il traite les sources séquentiellement dans un seul processus/chaîne de jointure de threads au lieu d'agents indépendamment threadés) afin d'isoler l'effet architectural mesuré.

### Persistance
- **Détections** (`site/{sensor}/detections`, QoS 0) : éphémères, jamais persistées — pure télémétrie en streaming.
- **Événements** (`site/events`, QoS 1) : éphémères sur le bus, mais chacun porte un `evidence_path` pointant vers un JPEG déjà anonymisé et écrit dans `data/evidence/` au moment de l'émission — c'est la trame elle-même qui est durable, pas le message.
- **Alertes** : le seul enregistrement durable et interrogeable — Redis Streams (`aura:alerts`) si accessible, sinon fichier JSONL en ajout seul (`data/alerts_<scenario>_<mode>.jsonl`). Redis Streams a été choisi spécifiquement pour sa sémantique de groupe de consommateurs/rejeu (journal durable, pas une file qui perd les messages une fois consommés) — approprié pour un enregistrement de niveau audit.
- **Audit** (`aura:audit` / `data/audit.jsonl`) : chaque décision de `PolicyAgent` (alerte *et* suppression) et chaque action de l'UI opérateur (`acknowledge`/`dismiss`) est ajoutée — une piste de redevabilité immuable et chronologique, délibérément séparée du flux d'alertes afin qu'elle ne puisse pas être modifiée en re-traitant les alertes.
- **Résultats de run de scénario** (`results/run_<scenario>_<mode>.json`) : l'enregistrement expérimental complet (vérité terrain, alertes horodatées, métriques par agent) que `eval/metrics.py` consomme — c'est effectivement le jeu de données brut de la thèse pour ses tableaux d'ablation.

### Concurrence & effets de bord
- Chaque agent de perception (`CameraAgent`, `AudioAgent`) exécute sa boucle `run()` sur son propre **thread démon**, démarré depuis `replay.run_scenario` ; les agents pilotés par tick (`FusionAgent`) exécutent leur logique périodique sur un thread interne engendré par `Agent.start()`.
- Les dictionnaires mutables partagés accédés depuis plusieurs threads (`FusionAgent._hypotheses`, `CoordinatorAgent._bids`/`_verifications`) sont protégés par un simple `threading.Lock` autour de chaque lecture-modification-écriture — grossier mais correct, approprié étant donné que les volumes de messages sont modestes (au niveau événement, pas au niveau trame).
- `CoordinatorAgent.request_verification` est un patron **synchrone-par-dessus-asynchrone** : il bloque le thread appelant (celui de Policy) sur une boucle de sondage temporisée attendant une réponse asynchrone pub/sub — une simplification pragmatique (pas de futures/asyncio) qui garde `PolicyAgent.on_hypothesis` comme une fonction synchrone à flux linéaire, facile à auditer, au prix d'immobiliser un thread jusqu'à 3s par hypothèse en zone grise.
- L'isolation des pannes se fait au niveau du bus : `LocalBus.publish` et `MqttBus._on_message` enveloppent tous deux chaque callback d'abonné dans un `try/except Exception: log.exception(...)`, si bien qu'un agent défaillant ne peut pas faire planter l'émetteur ou les autres abonnés — une propriété de robustesse importante pour un système censé survivre à des dépendances ML optionnelles/instables.

---

## 7. Enseignements pour le Développeur & Résumé du Modèle Mental

### Modèle mental

Pensez à AURA-MAS comme **une salle de rédaction, pas une machine** :
- **Les CameraAgents/AudioAgents sont des correspondants de terrain** — chacun dépose des rapports indépendants et non vérifiés (`Event`) dès qu'il voit quelque chose.
- **Le FusionAgent est le bureau des dépêches** — il n'enquête pas, il remarque simplement quand plusieurs correspondants décrivent la même histoire dans une fenêtre de temps/lieu, et augmente sa crédibilité en conséquence.
- **Le CoordinatorAgent est un rédacteur en chef qui distribue les missions** — pour une histoire plausible mais non confirmée, il lance un appel (« qui est près de zone_A ? ») et missionne le correspondant le mieux placé pour vérifier une seconde fois.
- **Le PolicyAgent est l'unique rédacteur en chef habilité à approuver la publication** — des règles de style déterministes (seuils, une règle « ne pas republier la même histoire dans les 20s »), et chaque décision d'acceptation/rejet est consignée dans le registre permanent du journal.
- **L'ExplanationAgent est un correcteur, engagé *après* que l'histoire ait été approuvée**, qui n'est autorisé à écrire qu'à partir des faits déjà présents dans l'histoire approuvée — jamais autorisé à ajouter un fait nouveau, et vérifié par rapport à la liste des sources avant impression.

Si vous ne devez retenir qu'une seule phrase : **la perception est distribuée et opportuniste (best-effort) ; la décision d'alerte est centralisée, déterministe et auditée ; le récit est généré en dernier et ne peut jamais annuler la décision.**

### Arbitrages, goulots d'étranglement, dette technique

- **Sondage grossier dans le chemin d'enchère** (`time.sleep(bid_window)`, sondage de vérification à 50ms) — simple et testable, mais ajoute une latence fixe (`bid_window` + jusqu'à 3s) à chaque vérification en zone grise ; un rendez-vous piloté par événements via `Condition`/futures réduirait cela mais ajoute une complexité dont la thèse n'a pas besoin pour démontrer son propos.
- **Poids de fiabilité fixes** (`MODALITY_RELIABILITY = {"video": 0.9, "audio": 0.7}`) et **seuils réglés à la main** (`ALERT_THRESHOLDS`, `gray_zone=(0.35, 0.75)`) ne sont pas appris à partir de données — raisonnable pour un système expérimental contrôlé, mais nécessiterait un calibrage face au coût réel des faux positifs d'un déploiement réel avant une utilisation en production.
- **Le coût de re-détection de `_verify` n'est pas mesuré dans le code lui-même face à son bénéfice** — le retour sur investissement de l'enchère (la re-vérification réduit-elle réellement plus les fausses alertes qu'elle ne coûte en latence/calcul ?) est le type de question que les colonnes `mean_allocation_ms` et `false_alerts_per_hour` de `eval/metrics.py` sont conçues pour élucider, mais seulement une fois de véritables runs d'ablation exécutés — actuellement `results/` et `data/` sont présents mais les clips de scénario (`data/clips/*.mp4|wav`) référencés par les manifestes ne sont pas fournis dans cet instantané, donc `replay.py` nécessite de véritables médias avant de pouvoir s'exécuter de bout en bout.
- **La duplication de fichiers à la racine** (les fichiers `bus.py`, `camera_agent.py`, etc. isolés à côté de `aura_mas/`) est du poids mort pour quiconque édite le code — toujours éditer sous `aura_mas/`, puisque c'est ce qu'importent `scenarios/replay.py` et la suite de tests.
- **Le README référence un répertoire `configs/`** (« zones du site, seuils ») qui n'existe pas actuellement dans le dépôt — la configuration des zones/seuils est intégrée directement dans le JSON de scénario et les constantes de module `SEVERITY_MAP`/`ALERT_THRESHOLDS` — dérive documentaire mineure, pas une lacune fonctionnelle.
- **Le guardrail de `ExplanationAgent` est basé sur des regex/ensembles, pas sémantique** — il arrête la fabrication littérale d'identifiants mais ne détecterait pas une hallucination plus subtile (par exemple, une mauvaise attribution du contenu d'un événement réellement cité). Suffisant pour l'affirmation spécifique de la thèse « aucune preuve inventée », mais une limite de portée connue qu'il vaut la peine d'énoncer explicitement si la soutenance de thèse est sondée sur ce point.

### Points de départ suggérés pour modification

- **Ajouter un nouveau type d'événement** (ex. « escalade de clôture ») : ajouter la logique de détection à `ZoneRuleEngine` ou à `CLIP.ANOMALY_PROMPTS`, puis l'enregistrer dans `EVENT_FAMILIES` (fusion_agent.py) et `SEVERITY_MAP`/`ALERT_THRESHOLDS` (policy_agent.py) — trois petites modifications bien isolées, aucun autre fichier ne touche aux chaînes de type d'événement.
- **Modifier la mathématique de fusion** : tout se trouve dans l'unique méthode statique `FusionAgent._fuse_confidence` — elle est pure (dataclass en entrée, float en sortie), donc trivialement testable en isolation, exactement comme le démontre déjà `test_fusion_noisy_or_increases_with_corroboration`.
- **Exécuter vous-même la suite d'ablation** : la section « Thesis ablations produced by this code » du `README.md` est littéralement une recette exécutable — commencez là, et placez de véritables clips aux chemins attendus par les JSON de scénario (`data/clips/...`) avant d'invoquer `replay.py`.
- **Comprendre le contrat du guardrail avant de toucher à `explanation_agent.py`** : lisez d'abord `test_explanation_guardrail_rejects_fabricated_evidence` — c'est la spécification exécutable de ce que signifie « sûr » pour ce module.
